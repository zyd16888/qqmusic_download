import asyncio
import os
import threading
from typing import Optional

import flet as ft

from src.core.batch_downloader import BatchDownloader
from src.core.downloader import MusicDownloader
from src.ui.constants import UIConstants


class EventHandler:
    def __init__(self, app):
        self.app = app
        self.constants = UIConstants()
        self.loop = None  # 用于异步任务
        self.selected_song_mid = None  # 添加这一行

    def on_minimize_window(self, _):
        """处理最小化窗口事件"""
        self.app.page.window.minimized = True
        self.app.page.update()

    def on_close_window(self, _):
        """处理关闭窗口事件"""
        self.app.page.window.destroy()

    def on_quality_changed(self, e):
        """处理音质选择变更事件"""
        self.app.ui.custom_quality.visible = self.app.ui.quality_dropdown.value == self.constants.QUALITY_OPTIONS[-1]
        self.app.page.update()

    def on_batch_quality_changed(self, e):
        """处理批量下载音质选择变更事件"""
        self.app.ui.batch_custom_quality.visible = self.app.ui.batch_quality_dropdown.value == \
                                                   self.constants.QUALITY_OPTIONS[-1]
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
                target=self._run_async_download_single,
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
                target=self._run_async_download_batch,
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
            self.app.log_message("正在停止下载... 等待当前歌曲处理完成后停止")
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

    def _setup_event_loop(self):
        """设置事件循环"""
        if os.name == "nt":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

        if self.loop is None or self.loop.is_closed():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

    async def _download_single_thread(self, song_name: str, mid: Optional[str] = None) -> None:
        """Single download thread"""
        try:
            lyrics_option = self.app.ui.lyrics_radio.value
            downloader = MusicDownloader(callback=self.app.log_message)

            self.app.log_message(f"开始下载: {song_name}")
            quality = self._get_quality_value()
            if quality is None:
                return

            download_lyrics = lyrics_option in ("save_lyrics", "save_and_embed")
            embed_lyrics = lyrics_option in ("embed_only", "save_and_embed")

            if mid:
                success = await downloader.download_song_by_mid(
                    mid,
                    quality=quality,
                    download_lyrics=download_lyrics,
                    embed_lyrics=embed_lyrics,
                    only_lyrics=lyrics_option == "only_lyrics",
                )
                self.selected_song_mid = None
            else:
                success = await downloader.download_song(
                    song_name,
                    n=int(self.app.ui.index_input.value),
                    quality=quality,
                    download_lyrics=download_lyrics,
                    embed_lyrics=embed_lyrics,
                    only_lyrics=lyrics_option == "only_lyrics",
                )

            if success:
                self.app.log_message(f"下载完成: {song_name}")
            else:
                self.app.log_message(f"下载失败: {song_name}")
        except Exception as e:
            self.app.log_message(f"下载出错: {str(e)}")
        finally:
            self.app.ui.download_btn.disabled = False
            self.app.ui.download_btn.style.bgcolor = ft.colors.BLUE
            self.app.page.update()

    def _run_async_download_single(self, song_name: str) -> None:
        """Run async download task wrapper"""
        try:
            self._setup_event_loop()
            self.loop.run_until_complete(
                self._download_single_thread(song_name, self.selected_song_mid)
            )
        except Exception as e:
            self.app.log_message(f"下载出错: {str(e)}")
        finally:
            self.app.ui.download_btn.disabled = False
            self.app.ui.download_btn.style.bgcolor = ft.colors.BLUE
            self.app.page.update()

    def _run_async_download_batch(
            self, file_path: str, quality: Optional[int], lyrics_option: str,
            auto_retry: bool = True
    ) -> None:
        try:
            self._setup_event_loop()
            downloader = BatchDownloader(
                callback=self.app.log_message,
                stop_event=self.app.stop_event,
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
            self.app.log_message(f"批量下载出错: {str(e)}")
        finally:
            self._set_batch_buttons_state(False)
            self.app.page.update()

    def on_search(self, e):
        """搜索按钮点击事件"""
        keyword = self.app.ui.search_input.value
        if not keyword:
            self.app.log_message("请输入搜索关键词")
            return

        self._setup_event_loop()
        downloader = MusicDownloader(callback=self.app.log_message)
        results = self.loop.run_until_complete(downloader.search_songs(keyword))

        # 只有在有搜索结果时才显示结果列表
        if results:
            self.app.ui.search_results.content.controls.clear()
            for result in results:
                self.app.ui.search_results.content.controls.append(
                    ft.TextButton(
                        text=result['display_text'],
                        on_click=lambda e, r=result: self.on_result_selected(e, r),
                        style=ft.ButtonStyle(
                            alignment=ft.alignment.center_left,
                            padding=ft.padding.only(top=2, bottom=2),
                        ),
                        width=self.app.ui.search_results.width - 40,
                    )
                )
            self.app.ui.search_results.visible = True
        else:
            self.app.ui.search_results.visible = False

        self.app.page.update()

    def on_result_selected(self, e, result):
        """搜索结果选择事件"""
        self.app.ui.search_input.value = result['input_value']
        self.app.ui.search_results.visible = False

        # 保存选中歌曲的 mid
        self.selected_song_mid = result.get('mid')

        self.app.page.update()
