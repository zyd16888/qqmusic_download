import os
import threading
from typing import Optional, Callable, Set, List
from pathlib import Path

from .config import config
from .downloader import MusicDownloader
from ..handlers.playlist import PlaylistManager
from ..handlers.report import DownloadReportManager
from ..utils.decorators import ensure_downloads_dir


class BatchDownloader(MusicDownloader):
    """批量下载器"""

    def __init__(self, callback: Optional[Callable] = None, stop_event: Optional[threading.Event] = None,
                 auto_retry: bool = True):
        super().__init__(callback)
        self.existing_songs: Set[str] = set()
        self.stop_event = stop_event
        self.playlist_manager = PlaylistManager(callback)
        self.report_manager = DownloadReportManager(config.DOWNLOADS_DIR / 'download_reports', callback)
        self.auto_retry = auto_retry

    @ensure_downloads_dir
    async def download_from_file(self, file_path: str, quality: int = 11,
                                 download_lyrics: bool = False, embed_lyrics: bool = False,
                                 only_lyrics: bool = False) -> None:
        """从文件或URL批量下载歌曲"""
        try:
            self.log("开始批量下载...")
            playlist_name = None

            if file_path.startswith(('http://', 'https://')):
                self.log(f"正在获取歌单: {file_path}")
                songs = await self.playlist_manager.get_playlist_songs(file_path)
                if self.playlist_manager.current_playlist:
                    playlist_name = self.playlist_manager.current_playlist['name']
            else:
                self.log(f"读取文件: {file_path}")
                if not os.path.exists(file_path):
                    raise FileNotFoundError("找不到指定的文件")
                songs = self.playlist_manager.read_playlist_file(file_path)
                playlist_name = Path(file_path).stem

            if not songs:
                self.log("没有找到要下载的歌曲")
                return

            await self._process_songs(songs, quality, download_lyrics, embed_lyrics, only_lyrics, playlist_name)

        except Exception as e:
            self.log(f"批量下载出错: {str(e)}")

    async def _process_songs(self, songs: List[str], quality: int,
                             download_lyrics: bool, embed_lyrics: bool,
                             only_lyrics: bool, playlist_name: Optional[str] = None) -> None:
        """处理歌曲列表"""
        self.existing_songs = self._get_existing_songs()
        total = len(songs)
        success = 0
        success_list = []
        failed = []
        skipped = []

        self.log(f"共找到 {total} 首歌曲")

        for i, song in enumerate(songs, 1):
            if self.stop_event and self.stop_event.is_set():
                self.log("下载已停止")
                break

            if not song.strip():
                continue

            song_name = song.split(' - ')[0].strip()
            if song_name in self.existing_songs:
                self.log(f"[{i}/{total}] 歌曲已存在,跳过: {song}")
                skipped.append(song)
                continue

            self.log(f"[{i}/{total}] 处理: {song}")
            if await self.download_song(song, quality=quality,
                                        download_lyrics=download_lyrics,
                                        embed_lyrics=embed_lyrics,
                                        only_lyrics=only_lyrics):
                success += 1
                success_list.append(song)
                self.existing_songs.add(song_name)
            else:
                failed.append(song)

        # 保存下载报告
        download_results = {
            'total': total,
            'success': success_list,
            'failed': failed,
            'skipped': skipped,
            'quality': quality,
            'download_lyrics': download_lyrics,
            'embed_lyrics': embed_lyrics,
            'only_lyrics': only_lyrics
        }
        self._report_results(success, failed, skipped)
        self.report_manager.save_report(download_results, playlist_name)

    def _report_results(self, success: int, failed: List[str], skipped: List[str]):
        """报告下载结果"""
        if failed:
            self.log("下载失败的歌曲:")
            for song in failed:
                self.log(f"- {song}")

        if skipped:
            self.log("已跳过的歌曲:")
            for song in skipped:
                self.log(f"- {song}")

        self.log("下载统计:")
        self.log(f"成功: {success}")
        self.log(f"失败: {len(failed)}")
        self.log(f"跳过: {len(skipped)}")

    @staticmethod
    def _get_existing_songs() -> Set[str]:
        """获取已存在的歌曲"""
        return config.DOWNLOADS_DIR.exists() and {
            filename.split(' - ')[0].strip()
            for filename in os.listdir(config.DOWNLOADS_DIR)
            if filename.endswith(('.mp3', '.flac'))
        } or set()

    async def download_song(self, keyword: str, n: int = 1, quality: int = 11,
                            download_lyrics: bool = False, embed_lyrics: bool = False,
                            only_lyrics: bool = False) -> bool:
        """重写下载方法，添加重试逻辑"""
        if not self.auto_retry:
            return await super().download_song(keyword, n, quality, download_lyrics, embed_lyrics, only_lyrics)

        # 定义所有可用的音质等级(从高到低)
        all_quality_levels = [14, 13, 12, 11, 10, 9, 8, 7, 4]

        # 只使用小于等于指定音质的等级
        quality_levels = [q for q in all_quality_levels if q <= quality]
        if not quality_levels:
            quality_levels = [quality]  # 如果用户指定的音质不在预设列表中，只使用该音质

        for retry_quality in quality_levels:
            if self.stop_event and self.stop_event.is_set():
                return False

            self.log(f"尝试使用音质等级 {retry_quality} 下载...")
            success = await super().download_song(
                keyword, n, retry_quality, download_lyrics, embed_lyrics, only_lyrics
            )
            if success:
                return True

            if retry_quality != quality_levels[-1]:
                self.log("下载失败，尝试降低音质重试...")

        return False
