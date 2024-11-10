import time
import aiohttp
import humanize
from pathlib import Path
from typing import Optional, Callable
from urllib.parse import urlparse

from .config import config
from .metadata import SongInfo
from ..handlers.audio import AudioHandler
from ..handlers.lyrics import LyricsManager
from ..handlers.playlist import MusicInfoFetcher
from ..utils.decorators import ensure_downloads_dir

class DownloadManager:
    """下载管理器"""
    def __init__(self, callback: Optional[Callable] = None):
        self.callback = callback or print

    def log(self, message: str):
        """日志输出"""
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
        """更新下载进度"""
        duration = current_time - start_time
        if duration > 0:
            speed = downloaded / duration
            progress = (downloaded / total_size * 100) if total_size else 0
            self.log(f"下载进度: {progress:.1f}% | 速度: {humanize.naturalsize(speed)}/s")


class MusicDownloader:
    """音乐下载器"""
    def __init__(self, callback: Optional[Callable] = None):
        self.callback = callback or print
        self.download_manager = DownloadManager(callback)
        self.lyrics_manager = LyricsManager(callback)
        self.info_fetcher = MusicInfoFetcher(callback)

    def log(self, message: str):
        """日志输出"""
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

            if not only_lyrics:
                if not song_info.url:
                    self.log("api返回的URL为空, 请尝试更换音质或序号，或稍后再试")
                    return False

                temp_filepath = self._get_temp_filepath(song_info.url)
                if not await self.download_manager.download_with_progress(song_info.url, temp_filepath):
                    return False

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

    async def _process_audio_file(self, temp_filepath: Path, song_info: SongInfo,
                                download_lyrics: bool, embed_lyrics: bool) -> bool:
        """处理下载的音频文件"""
        try:
            if song_info.cover:
                self.log("正在添加封面...")
                async with aiohttp.ClientSession() as session:
                    async with session.get(song_info.cover) as response:
                        cover_data = await response.read()
                        AudioHandler(temp_filepath).add_cover(cover_data)

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
                        final_filename = self._get_final_filename(song_info)
                        await self.lyrics_manager.download_lyrics_from_qq(
                            song_info.songmid,
                            audio_filename=final_filename
                        )

            final_filename = self._get_final_filename(song_info)
            final_filepath = config.DOWNLOADS_DIR / final_filename

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

    def _get_temp_filepath(self, url: str) -> Path:
        """获取临时文件路径"""
        ext = self._get_audio_extension(url)
        return config.DOWNLOADS_DIR / f"temp_{int(time.time())}{ext}"

    def _get_final_filename(self, song_info: SongInfo) -> str:
        """获取最终文件名"""
        base_filename = f"{song_info.song} - {song_info.singer}"
        base_filename = "".join(c if c not in r'<>:"/\|?*' else ' ' for c in base_filename)
        ext = self._get_audio_extension(song_info.url)
        return f"{base_filename}{ext}"

    @staticmethod
    def _get_audio_extension(url: str) -> str:
        """获取音频文件扩展名"""
        ext = Path(urlparse(url).path).suffix.lower()

        if not ext:
            if 'flac' in url.lower():
                ext = '.flac'
            elif 'm4a' in url.lower():
                ext = '.m4a'
            elif 'mp3' in url.lower():
                ext = '.mp3'
            else:
                ext = '.mp3'

        supported_extensions = {'.mp3', '.flac', '.m4a'}
        if ext not in supported_extensions:
            ext = '.mp3'

        return ext 