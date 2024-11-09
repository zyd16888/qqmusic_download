import asyncio
import logging
import os
import threading
from datetime import datetime
from typing import Optional

import flet as ft

from downscript import MusicDownloader, BatchDownloader


class MusicDownloaderApp:
    # Constants
    QUALITY_OPTIONS = [
        "标准音质",
        "HQ高音质",
        "无损音质",
        "母带",
        "其他"
    ]

    QUALITY_MAP = {
        "标准音质": 4,
        "HQ高音质": 8,
        "无损音质": 11,
        "母带": 14
    }

    LYRICS_OPTIONS = [
        ("仅下载音频", "no_lyrics"),
        ("仅下载歌词", "only_lyrics"),
        ("下载音频和歌词", "save_lyrics"),
        ("下载音频并嵌入歌词", "embed_only"),
        ("下载音频嵌入歌词并保存", "save_and_embed")
    ]

    def __init__(self, page: ft.Page):
        self.page = page
        self._init_variables()
        self._setup_logger()
        self._init_ui()

    def _init_variables(self) -> None:
        """Initialize variables"""
        self.stop_event = threading.Event()
        self.last_progress_line = None
        self.last_update_time = 0
        self.download_thread: Optional[threading.Thread] = None

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

    def _init_ui(self) -> None:
        """Initialize UI components"""
        self.page.title = "音乐下载器"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.window.width = 800
        self.page.window.height = 800

        # Create tabs
        self.tabs = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            tabs=[
                ft.Tab(
                    text="单曲下载",
                    content=self._create_single_download_view()
                ),
                ft.Tab(
                    text="批量下载",
                    content=self._create_batch_download_view()
                ),
            ],
            expand=1
        )

        # Create log view
        self.log_text = ft.TextField(
            multiline=True,
            read_only=True,
            min_lines=8,
            max_lines=8,
            border_color=ft.colors.GREY_400,
            text_size=14
        )

        # Main layout
        self.page.add(
            ft.Column(
                [
                    self.tabs,
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text("下载日志", size=16, weight=ft.FontWeight.BOLD),
                                self.log_text
                            ]
                        ),
                        padding=10,
                        border=ft.border.all(1, ft.colors.GREY_400),
                        border_radius=8,
                        margin=ft.margin.only(top=20)
                    )
                ],
                expand=True
            )
        )

    def _create_single_download_view(self) -> ft.Container:
        """Create single download view"""
        # Search input
        self.search_input = ft.TextField(
            label="歌曲名称",
            hint_text="请输入要下载的歌曲名称",
            border_radius=8,
            expand=True
        )

        # Quality selection
        self.quality_dropdown = ft.Dropdown(
            label="音质选择",
            options=[ft.dropdown.Option(text=opt) for opt in self.QUALITY_OPTIONS],
            value="无损音质",
            border_radius=8,
            width=200
        )

        self.custom_quality = ft.TextField(
            label="自定义音质",
            hint_text="1-14",
            border_radius=8,
            width=100,
            visible=False
        )

        def on_quality_changed(e):
            self.custom_quality.visible = self.quality_dropdown.value == "其他"
            self.page.update()

        self.quality_dropdown.on_change = on_quality_changed

        # Search index
        self.index_input = ft.TextField(
            label="搜索结果序号",
            value="1",
            border_radius=8,
            width=100,
            input_filter=ft.NumbersOnlyInputFilter()
        )

        # Lyrics options
        self.lyrics_radio = ft.RadioGroup(
            content=ft.Column([
                ft.Radio(value=value, label=text)
                for text, value in self.LYRICS_OPTIONS
            ]),
            value="no_lyrics"
        )

        # Download button
        self.download_btn = ft.ElevatedButton(
            text="下载",
            on_click=lambda _: self.download_single(),
            style=ft.ButtonStyle(
                color=ft.colors.WHITE,
                bgcolor=ft.colors.BLUE,
                padding=3,
            ),
            width=200,
            height=50,
        )

        return ft.Container(
            content=ft.Column(
                [
                    self.search_input,
                    ft.Row(
                        [
                            self.quality_dropdown, 
                            self.custom_quality,
                            self.index_input
                        ],
                        alignment=ft.MainAxisAlignment.START
                    ),
                    ft.Row(
                        [
                            ft.Container(
                                content=ft.Column(
                                    [
                                        ft.Text("歌词选项"),
                                        self.lyrics_radio
                                    ]
                                ),
                            )
                        ]
                    ),
                    ft.Container(
                        content=self.download_btn,
                        alignment=ft.alignment.center
                    )
                ],
                spacing=5
            ),
            padding=10
        )

    def _create_batch_download_view(self) -> ft.Container:
        """Create batch download view"""
        # File selection
        self.file_path_input = ft.TextField(
            label="歌列表文件",
            read_only=True,
            border_radius=8,
            expand=True
        )

        def pick_files_result(e: ft.FilePickerResultEvent):
            if e.files:
                self.file_path_input.value = e.files[0].path
                self.page.update()

        self.file_picker = ft.FilePicker(
            on_result=pick_files_result
        )
        self.page.overlay.append(self.file_picker)

        self.browse_btn = ft.ElevatedButton(
            "浏览",
            icon=ft.icons.FOLDER_OPEN,
            on_click=lambda _: self.file_picker.pick_files(
                allowed_extensions=["txt"],
                dialog_title="选择歌曲列表文件"
            )
        )

        # Quality selection
        self.batch_quality_dropdown = ft.Dropdown(
            label="音质选择",
            options=[ft.dropdown.Option(text=opt) for opt in self.QUALITY_OPTIONS],
            value="无损音质",
            border_radius=8,
            width=200
        )

        self.batch_custom_quality = ft.TextField(
            label="自定义音质",
            hint_text="1-14",
            border_radius=8,
            width=100,
            visible=False
        )

        def on_batch_quality_changed(e):
            self.batch_custom_quality.visible = self.batch_quality_dropdown.value == "其他"
            self.page.update()

        self.batch_quality_dropdown.on_change = on_batch_quality_changed

        # Lyrics options
        self.batch_lyrics_radio = ft.RadioGroup(
            content=ft.Column([
                ft.Radio(value=value, label=text)
                for text, value in self.LYRICS_OPTIONS
            ]),
            value="no_lyrics"
        )

        # Buttons
        self.batch_download_btn = ft.ElevatedButton(
            text="开始批量下载",
            on_click=lambda _: self.download_batch(),
            style=ft.ButtonStyle(
                color=ft.colors.WHITE,
                bgcolor=ft.colors.BLUE,
                padding=3,
            ),
            width=200,
            height=50,
        )

        self.stop_btn = ft.ElevatedButton(
            text="停止下载",
            on_click=lambda _: self.stop_download(),
            disabled=True,
            style=ft.ButtonStyle(
                color=ft.colors.WHITE,
                bgcolor=ft.colors.RED,
                padding=20
            )
        )

        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [self.file_path_input, self.browse_btn],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                    ),
                    ft.Row(
                        [self.batch_quality_dropdown, self.batch_custom_quality],
                        alignment=ft.MainAxisAlignment.START
                    ),
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text("歌词选项"),
                                self.batch_lyrics_radio
                            ]
                        )
                    ),
                    ft.Row(
                        [self.batch_download_btn, self.stop_btn],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=20
                    )
                ],
                spacing=10
            ),
            padding=10
        )

    def log_message(self, message: str) -> None:
        """Add log message to text field and log file"""

        def update_log():
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.log_text.value = f"{self.log_text.value or ''}\n[{timestamp}] {message}"
            self.logger.info(message)
            self.page.update()

        self.page.run_on_ui_thread(update_log)

    def download_single(self) -> None:
        """Handle single download"""
        try:
            song_name = self.search_input.value.strip()
            if not song_name:
                self.page.show_snack_bar(ft.SnackBar(content=ft.Text("请输入歌曲名称")))
                return

            self.download_btn.disabled = True
            self.page.update()

            self.download_thread = threading.Thread(
                target=self._run_async_download_single,
                args=(song_name,),
                daemon=True
            )
            self.download_thread.start()
        except Exception as e:
            self.log_message(f"启动下载线程时出错: {str(e)}")
            self.download_btn.disabled = False
            self.page.update()

    def _run_async_download_single(self, song_name: str) -> None:
        """Run async download task wrapper"""
        try:
            if os.name == "nt":
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            loop.run_until_complete(self._download_single_thread(song_name))
        except Exception as e:
            self.log_message(f"下载出错: {str(e)}")
        finally:
            loop.close()
            self.page.run_on_ui_thread(lambda: setattr(self.download_btn, 'disabled', False))
            self.page.update()

    async def _download_single_thread(self, song_name: str) -> None:
        """Single download thread"""
        try:
            lyrics_option = self.lyrics_radio.value
            downloader = MusicDownloader(callback=self.log_message)

            self.log_message(f"开始下载: {song_name}")
            quality = self._get_quality_value()
            if quality is None:
                return

            download_lyrics = lyrics_option in ("save_lyrics", "save_and_embed")
            embed_lyrics = lyrics_option in ("embed_only", "save_and_embed")

            success = await downloader.download_song(
                song_name,
                n=int(self.index_input.value),
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

    def download_batch(self) -> None:
        """Handle batch download"""
        try:
            file_path = self.file_path_input.value
            if not file_path or not os.path.exists(file_path):
                self.page.show_snack_bar(ft.SnackBar(content=ft.Text("请选择有效的歌曲列表文件")))
                return

            lyrics_option = self.batch_lyrics_radio.value
            quality = self._get_batch_quality_value()

            if lyrics_option != "only_lyrics":
                if quality is None:
                    return
            else:
                quality = 4

            self.stop_event.clear()
            self._set_batch_buttons_state(True)

            self.download_thread = threading.Thread(
                target=self._run_async_download_batch,
                args=(file_path, quality, lyrics_option),
                daemon=True
            )
            self.download_thread.start()
        except Exception as e:
            self.log_message(f"启动批量下载时出错: {str(e)}")
            self._set_batch_buttons_state(False)

    def _run_async_download_batch(
            self, file_path: str, quality: Optional[int], lyrics_option: str
    ) -> None:
        """Run async batch download task wrapper"""
        try:
            if os.name == "nt":
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            loop.run_until_complete(
                self._download_batch_thread(file_path, quality, lyrics_option)
            )
        except Exception as e:
            self.log_message(f"批量下载出错: {str(e)}")
        finally:
            loop.close()
            self.page.run_on_ui_thread(lambda: self._set_batch_buttons_state(False))
            self.page.update()

    async def _download_batch_thread(
            self, file_path: str, quality: Optional[int], lyrics_option: str
    ) -> None:
        """Batch download thread"""
        try:
            downloader = BatchDownloader(callback=self.log_message)

            download_lyrics = lyrics_option in ("save_lyrics", "save_and_embed")
            embed_lyrics = lyrics_option in ("embed_only", "save_and_embed")

            await downloader.download_from_file(
                file_path,
                quality=quality,
                download_lyrics=download_lyrics,
                embed_lyrics=embed_lyrics,
                only_lyrics=lyrics_option == "only_lyrics",
            )

        except Exception as e:
            self.log_message(f"批量下载出错: {str(e)}")

    def _set_batch_buttons_state(self, is_downloading: bool) -> None:
        """Set batch download buttons state"""
        self.batch_download_btn.disabled = is_downloading
        self.stop_btn.disabled = not is_downloading
        self.page.update()

    def _get_quality_value(self) -> Optional[int]:
        """Get quality value for single download"""
        return self._get_quality_value_common(self.quality_dropdown, self.custom_quality)

    def _get_batch_quality_value(self) -> Optional[int]:
        """Get quality value for batch download"""
        return self._get_quality_value_common(self.batch_quality_dropdown, self.batch_custom_quality)

    def _get_quality_value_common(self, dropdown: ft.Dropdown, custom_field: ft.TextField) -> Optional[int]:
        """Common method for getting quality value"""
        quality = dropdown.value
        if quality == "其他":
            try:
                value = int(custom_field.value)
                if 1 <= value <= 14:
                    return value
                raise ValueError()
            except ValueError:
                self.page.show_snack_bar(ft.SnackBar(content=ft.Text("请输入1-14之间的数字")))
                return None
        return self.QUALITY_MAP[quality]

    def stop_download(self) -> None:
        """Stop download"""
        if self.download_thread and self.download_thread.is_alive():
            self.stop_event.set()
            self.log_message("正在停止下载...")
            self.stop_btn.disabled = True
            self.page.update()


def main():
    def init(page: ft.Page):
        app = MusicDownloaderApp(page)

    ft.app(target=init)


if __name__ == "__main__":
    main()
