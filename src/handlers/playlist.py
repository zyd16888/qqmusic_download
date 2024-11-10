from datetime import datetime
from typing import Optional, Callable, Dict, List

from ..core.config import config
from ..core.network import network


class PlaylistManager:
    """歌单管理类"""

    def __init__(self, callback: Optional[Callable] = None):
        self.callback = callback or print
        self.playlist_dir = config.DOWNLOADS_DIR / 'playlist'
        self.download_report_dir = config.DOWNLOADS_DIR / 'download_reports'  # 新增下载报告目录
        self.playlist_dir.mkdir(exist_ok=True)
        self.download_report_dir.mkdir(exist_ok=True)  # 确保下载报告目录存在
        self.current_playlist: Dict = {}

    def log(self, message: str):
        """日志输出"""
        self.callback(message)

    async def save_playlist(self, playlist_info: Dict) -> None:
        """保存歌单信息"""
        try:
            if not playlist_info:
                return

            # 生成歌单文件名
            playlist_name = playlist_info.get('name', 'playlist')
            txt_file = self.playlist_dir / f"{playlist_name}.txt"

            # 保存为文本格式
            with open(txt_file, 'w', encoding='utf-8') as f:
                for song in playlist_info['songs']:
                    f.write(f"{song}\n")

            self.log(f"歌单文本已保存: {txt_file}")

        except Exception as e:
            self.log(f"保存歌单时出错: {str(e)}")

    def save_download_report(self, download_results: Dict) -> None:
        """保存下载报告"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = self.download_report_dir / f"download_report_{timestamp}.txt"  # 修改报告文件路径

            success = len(download_results['success'])
            failed = download_results['failed']
            skipped = download_results['skipped']

            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(f"下载时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"总数: {download_results['total']}\n")
                f.write(f"成功: {success}\n")
                f.write(f"失败: {len(failed)}\n")
                f.write(f"跳过: {len(skipped)}\n\n")

                if failed:
                    f.write("\n下载失败的歌曲:\n")
                    for song in failed:
                        f.write(f"- {song}\n")

                if skipped:
                    f.write("\n已跳过的歌曲:\n")
                    for song in skipped:
                        f.write(f"- {song}\n")

            self.log(f"\n下载报告已保存: {report_file}")

        except Exception as e:
            self.log(f"保存下载报告时出错: {str(e)}")

    @staticmethod
    def read_playlist_file(filename: str) -> List[str]:
        """读取歌单文件"""
        encodings = ["utf-8", "gbk", "gb2312", "ansi"]
        for encoding in encodings:
            try:
                with open(filename, "r", encoding=encoding) as f:
                    return [line.strip() for line in f if line.strip()]
            except UnicodeDecodeError:
                continue
        raise UnicodeDecodeError("无法使用任何支持的编码读取文件")
    async def get_playlist_songs(self, url: str) -> List[str]:
        """从URL获取歌单列表"""
        try:
            api_url = "https://sss.unmeta.cn/songlist"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://music.unmeta.cn/"
            }
            data = {"url": url}

            response_data = await network.async_post(api_url, data=data, headers=headers)

            if not response_data:
                raise Exception("API请求失败")

            if response_data["code"] != 1:
                raise Exception(f"获取歌单失败: {response_data['msg']}")

            playlist_name = response_data['data']['name']
            songs = response_data["data"]["songs"]
            songs_count = response_data['data']['songs_count']

            self.log(f"成功获取歌单，歌单名: {playlist_name}")
            self.log(f"歌单包含 {songs_count} 首歌曲")

            return songs

        except Exception as e:
            self.log(f"获取歌单失败: {str(e)}")
            return []


