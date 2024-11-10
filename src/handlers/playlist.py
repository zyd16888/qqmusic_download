import aiohttp
from typing import Optional, Callable
from urllib.parse import urlparse

from ..core.metadata import SongInfo

class MusicInfoFetcher:
    """音乐信息获取类"""
    def __init__(self, callback: Optional[Callable] = None):
        self.callback = callback or print

    def log(self, message: str):
        """日志输出"""
        self.callback(message)

    async def get_song_info(self, keyword: str, n: int = 1, quality: int = 11) -> Optional[SongInfo]:
        """获取歌曲信息"""
        base_url = 'https://api.lolimi.cn/API/qqdg/'
        params = {'word': keyword, 'n': n, 'q': quality}

        try:
            self.log(f"正在获取 {keyword} 的歌曲信息, 序号: {n}, 音质: {quality}")
            async with aiohttp.ClientSession() as session:
                async with session.get(base_url, params=params) as response:
                    data = await response.json()

                    if data['code'] != 200:
                        self.callback(f"获取歌曲信息失败: {data.get('msg', '未知错误')}")
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

    async def get_playlist_songs(self, url: str) -> 'list[str]':
        """从URL获取歌单列表"""
        try:
            api_url = "https://sss.unmeta.cn/songlist"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://music.unmeta.cn/"
            }
            data = {"url": url}

            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, data=data, headers=headers) as response:
                    if response.status != 200:
                        raise Exception(f"API请求失败: {response.status}")

                    response_data = await response.json()
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