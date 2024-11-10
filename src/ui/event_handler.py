import threading
from typing import Optional

import flet as ft


class EventHandler:
    def __init__(self, app):
        self.app = app

    def on_minimize_window(self, _):
        """处理最小化窗口事件"""
        self.app.page.window.minimized = True
        self.app.page.update()

    def on_close_window(self, _):
        """处理关闭窗口事件"""
        self.app.page.window.destroy()

    def on_quality_changed(self, e):
        """处理音质选择变更事件"""
        self.app.ui.custom_quality.visible = self.app.ui.quality_dropdown.value == "其他"
        self.app.page.update()

    def on_batch_quality_changed(self, e):
        """处理批量下载音质选择变更事件"""
        self.app.ui.batch_custom_quality.visible = self.app.ui.batch_quality_dropdown.value == "其他"
        self.app.page.update()

    def on_file_picked(self, e: ft.FilePickerResultEvent):
        """处理文件选择事件"""
        if e.files:
            self.app.ui.file_path_input.value = e.files[0].path
            self.app.page.update()

    def on_single_download(self, _):
        """处理单曲下载事件"""
        try:
            song_name = self.app.ui.search_input.value.strip()
            if not song_name:
                self.app.page.show_snack_bar(ft.SnackBar(content=ft.Text("请输入歌曲名称")))
                return

            self.app.ui.download_btn.disabled = True
            self.app.ui.download_btn.style.bgcolor = ft.colors.BLUE_200
            self.app.page.update()

            self.app.download_thread = threading.Thread(
                target=self.app._run_async_download_single,
                args=(song_name,),
                daemon=True
            )
            self.app.download_thread.start()
        except Exception as e:
            self.app.log_message(f"启动下载线程时出错: {str(e)}")
            self.app.ui.download_btn.disabled = False
            self.app.ui.download_btn.style.bgcolor = ft.colors.BLUE
            self.app.page.update()

    def on_batch_download(self, _):
        """处理批量下载事件"""
        try:
            file_path = self.app.ui.file_path_input.value
            if not file_path:
                self.app.page.show_snack_bar(ft.SnackBar(content=ft.Text("请输入歌单文件路径或歌单URL")))
                return

            lyrics_option = self.app.ui.batch_lyrics_radio.value
            quality = self._get_batch_quality_value()

            if lyrics_option != "only_lyrics":
                if quality is None:
                    return
            else:
                quality = 4

            self.app.stop_event.clear()
            self._set_batch_buttons_state(True)

            self.app.download_thread = threading.Thread(
                target=self.app._run_async_download_batch,
                args=(file_path, quality, lyrics_option, self.app.ui.retry_checkbox.value),
                daemon=True
            )
            self.app.download_thread.start()
        except Exception as e:
            self.app.log_message(f"启动批量下载时出错: {str(e)}")
            self._set_batch_buttons_state(False)

    def on_stop_download(self, _):
        """处理停止下载事件"""
        if self.app.download_thread and self.app.download_thread.is_alive():
            self.app.stop_event.set()
            self.app.log_message("正在停止下载...")
            self.app.ui.stop_btn.disabled = True
            self.app.ui.stop_btn.style.bgcolor = ft.colors.RED_200
            self.app.page.update()

    def _get_quality_value(self) -> Optional[int]:
        """获取单曲下载音质值"""
        return self._get_quality_value_common(
            self.app.ui.quality_dropdown,
            self.app.ui.custom_quality
        )

    def _get_batch_quality_value(self) -> Optional[int]:
        """获取批量下载音质值"""
        return self._get_quality_value_common(
            self.app.ui.batch_quality_dropdown,
            self.app.ui.batch_custom_quality
        )

    def _get_quality_value_common(self, dropdown: ft.Dropdown, custom_field: ft.TextField) -> Optional[int]:
        """通用的获取音质值方法"""
        quality = dropdown.value
        if quality == "其他":
            try:
                value = int(custom_field.value)
                if 1 <= value <= 14:
                    return value
                raise ValueError()
            except ValueError:
                self.app.page.show_snack_bar(ft.SnackBar(content=ft.Text("请输入1-14之间的数字")))
                return None
        return self.app.constants.QUALITY_MAP[quality]

    def _set_batch_buttons_state(self, is_downloading: bool) -> None:
        """设置批量下载按钮状态"""
        self.app.ui.batch_download_btn.disabled = is_downloading
        self.app.ui.batch_download_btn.style.bgcolor = ft.colors.BLUE_200 if is_downloading else ft.colors.BLUE
        self.app.ui.stop_btn.disabled = not is_downloading
        self.app.ui.stop_btn.style.bgcolor = ft.colors.RED if is_downloading else ft.colors.RED_200
        self.app.page.update()
