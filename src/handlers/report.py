from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Callable
from ..utils.filename import sanitize_filename


class DownloadReportManager:
    """下载报告管理类"""

    def __init__(self, report_dir: Path, callback: Optional[Callable] = None):
        self.callback = callback or print
        self.report_dir = report_dir
        self.report_dir.mkdir(exist_ok=True)

    def log(self, message: str):
        """日志输出"""
        self.callback(message)

    def save_report(self, download_results: Dict, playlist_name: Optional[str] = None) -> None:
        """保存下载报告"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 如果提供了歌单名，使用歌单名作为报告文件名
            if playlist_name:
                safe_name = sanitize_filename(playlist_name)
                report_file = self.report_dir / f"{safe_name}_{timestamp}.txt"
            else:
                report_file = self.report_dir / f"download_report_{timestamp}.txt"

            success = download_results['success']
            failed = download_results['failed']
            skipped = download_results['skipped']

            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(f"下载时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                if playlist_name:
                    f.write(f"歌单名称: {playlist_name}\n")
                f.write(f"总数: {download_results['total']}\n")
                f.write(f"成功: {len(success)}\n")
                f.write(f"失败: {len(failed)}\n")
                f.write(f"跳过: {len(skipped)}\n\n")

                f.write("下载统计:\n")
                if success:
                    f.write(f"下载成功的歌曲: \n")
                    for song in success:
                        f.write(f"- {song}\n")

                if failed:
                    f.write("\n下载失败的歌曲:\n")
                    for song in failed:
                        f.write(f"- {song}\n")

                if skipped:
                    f.write("\n已跳过的歌曲:\n")
                    for song in skipped:
                        f.write(f"- {song}\n")

            self.log(f"下载报告已保存: {report_file}")

        except Exception as e:
            self.log(f"保存下载报告时出错: {str(e)}")
