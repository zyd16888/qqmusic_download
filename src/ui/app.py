import logging
import os
import threading
from datetime import datetime
from typing import Optional

import flet as ft

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
