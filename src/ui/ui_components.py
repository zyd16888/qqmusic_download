import os
import sys

import flet as ft

from src.ui.constants import UIConstants
from src.core.config import Config


class UIComponents:
    def __init__(self, app):
        self.app = app
        self.constants = UIConstants()
        self._init_components()
        self._setup_fonts()
        self._create_layout()

    def _init_components(self):
        """初始化所有UI组件"""
        self._create_title_bar()
        self._create_single_download_components()
        self._create_batch_download_components()
        self._create_log_components()
        self._create_tabs()

    def _setup_fonts(self):
        """设置字体和窗口大小"""
        if getattr(sys, 'frozen', False):
            fonts_dir = os.path.join(sys._MEIPASS, 'fonts')
        else:
            fonts_dir = './fonts'

        self.app.page.fonts = {
            "可爱泡芙桃子酒": os.path.join(fonts_dir, "可爱泡芙桃子酒.ttf")
        }
        self.app.page.theme = ft.Theme(font_family="可爱泡芙桃子酒")
        self.app.page.window.width = 700
        self.app.page.window.height = 870

    def _create_title_bar(self):
        """创建标题栏"""
        self.title_bar = ft.WindowDragArea(
            content=ft.Container(
                content=ft.Row(
                    [
                        ft.Text("音乐下载器", size=18, weight=ft.FontWeight.BOLD),
                        ft.Text("免责声明：本软件仅供学习交流，请勿用于商业用途。", size=9, color=ft.colors.BLACK54),
                        ft.Container(expand=True),
                        ft.IconButton(
                            icon=ft.icons.REMOVE,
                            icon_color=ft.colors.BLACK54,
                            on_click=self.app.event_handler.on_minimize_window,
                            tooltip="最小化"
                        ),
                        ft.IconButton(
                            icon=ft.icons.CLOSE,
                            icon_color=ft.colors.BLACK54,
                            on_click=lambda _: self.app.page.window.destroy(),
                            tooltip="关闭"
                        ),
                    ],
                    spacing=10,
                ),
                padding=ft.padding.only(left=15, right=10),
                height=40,
            )
        )

    def _create_single_download_components(self):
        """创建单曲下载相关组件"""
        # 搜索输入框
        self.search_input = ft.TextField(
            label="歌曲名称",
            hint_text="请输入要下载的歌曲名称 可加上歌手名获取更加准确的结果",
            border_radius=8,
            expand=True
        )

        # 音质选择
        self.quality_dropdown = ft.Dropdown(
            label="音质选择",
            options=[ft.dropdown.Option(text=opt) for opt in self.constants.QUALITY_OPTIONS],
            value=self.constants.QUALITY_OPTIONS[2],
            border_radius=8,
            width=200,
            on_change=self.app.event_handler.on_quality_changed
        )

        self.custom_quality = ft.TextField(
            label="自定义音质",
            hint_text="1-14",
            border_radius=8,
            width=100,
            visible=False
        )

        # 搜索序号
        self.index_input = ft.TextField(
            label="搜索结果序号",
            value="1",
            border_radius=8,
            width=100,
            input_filter=ft.NumbersOnlyInputFilter()
        )

        # 歌词选项
        self.lyrics_radio = ft.RadioGroup(
            content=ft.Column([
                ft.Radio(value=value, label=text)
                for text, value in self.constants.LYRICS_OPTIONS
            ], spacing=0),
            value="no_lyrics"
        )

        # 下载按钮
        self.download_btn = ft.ElevatedButton(
            text="下载",
            on_click=self.app.event_handler.on_single_download,
            style=ft.ButtonStyle(
                color=ft.colors.WHITE,
                bgcolor=ft.colors.BLUE,
                padding=0,
            ),
            width=200,
            height=50,
            content=ft.Text("下载", size=16),
        )
        self.control_options = ft.Column(
            [
                ft.Text("控制选项", size=14),
                self.lyrics_radio,
            ],
            spacing=5,
            tight=True
        )
        self.path_info = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("路径信息:", size=16, color=ft.colors.GREY_600),
                    ft.Text(f"下载目录: {Config.DOWNLOADS_DIR}",
                            size=14, color=ft.colors.GREY_400),
                    ft.Text(f"日志目录: {Config.LOGS_DIR}",
                            size=14, color=ft.colors.GREY_400),
                ],
                spacing=5,
            ),
            padding=10,
            border=ft.border.all(0.5, ft.colors.GREY_300),
            border_radius=8,
            margin=ft.margin.only(left=20),
            alignment=ft.alignment.top_left
        )

    def _create_batch_download_components(self):
        """创建批量下载相关组件"""
        # 文件选择
        self.file_path_input = ft.TextField(
            label="歌单链接/歌单文件路径",
            read_only=False,
            hint_text="支持QQ音乐/网易云歌单链接 或 点击浏览按钮选择歌曲列表文件",
            border_radius=8,
            expand=True
        )

        self.file_picker = ft.FilePicker(
            on_result=self.app.event_handler.on_file_picked
        )
        self.app.page.overlay.append(self.file_picker)

        self.browse_btn = ft.ElevatedButton(
            "浏览",
            icon=ft.icons.FOLDER_OPEN,
            on_click=lambda _: self.file_picker.pick_files(
                allowed_extensions=["txt"],
                dialog_title="选择歌曲列表文件"
            )
        )

        # 批量下载音质选择
        self.batch_quality_dropdown = ft.Dropdown(
            label="音质选择",
            options=[ft.dropdown.Option(text=opt) for opt in self.constants.QUALITY_OPTIONS],
            value=self.constants.QUALITY_OPTIONS[2],
            border_radius=8,
            width=200,
            on_change=self.app.event_handler.on_batch_quality_changed
        )

        self.batch_custom_quality = ft.TextField(
            label="自定义音质",
            hint_text="1-14",
            border_radius=8,
            width=100,
            visible=False
        )

        # 重试选项
        self.retry_checkbox = ft.Checkbox(
            label="下载失败时自动降低音质重试",
            value=True,
        )

        # 批量下载歌词选项
        self.batch_lyrics_radio = ft.RadioGroup(
            content=ft.Column([
                ft.Radio(value=value, label=text)
                for text, value in self.constants.LYRICS_OPTIONS
            ], spacing=0),
            value="no_lyrics"
        )

        # 批量下载按钮
        self.batch_download_btn = ft.ElevatedButton(
            text="开始批量下载",
            on_click=self.app.event_handler.on_batch_download,
            style=ft.ButtonStyle(
                color=ft.colors.WHITE,
                bgcolor=ft.colors.BLUE,
                padding=3,
            ),
            width=200,
            height=50,
            content=ft.Text("开始批量下载", size=16),
        )

        self.stop_btn = ft.ElevatedButton(
            text="停止下载",
            on_click=self.app.event_handler.on_stop_download,
            disabled=True,
            style=ft.ButtonStyle(
                color=ft.colors.WHITE,
                bgcolor=ft.colors.RED,
                padding=3,
            ),
            width=150,
            height=50,
            content=ft.Text("停止下载", size=16),
        )
        self.batch_path_info = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("路径信息:", size=16, color=ft.colors.GREY_600),
                    ft.Text(f"下载目录: {Config.DOWNLOADS_DIR}",
                            size=14, color=ft.colors.GREY_400),
                    ft.Text(f"日志目录: {Config.LOGS_DIR}",
                            size=14, color=ft.colors.GREY_400),
                    ft.Text(f"歌单目录: {Config.PLAYLISTS_DIR}",
                            size=14, color=ft.colors.GREY_400),
                    ft.Text(f"报告目录: {Config.REPORTS_DIR}",
                            size=14, color=ft.colors.GREY_400),
                ],
                spacing=5,
            ),
            padding=10,
            border=ft.border.all(0.5, ft.colors.GREY_300),
            border_radius=8,
            margin=ft.margin.only(left=20)
        )

    def _create_log_components(self):
        """创建日志相关组件"""
        self.log_text = ft.Text(
            size=12,
            selectable=True,
            no_wrap=True,
            value=""
        )

        self.log_view = ft.ListView(
            [self.log_text],
            expand=1,
            spacing=10,
            auto_scroll=True
        )

    def _create_tabs(self):
        """创建标签页"""
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

    def _create_layout(self):
        """创建主布局"""
        log_container = ft.Container(
            content=self.log_view,
            border=ft.border.all(color=ft.colors.GREY_100),
            border_radius=8,
            padding=10,
            expand=True
        )

        self.app.page.add(
            ft.Column(
                [
                    self.title_bar,
                    ft.Column(
                        [
                            self.tabs,
                            ft.Container(
                                content=ft.Column(
                                    [
                                        ft.Text("下载日志", size=12, weight=ft.FontWeight.BOLD),
                                        log_container
                                    ],
                                    spacing=5,
                                ),
                                height=300,
                                padding=10,
                            )
                        ],
                        expand=True,
                        spacing=10
                    )
                ],
                expand=True,
                spacing=0
            )
        )

    def _create_single_download_view(self) -> ft.Container:
        """创建单曲下载视图"""
        return ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        content=self.search_input,
                        margin=ft.margin.only(bottom=10)
                    ),
                    ft.Container(
                        content=ft.Row(
                            [
                                self.quality_dropdown,
                                self.custom_quality,
                                self.index_input
                            ],
                            # alignment=ft.MainAxisAlignment.START,
                            alignment=ft.alignment.top_left,
                            spacing=10
                        ),
                        margin=ft.margin.only(bottom=10)
                    ),
                    ft.Container(
                        content=ft.Row(
                            [
                                self.control_options,
                                ft.Container(expand=True),
                                self.path_info
                            ]
                        ),
                        margin=ft.margin.only(bottom=15)
                    ),
                    ft.Container(
                        content=self.download_btn,
                        alignment=ft.alignment.center
                    )
                ],
                spacing=0
            ),
            margin=ft.margin.only(left=10, top=10, right=10),
            padding=ft.padding.only(left=10, top=0, right=10)
        )

    def _create_batch_download_view(self) -> ft.Container:
        """创建批量下载视图"""
        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [self.file_path_input, self.browse_btn],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                    ),
                    ft.Row(
                        [
                            self.batch_quality_dropdown,
                            self.batch_custom_quality,
                            self.retry_checkbox
                        ],
                        alignment=ft.MainAxisAlignment.START
                    ),
                    ft.Container(
                        content=ft.Row(
                            [
                                self.batch_lyrics_radio,
                                ft.Container(expand=True),
                                self.batch_path_info,
                            ]
                        ),
                        margin=ft.margin.only(bottom=15)
                    ),
                    ft.Row(
                        [self.batch_download_btn, self.stop_btn],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=10
                    )
                ],
                spacing=10
            ),
            margin=ft.margin.only(left=10, top=10, right=10),
            padding=ft.padding.only(left=10, top=0, right=10)
        )
