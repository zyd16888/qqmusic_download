from typing import Optional, Callable, Dict, List

from ..core.config import config
from ..core.network import network
from ..utils.filename import sanitize_filename


class PlaylistManager:
    """歌单管理类"""

    def __init__(self, callback: Optional[Callable] = None):
        self.callback = callback or print
        self.playlist_dir = config.PLAYLISTS_DIR
        self.download_report_dir = config.REPORTS_DIR
        self.current_playlist: Dict = {}

    def log(self, message: str):
        """日志输出"""
        self.callback(message)

    async def save_playlist(self, playlist_info: Dict) -> None:
        """保存歌单信息"""
        try:
            if not playlist_info:
                return

            # 生成歌单文件名并处理非法字符
            playlist_name = playlist_info.get('name', 'playlist')
            safe_name = sanitize_filename(playlist_name)
            txt_file = self.playlist_dir / f"{safe_name}.txt"

            # 保存为文本格式
            with open(txt_file, 'w', encoding='utf-8') as f:
                for song in playlist_info['songs']:
                    f.write(f"{song}\n")

            self.log(f"歌单文本已保存: {txt_file}")

        except Exception as e:
            self.log(f"保存歌单时出错: {str(e)}")

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

            # 保存完整的歌单信息
            self.current_playlist = {
                'name': response_data['data']['name'],
                'songs': response_data["data"]["songs"],
                'songs_count': response_data['data']['songs_count']
            }

            self.log(f"成功获取歌单，歌单名: {self.current_playlist['name']}")
            self.log(f"歌单包含 {self.current_playlist['songs_count']} 首歌曲")

            # 保存歌单到文件
            await self.save_playlist(self.current_playlist)

            return self.current_playlist['songs']

        except Exception as e:
            self.log(f"获取歌单失败: {str(e)}")
            return []
