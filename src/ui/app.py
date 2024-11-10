import asyncio
import logging
import os
import threading
from datetime import datetime
from typing import Optional

import flet as ft

from src.core.batch_downloader import BatchDownloader
from src.core.downloader import MusicDownloader
from src.ui.constants import UIConstants
from src.ui.event_handler import EventHandler
from src.ui.ui_components import UIComponents


class MusicDownloaderApp:
    def __init__(self, page: ft.Page):
        self.page = page
        # self.page.window.prevent_close = True
        # self.page.window.on_event = self.on_window_event
        # 隐藏原生标题栏
        self.page.window.title_bar_hidden = True

        self.constants = UIConstants()
        self.event_handler = EventHandler(self)
        self.ui = UIComponents(self)

        self._init_variables()
        self._setup_logger()

    def _init_variables(self) -> None:
        """Initialize variables"""
        self.stop_event = threading.Event()
        self.last_progress_line = None
        self.last_update_time = 0
        self.download_thread: Optional[threading.Thread] = None
        self.loop = None

    def _setup_logger(self) -> None:
        """Set up logging system"""
        if not os.path.exists('logs'):
            os.makedirs('logs')

        self.logger = logging.getLogger('MusicDownloader')
        self.logger.setLevel(logging.INFO)

        log_file = f'logs/download_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        fh = logging.FileHandler(log_file, encoding='utf-8')
        fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(fh)

    def log_message(self, message: str) -> None:
        """Add log message to text field and log file"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if "下载进度:" in message:
            lines = (self.ui.log_text.value or '').split('\n')
            if lines and "下载进度:" in lines[-1]:
                lines[-1] = f"[{timestamp}] {message}"
                self.ui.log_text.value = '\n'.join(filter(None, lines))
            else:
                new_value = f"{self.ui.log_text.value or ''}\n[{timestamp}] {message}".strip()
                self.ui.log_text.value = new_value
        else:
            new_value = f"{self.ui.log_text.value or ''}\n[{timestamp}] {message}".strip()
            self.ui.log_text.value = new_value

        self.logger.info(message)
        self.page.update()

    async def _download_single_thread(self, song_name: str) -> None:
        """Single download thread"""
        try:
            lyrics_option = self.ui.lyrics_radio.value
            downloader = MusicDownloader(callback=self.log_message)

            self.log_message(f"开始下载: {song_name}")
            quality = self.event_handler._get_quality_value()
            if quality is None:
                return

            download_lyrics = lyrics_option in ("save_lyrics", "save_and_embed")
            embed_lyrics = lyrics_option in ("embed_only", "save_and_embed")

            success = await downloader.download_song(
                song_name,
                n=int(self.ui.index_input.value),
                quality=quality,
                download_lyrics=download_lyrics,
                embed_lyrics=embed_lyrics,
                only_lyrics=lyrics_option == "only_lyrics",
            )

            if success:
                self.log_message(f"下载完成: {song_name}")
            else:
                self.log_message(f"下载失败: {song_name}")
        except Exception as e:
            self.log_message(f"下载出错: {str(e)}")
        finally:
            self.ui.download_btn.disabled = False
            self.ui.download_btn.style.bgcolor = ft.colors.BLUE
            self.page.update()

    def _run_async_download_single(self, song_name: str) -> None:
        """Run async download task wrapper"""
        try:
            if os.name == "nt":
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

            if self.loop is None or self.loop.is_closed():
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)

            self.loop.run_until_complete(self._download_single_thread(song_name))
        except Exception as e:
            self.log_message(f"下载出错: {str(e)}")
        finally:
            self.ui.download_btn.disabled = False
            self.ui.download_btn.style.bgcolor = ft.colors.BLUE
            self.page.update()

    def _run_async_download_batch(
            self, file_path: str, quality: Optional[int], lyrics_option: str,
            auto_retry: bool = True
    ) -> None:
        try:
            if os.name == "nt":
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

            if self.loop is None or self.loop.is_closed():
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)

            downloader = BatchDownloader(
                callback=self.log_message,
                stop_event=self.stop_event,
                auto_retry=auto_retry
            )

            download_lyrics = lyrics_option in ("save_lyrics", "save_and_embed")
            embed_lyrics = lyrics_option in ("embed_only", "save_and_embed")

            self.loop.run_until_complete(
                downloader.download_from_file(
                    file_path,
                    quality=quality,
                    download_lyrics=download_lyrics,
                    embed_lyrics=embed_lyrics,
                    only_lyrics=lyrics_option == "only_lyrics",
                )
            )

        except Exception as e:
            self.log_message(f"批量下载出错: {str(e)}")
        finally:
            self.event_handler._set_batch_buttons_state(False)
            self.page.update()

    def on_window_event(self, e: ft.WindowEvent):
        if e.data == "close":
            if self.loop and not self.loop.is_closed():
                self.loop.close()
            self.page.window.destroy()


def main():
    def init(page: ft.Page):
        app = MusicDownloaderApp(page)

    ft.app(target=init)


if __name__ == "__main__":
    main()
