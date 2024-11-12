from datetime import datetime
from typing import Optional, Callable, List

from src.core.metadata import SongInfo
from src.core.models import SongResponse, SongData, SearchSongData, SearchResponse
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
            raw_data = await network.async_get(base_url, params=params)

            if not raw_data or raw_data['code'] != 200:
                self.callback(f"获取歌曲信息失败: {raw_data.get('msg', '未知错误') if raw_data else '请求失败'}")
                return None

            # 转换日期字符串为date对象
            raw_data['data']['time'] = datetime.strptime(raw_data['data']['time'], '%Y-%m-%d').date()

            # 使用新的数据模型
            response = SongResponse(
                code=raw_data['code'],
                data=SongData(**raw_data['data'])
            )

            songmid = response.data.link.split('songmid=')[1].split('&')[0]

            return SongInfo(
                song=response.data.song,
                singer=response.data.singer,
                url=response.data.url,
                cover=response.data.cover,
                songmid=songmid
            )

        except Exception as e:
            self.callback(f"获取歌曲信息时出错: {str(e)}")
            return None

    async def search_songs(self, keyword: str) -> List[SearchSongData]:
        """搜索歌曲
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            List[SearchSongData]: 搜索结果列表
        """
        base_url = 'https://api.lolimi.cn/API/qqdg/'
        params = {'word': keyword}

        try:
            self.log(f"正在搜索: {keyword}")
            raw_data = await network.async_get(base_url, params=params)

            if not raw_data or raw_data['code'] != 200:
                self.callback(f"搜索失败: {raw_data.get('msg', '未知错误') if raw_data else '请求失败'}")
                return []

            # 使用新的数据模型
            response = SearchResponse(
                code=raw_data['code'],
                data=[SearchSongData(**song_data) for song_data in raw_data['data']]
            )

            return response.data

        except Exception as e:
            self.callback(f"搜索歌曲时出错: {str(e)}")
            return []
