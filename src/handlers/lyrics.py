import html
import json
from pathlib import Path
from typing import Optional, Callable, Tuple, Dict
from .playlist import MusicInfoFetcher
from ..core.network import network
from ..core.config import config
from ..utils.decorators import ensure_downloads_dir


class LyricsManager:
    """歌词管理类"""

    def __init__(self, callback: Optional[Callable] = None):
        self.callback = callback or print

    def log(self, message: str):
        """日志输出"""
        self.callback(message)

    async def download_lyrics_from_qq(self, song_mid: str, audio_filename: Optional[str] = None,
                                      return_content: bool = False) -> Tuple[bool, str]:
        """从QQ音乐下载歌词"""
        self.log(f"正在从QQ音乐获取歌词，歌曲mid: {song_mid}")
        try:
            # song_mid 为0时，先获取歌曲信息
            if song_mid == "0":
                fetcher = MusicInfoFetcher(self.callback)
                song_info = await fetcher.get_song_info(audio_filename)
                if not song_info:
                    return False, "无法获取歌曲信息"
                song_mid = song_info.songmid
                self.log(f"重新获取到的歌曲mid: {song_mid}")

            lyric_url = "https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg"
            params = {
                "nobase64": 1,
                "songmid": song_mid,
                "platform": "yqq",
                "inCharset": "utf8",
                "outCharset": "utf-8",
                "g_tk": 5381
            }
            headers = {"Referer": "https://y.qq.com/"}

            lyric_data = await network.async_get_text(lyric_url, params=params, headers=headers)
            if not lyric_data:
                return False, "获取歌词失败"

            lyric_data = lyric_data.strip('MusicJsonCallback()').strip()
            lyric_json = json.loads(lyric_data)

            if lyric_json.get('retcode') != 0:
                return False, "获取歌词失败"

            lyrics_content = self._process_qq_lyrics(
                html.unescape(lyric_json.get("lyric", "")),
                html.unescape(lyric_json.get("trans", ""))
            )

            if return_content:
                return True, lyrics_content

            if audio_filename:
                return await self.save_lyrics_file(lyrics_content, audio_filename)
            
            return True, lyrics_content

        except Exception as e:
            error_msg = f"下载歌词时出错: {str(e)}"
            self.log(error_msg)
            return False, error_msg

    def _process_qq_lyrics(self, original_lyric: str, translate_lyric: str) -> str:
        """处理QQ音乐歌词"""
        original_lines = self._parse_lyric_lines(original_lyric)
        translate_lines = self._parse_lyric_lines(translate_lyric)

        lyrics_content = []
        for time_tag, original in original_lines.items():
            lyrics_content.append(f"{time_tag}{original}")
            if time_tag in translate_lines:
                lyrics_content.append(f"{time_tag}{translate_lines[time_tag]}")

        return "\n".join(lyrics_content)

    @staticmethod
    def _parse_lyric_lines(lyric: str) -> Dict[str, str]:
        """解析歌词行"""
        lines = {}
        for line in lyric.split('\n'):
            if line.strip() and '[' in line:
                try:
                    time_tag = line[line.find('['):line.find(']') + 1]
                    content = line[line.find(']') + 1:].strip()
                    if content:
                        lines[time_tag] = content
                except:
                    continue
        return lines

    @ensure_downloads_dir
    async def save_lyrics_file(self, lyrics_content: str, audio_filename: Optional[str]) -> Tuple[bool, str]:
        """保存歌词到文件"""
        if not audio_filename:
            return False, "保存歌词文件时需要提供音频文件名"

        lyrics_filename = Path(audio_filename).with_suffix('.lrc')
        output_file = config.DOWNLOADS_DIR / lyrics_filename

        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(lyrics_content)
            self.log(f"歌词已保存到: {output_file}")
            return True, str(output_file)
        except Exception as e:
            error_msg = f"保存歌词文件时出错: {str(e)}"
            self.log(error_msg)
            return False, error_msg
