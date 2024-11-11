import flet as ft
from src.ui.state.app_state import AppState, DownloadStatus


class UIStateHandler:
    def __init__(self, app):
        self.app = app
        
    def handle_state_change(self, state: AppState) -> None:
        """处理状态变化，更新UI"""
        self._update_download_buttons(state)
        self._update_progress(state)
        self._update_status(state)
        self._update_batch_status(state)
        self.app.page.update()
        
    def _update_download_buttons(self, state: AppState) -> None:
        """更新下载按钮状态"""
        is_downloading = state.download.status == DownloadStatus.DOWNLOADING
        
        # 单曲下载按钮
        self.app.ui.download_btn.disabled = is_downloading
        self.app.ui.download_btn.style.bgcolor = (
            ft.colors.BLUE_200 if is_downloading else ft.colors.BLUE
        )
        
        # 批量下载按钮
        self.app.ui.batch_download_btn.disabled = is_downloading
        self.app.ui.batch_download_btn.style.bgcolor = (
            ft.colors.BLUE_200 if is_downloading else ft.colors.BLUE
        )
        
        # 停止按钮
        self.app.ui.stop_btn.disabled = not is_downloading
        self.app.ui.stop_btn.style.bgcolor = (
            ft.colors.RED if is_downloading else ft.colors.RED_200
        )
        
    def _update_progress(self, state: AppState) -> None:
        """更新进度显示"""
        if state.download.progress > 0:
            self.app.log_message(f"下载进度: {state.download.progress:.1f}%")
            
    def _update_status(self, state: AppState) -> None:
        """更新状态信息"""
        if state.download.status == DownloadStatus.COMPLETED:
            self.app.log_message(
                f"下载完成 - 成功: {state.download.completed_count}, "
                f"失败: {state.download.failed_count}"
            )
        elif state.download.status == DownloadStatus.ERROR:
            self.app.log_message("下载出错") 
        
    def _update_batch_status(self, state: AppState) -> None:
        """更新批量下载状态"""
        if state.download.status == DownloadStatus.DOWNLOADING:
            # 更新进度信息
            if state.batch.total_songs > 0:
                progress = (state.batch.current_index / state.batch.total_songs) * 100
                self.app.log_message(
                    f"批量下载进度: {progress:.1f}% "
                    f"({state.batch.current_index}/{state.batch.total_songs})"
                )
            
            # 更新按钮状态
            self.app.ui.batch_download_btn.disabled = True
            self.app.ui.batch_download_btn.style.bgcolor = ft.colors.BLUE_200
            self.app.ui.stop_btn.disabled = False
            self.app.ui.stop_btn.style.bgcolor = ft.colors.RED
        else:
            # 重置按钮状态
            self.app.ui.batch_download_btn.disabled = False
            self.app.ui.batch_download_btn.style.bgcolor = ft.colors.BLUE
            self.app.ui.stop_btn.disabled = True
            self.app.ui.stop_btn.style.bgcolor = ft.colors.RED_200