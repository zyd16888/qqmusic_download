import argparse
import html
import json
import os
import ssl
import time
from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from typing import Optional, Tuple, Callable, Dict, Set, List, Union
from urllib.parse import urlparse

import aiohttp
import humanize
import requests
import urllib3
from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3, APIC, USLT
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4, MP4Cover


# 全局配置
@dataclass
class Config:
    DOWNLOADS_DIR: Path = Path('downloads')
    DEFAULT_QUALITY: int = 11
    BLOCK_SIZE: int = 8192
    PROGRESS_UPDATE_INTERVAL: float = 0.5


config = Config()


# SSL配置
def setup_ssl():
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    session = requests.Session()
    session.verify = False
    session.trust_env = False

    try:
        default_context = ssl.create_default_context()
        default_context.set_ciphers("DEFAULT:@SECLEVEL=1")
        session.mount("https://", requests.adapters.HTTPAdapter(max_retries=3))
    except Exception as e:
        print(f"SSL配置警告: {str(e)}")

    return session


session = setup_ssl()
requests.get = session.get


# 数据类
@dataclass
class AudioMetadata:
    title: Optional[str]
    artist: Optional[str]


@dataclass
class SongInfo:
    song: str
    singer: str
    url: str
    cover: Optional[str]
    songmid: str


# 工具装饰器
def ensure_downloads_dir(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        config.DOWNLOADS_DIR.mkdir(exist_ok=True)
        return func(*args, **kwargs)

    return wrapper


def log_errors(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"{func.__name__} 发生错误: {str(e)}")
            return None

    return wrapper


# 音频处理类
class AudioHandler:
    def __init__(self, filepath: Union[str, Path]):
        self.filepath = Path(filepath)
        self.audio = self._load_audio()

    def _load_audio(self):
        handlers = {
            '.mp3': lambda p: MP3(p, ID3=ID3),
            '.flac': FLAC,
            '.m4a': MP4
        }
        handler = handlers.get(self.filepath.suffix.lower())
        if not handler:
            raise ValueError(f"不支持的音频格式: {self.filepath.suffix}")
        return handler(self.filepath)

    def add_cover(self, cover_data: bytes, mime_type: str = 'image/jpeg') -> bool:
        try:
            ext = self.filepath.suffix.lower()
            if ext == '.mp3':
                if not hasattr(self.audio, 'tags'):
                    self.audio.add_tags()
                self.audio.tags.add(
                    APIC(encoding=3, mime=mime_type, type=3, desc='Cover', data=cover_data)
                )
            elif ext == '.flac':
                image = Picture()
                image.type = 3
                image.mime = mime_type
                image.desc = 'Cover'
                image.data = cover_data
                self.audio.add_picture(image)
            elif ext == '.m4a':
                cover_format = MP4Cover.FORMAT_PNG if mime_type.endswith('png') else MP4Cover.FORMAT_JPEG
                self.audio.tags['covr'] = [MP4Cover(cover_data, imageformat=cover_format)]

            self.audio.save()
            return True
        except Exception as e:
            print(f"添加封面时出错: {str(e)}")
            return False

    def add_lyrics(self, lyrics: str) -> bool:
        try:
            ext = self.filepath.suffix.lower()
            if ext == '.mp3':
                if not hasattr(self.audio, 'tags'):
                    self.audio.add_tags()
                self.audio.tags["USLT"] = USLT(encoding=3, lang="chi", desc="", text=lyrics)
            elif ext == '.flac':
                self.audio["LYRICS"] = lyrics
            elif ext == '.m4a':
                self.audio["\xa9lyr"] = lyrics

            self.audio.save()
            return True
        except Exception as e:
            print(f"添加歌词时出错: {str(e)}")
            return False

    def get_metadata(self) -> AudioMetadata:
        try:
            ext = self.filepath.suffix.lower()
            if ext == '.mp3':
                return AudioMetadata(
                    title=str(self.audio.get('TIT2', [''])[0]),
                    artist=str(self.audio.get('TPE1', [''])[0])
                )
            elif ext == '.flac':
                return AudioMetadata(
                    title=self.audio.get('title', [''])[0] if self.audio.get('title') else None,
                    artist=self.audio.get('artist', [''])[0] if self.audio.get('artist') else None
                )
            elif ext == '.m4a':
                return AudioMetadata(
                    title=self.audio.get('\xa9nam', [''])[0] if self.audio.get('\xa9nam') else None,
                    artist=self.audio.get('\xa9ART', [''])[0] if self.audio.get('\xa9ART') else None
                )
        except Exception as e:
            print(f"读取元数据时出错: {str(e)}")
            return AudioMetadata(None, None)


class DownloadManager:
    def __init__(self, callback: Optional[Callable] = None):
        self.callback = callback or print

    def log(self, message: str):
        self.callback(message)

    @ensure_downloads_dir
    async def download_with_progress(self, url: str, filepath: Path) -> bool:
        """带进度和速度显示的下载函数"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded = 0
                    start_time = time.time()
                    last_update_time = start_time

                    with open(filepath, 'wb') as f:
                        async for chunk in response.content.iter_chunked(config.BLOCK_SIZE):
                            downloaded += len(chunk)
                            f.write(chunk)

                            current_time = time.time()
                            if current_time - last_update_time >= config.PROGRESS_UPDATE_INTERVAL:
                                self._update_progress(downloaded, total_size, start_time, current_time)
                                last_update_time = current_time

                    self.log("下载完成！")
                    return True

        except Exception as e:
            self.log(f"下载出错: {str(e)}")
            return False

    def _update_progress(self, downloaded: int, total_size: int, start_time: float, current_time: float):
        duration = current_time - start_time
        if duration > 0:
            speed = downloaded / duration
            progress = (downloaded / total_size * 100) if total_size else 0
            self.log(f"下载进度: {progress:.1f}% | 速度: {humanize.naturalsize(speed)}/s")


class LyricsManager:
    def __init__(self, callback: Optional[Callable] = None):
        self.callback = callback or print

    def log(self, message: str):
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

            async with aiohttp.ClientSession() as session:
                async with session.get(lyric_url, params=params, headers=headers) as response:
                    lyric_data = await response.text()
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

                    return self._save_lyrics(lyrics_content, audio_filename)

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
    def _save_lyrics(self, lyrics_content: str, audio_filename: Optional[str]) -> Tuple[bool, str]:
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


class MusicInfoFetcher:
    def __init__(self, callback: Optional[Callable] = None):
        self.callback = callback or print
    def log(self, message: str):
        self.callback(message)
    async def get_song_info(self, keyword: str, n: int = 1, quality: int = 11) -> Optional[SongInfo]:
        """获取歌曲信息"""
        base_url = 'https://api.lolimi.cn/API/qqdg/'
        params = {'word': keyword, 'n': n, 'q': quality}

        try:
            self.log(f"正在获取 {keyword} 的歌曲信息, 序号: {n}, 音质: {quality}")
            async with aiohttp.ClientSession() as session:
                async with session.get(base_url, params=params) as response:
                    data = await response.json()

                    if data['code'] != 200:
                        self.callback(f"获取歌曲信息失败: {data.get('msg', '未知错误')}")
                        return None

                    song_data = data['data']
                    songmid = song_data['link'].split('songmid=')[1].split('&')[0]

                    return SongInfo(
                        song=song_data['song'],
                        singer=song_data['singer'],
                        url=song_data['url'],
                        cover=song_data.get('cover'),
                        songmid=songmid
                    )

        except Exception as e:
            self.callback(f"获取歌曲信息时出错: {str(e)}")
            return None


class MusicDownloader:
    def __init__(self, callback: Optional[Callable] = None):
        self.callback = callback or print
        self.download_manager = DownloadManager(callback)
        self.lyrics_manager = LyricsManager(callback)
        self.info_fetcher = MusicInfoFetcher(callback)

    def log(self, message: str):
        self.callback(message)

    @ensure_downloads_dir
    async def download_song(self, keyword: str, n: int = 1, quality: int = 11,
                            download_lyrics: bool = False, embed_lyrics: bool = False,
                            only_lyrics: bool = False) -> bool:
        """下载单首歌曲"""
        try:
            song_info = await self.info_fetcher.get_song_info(keyword, n, quality)
            if not song_info:
                return False

            # 下载音频文件
            if not only_lyrics:
                # 验证URL是否为空
                if not song_info.url:
                    self.log("api返回的URL为空, 请尝试更换音质或序号，或稍后再试")
                    return False

                temp_filepath = self._get_temp_filepath(song_info.url)
                if not await self.download_manager.download_with_progress(song_info.url, temp_filepath):
                    return False

                # 处理音频文件
                success = await self._process_audio_file(temp_filepath, song_info, download_lyrics, embed_lyrics)
                return success
            else:
                final_filename = self._get_final_filename(song_info)
                success, _ = await self.lyrics_manager.download_lyrics_from_qq(
                    song_info.songmid,
                    audio_filename=final_filename
                )
                return success

        except Exception as e:
            self.log(f"下载失败: {str(e)}")
            return False

    def _get_temp_filepath(self, url: str) -> Path:
        """获取临时文件路径"""
        ext = self._get_audio_extension(url)
        return config.DOWNLOADS_DIR / f"temp_{int(time.time())}{ext}"

    async def _process_audio_file(self, temp_filepath: Path, song_info: SongInfo,
                                  download_lyrics: bool, embed_lyrics: bool) -> bool:
        """处理下载的音频文件"""
        try:
            # 添加封面
            if song_info.cover:
                self.log("正在添加封面...")
                async with aiohttp.ClientSession() as session:
                    async with session.get(song_info.cover) as response:
                        cover_data = await response.read()
                        AudioHandler(temp_filepath).add_cover(cover_data)

            # 处理歌词
            if download_lyrics or embed_lyrics:
                self.log("正在获取歌词...")
                lyrics_success, lyrics_content = await self.lyrics_manager.download_lyrics_from_qq(
                    song_info.songmid,
                    return_content=True
                )

                if lyrics_success:
                    if embed_lyrics:
                        self.log("正在嵌入歌词...")
                        AudioHandler(temp_filepath).add_lyrics(lyrics_content)

                    if download_lyrics:
                        final_filename = self._get_final_filename(song_info)  # 获取完整文件名
                        await self.lyrics_manager.download_lyrics_from_qq(
                            song_info.songmid,
                            audio_filename=final_filename
                        )

            # 重命名文件
            final_filename = self._get_final_filename(song_info)
            final_filepath = config.DOWNLOADS_DIR / final_filename
            
            # 如果文件已存在，添加序号
            counter = 1
            while final_filepath.exists():
                base_name = Path(final_filename).stem
                ext = Path(final_filename).suffix
                final_filepath = config.DOWNLOADS_DIR / f"{base_name} ({counter}){ext}"
                counter += 1
            
            temp_filepath.rename(final_filepath)
            self.log(f"下载完成！保存在: {final_filepath}")

            return True

        except Exception as e:
            self.log(f"处理音频文件时出错: {str(e)}")
            return False

    def _get_final_filename(self, song_info: SongInfo) -> str:
        """获取最终文件名（包含扩展名）"""
        # 基础文件名（不含扩展名）
        base_filename = f"{song_info.song} - {song_info.singer}"
        # 移除文件名中的非法字符
        base_filename = "".join(c if c not in r'<>:"/\|?*' else ' ' for c in base_filename)
        # 获取并添加正确的文件扩展名
        ext = self._get_audio_extension(song_info.url)
        return f"{base_filename}{ext}"

    @staticmethod
    def _get_audio_extension(url: str) -> str:
        """从URL获取正确的音频文件扩展名"""
        # 首先尝试从URL路径获取扩展名
        ext = Path(urlparse(url).path).suffix.lower()

        # 如果URL中没有扩展名，则根据URL中的关键字判断
        if not ext:
            if 'flac' in url.lower():
                ext = '.flac'
            elif 'm4a' in url.lower():
                ext = '.m4a'
            elif 'mp3' in url.lower():
                ext = '.mp3'
            else:
                # 默认使用mp3
                ext = '.mp3'

        # 确保扩展名是受支持的格式
        supported_extensions = {'.mp3', '.flac', '.m4a'}
        if ext not in supported_extensions:
            ext = '.mp3'  # 默认使用mp3

        return ext

    async def _get_song_info(self, keyword: str, n: int, quality: int) -> Optional[SongInfo]:
        return await self.info_fetcher.get_song_info(keyword, n, quality)


class BatchDownloader(MusicDownloader):
    def __init__(self, callback: Optional[Callable] = None):
        super().__init__(callback)
        self.existing_songs: Set[str] = set()

    @ensure_downloads_dir
    async def download_from_file(self, filename: Union[str, Path], quality: int = 11,
                                 download_lyrics: bool = False, embed_lyrics: bool = False,
                                 only_lyrics: bool = False) -> None:
        """从文件批量下载歌曲"""
        try:
            self.log("开始批量下载...")
            self.log(f"读取文件: {filename}")
            songs = self._read_song_list(filename)
            self.existing_songs = self._get_existing_songs()

            total = len(songs)
            success = 0
            failed = []
            skipped = []

            self.log(f"共找到 {total} 首歌曲")

            for i, song in enumerate(songs, 1):
                if not song.strip():
                    continue

                song_name = song.split(' - ')[0].strip()
                if song_name in self.existing_songs:
                    self.log(f" [{i}/{total}] 歌曲已存在,跳过: {song}")
                    skipped.append(song)
                    continue

                self.log(f"\n[{i}/{total}] 处理: {song}")
                if await self.download_song(song, quality=quality,
                                            download_lyrics=download_lyrics,
                                            embed_lyrics=embed_lyrics,
                                            only_lyrics=only_lyrics):
                    success += 1
                    self.existing_songs.add(song_name)
                else:
                    failed.append(song)

            self._report_results(success, failed, skipped)

        except Exception as e:
            self.log(f"批量下载出错: {str(e)}")

    @staticmethod
    def _read_song_list(filename: Union[str, Path]) -> List[str]:
        """读取歌曲列表文件"""
        encodings = ["utf-8", "gbk", "gb2312", "ansi"]
        for encoding in encodings:
            try:
                with open(filename, "r", encoding=encoding) as f:
                    return [line.strip() for line in f if line.strip()]
            except UnicodeDecodeError:
                continue
        raise UnicodeDecodeError("无法使用任何支持的编码读取文件")

    @staticmethod
    def _get_existing_songs() -> Set[str]:
        """获取已存在的歌曲"""
        return Config.DOWNLOADS_DIR.exists() and {
            filename.split(' - ')[0].strip()
            for filename in os.listdir(Config.DOWNLOADS_DIR)
            if filename.endswith(('.mp3', '.flac'))
        } or set()

    def _report_results(self, success: int, failed: List[str], skipped: List[str]):
        """报告下载结果"""
        if failed:
            self.log("\n以下歌曲下载失败:")
            for song in failed:
                self.log(f"- {song}")

        if skipped:
            self.log("\n以下歌曲已存在(已跳过):")
            for song in skipped:
                self.log(f"- {song}")

        self.log(f"\n下载完成！")
        self.log(f"成功: {success}")
        self.log(f"失败: {len(failed)}")
        self.log(f"跳过: {len(skipped)}")


def main():
    parser = argparse.ArgumentParser(description='下载QQ音乐歌曲')
    parser.add_argument('input', help='要下载的歌曲名称或歌曲列表文件')
    parser.add_argument('-f', '--file', action='store_true', help='从文件读取歌曲列表')
    parser.add_argument('-n', type=int, default=1, help='搜索结果的序号（可选）')
    parser.add_argument('-q', type=int, default=11, choices=range(1, 15),
                        help='音质，范围1-14，从差到好（可选）')
    parser.add_argument('--lyrics', action='store_true', help='下载歌词文件')
    parser.add_argument('--embed-lyrics', action='store_true', help='嵌入歌词到音频文件')

    args = parser.parse_args()

    import asyncio
    if args.file:
        downloader = BatchDownloader()
        asyncio.run(downloader.download_from_file(
            args.input,
            quality=args.q,
            download_lyrics=args.lyrics,
            embed_lyrics=args.embed_lyrics
        ))
    else:
        downloader = MusicDownloader()
        asyncio.run(downloader.download_song(
            args.input,
            args.n,
            args.q,
            download_lyrics=args.lyrics,
            embed_lyrics=args.embed_lyrics
        ))


if __name__ == "__main__":
    main()
