from typing import Optional, Callable

from src.core.metadata import SongInfo
from src.core.network import network
from src.handlers.playlist import PlaylistManager


class MusicInfoFetcher:
    """音乐信息获取类"""

    def __init__(self, callback: Optional[Callable] = None):
        self.callback = callback or print
        self.playlist_manager = PlaylistManager(callback)

    def log(self, message: str):
        """日志输出"""
        self.callback(message)

    async def get_song_info(self, keyword: str, n: int = 1, quality: int = 11) -> Optional[SongInfo]:
        """获取歌曲信息"""
        base_url = 'https://api.lolimi.cn/API/qqdg/'
        params = {'word': keyword, 'n': n, 'q': quality}

        try:
            self.log(f"正在获取 {keyword} 的歌曲信息, 序号: {n}, 音质: {quality}")
            data = await network.async_get(base_url, params=params)

            if not data or data['code'] != 200:
                self.callback(f"获取歌曲信息失败: {data.get('msg', '未知错误') if data else '请求失败'}")
                return None

            song_data = data['data']
            songmid = song_data['link'].split('songmid=')[1].split('&')[0]

            return SongInfo(
                song=song_data['song'],
                singer=song_data['singer'],
                url=song_data['url'],
                cover=song_data.get('cover'),
                songmid=songmid
            )

        except Exception as e:
            self.callback(f"获取歌曲信息时出错: {str(e)}")
            return None
