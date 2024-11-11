import re
import json
import requests
import time
import hashlib
from typing import Optional, Dict, List
from dataclasses import dataclass

@dataclass
class SongList:
    name: str
    songs: List[str]
    songs_count: int

class MusicParser:
    def __init__(self):
        # 正则表达式
        self.neteasy_pattern = re.compile(r'(163cn)|(.163.)')
        self.qqmusic_pattern = re.compile(r'.qq.')
        
        # QQ音乐相关正则
        self.qq_patterns = {
            'v1': re.compile(r'fcgi-bin'),
            'v2': re.compile(r'details'),
            'v3': re.compile(r'playlist'),
            'v4': re.compile(r'id=[89]\d{9}'),
            'v5': re.compile(r'.*playlist/7\d{9}$')
        }
        
        # API URLs
        self.qq_music_api = "https://u6.y.qq.com/cgi-bin/musics.fcg?sign={}&_={}"
        self.neteasy_api_v6 = "https://music.163.com/api/v6/playlist/detail"
        self.neteasy_api_v3 = "https://music.163.com/api/v3/song/detail"

    def parse_url(self, url: str) -> Optional[SongList]:
        """解析音乐链接"""
        if self.neteasy_pattern.search(url):
            return self.parse_neteasy(url)
        elif self.qqmusic_pattern.search(url):
            return self.parse_qqmusic(url)
        return None

    def parse_qqmusic(self, url: str) -> Optional[SongList]:
        """解析QQ音乐歌单"""
        tid = self._get_qqmusic_id(url)
        if not tid:
            return None
            
        # 尝试不同平台获取数据
        platforms = ["-1", "android", "iphone", "h5", "wxfshare", "iphone_wx", "windows"]
        
        # 简化请求头，只保留 Content-Type
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        for platform in platforms:
            # 构造请求参数
            param_string = self._get_qqmusic_req_string(tid, platform)
            sign = self._encrypt(param_string)
            api_url = self.qq_music_api.format(sign, int(time.time() * 1000))
            
            print(api_url)
            print(param_string)
            print(sign)
            try:
                response = requests.post(
                    api_url, 
                    data=param_string,
                    headers=headers
                )
                
                if response.status_code != 200:
                    continue
                    
                data = response.json()
                print(data)
                
                # 检查返回数据是否有效
                if len(response.content) == 108:
                    continue
                    
                if data.get('code') != 0 or data.get('req_0', {}).get('code') != 0:
                    continue
                    
                try:
                    songs = []
                    for song in data['req_0']['data']['songlist']:
                        song_name = self._standardize_name(song['name'])
                        artists = ' / '.join(singer['name'] for singer in song['singer'])
                        songs.append(f"{song_name} - {artists}")
                        
                    return SongList(
                        name=data['req_0']['data']['dirinfo']['title'],
                        songs=songs,
                        songs_count=data['req_0']['data']['dirinfo']['songnum']
                    )
                except (KeyError, TypeError):
                    continue
                    
            except Exception:
                continue
        
        return None

    def parse_neteasy(self, url: str) -> Optional[SongList]:
        """解析网易云歌单"""
        playlist_id = self._get_neteasy_id(url)
        if not playlist_id:
            return None
            
        # 获取歌单信息
        response = requests.post(self.neteasy_api_v6, data={'id': playlist_id})
        if response.status_code != 200:
            return None
            
        playlist_data = response.json()
        if playlist_data.get('code') == 401:
            return None
            
        # 获取歌曲详情
        song_ids = [{'id': track['id']} for track in playlist_data['playlist']['trackIds']]
        songs_response = requests.post(
            self.neteasy_api_v3, 
            data={'c': json.dumps(song_ids)}
        )
        
        if songs_response.status_code != 200:
            return None
            
        songs_data = songs_response.json()
        print(songs_data)
        songs = []
        for song in songs_data['songs']:
            song_name = self._standardize_name(song['name'])
            artists = ' / '.join(ar['name'] for ar in song['ar'])
            songs.append(f"{song_name} - {artists}")
            
        return SongList(
            name=playlist_data['playlist']['name'],
            songs=songs,
            songs_count=playlist_data['playlist']['trackCount']
        )

    def _get_qqmusic_id(self, url: str) -> Optional[int]:
        """
        从QQ音乐链接中提取歌单ID
        支持多种链接格式:
        1. https://y.qq.com/n/ryqq/playlist/7364061065
        2. https://i.y.qq.com/n2/m/share/details/taoge.html?id=9094523921
        3. https://c6.y.qq.com/base/fcgi-bin/u?__=4V33zWKDE3tI
        """
        # 处理 playlist/7xxxxxxxxx 格式
        if self.qq_patterns['v5'].match(url):
            try:
                index = url.find('playlist')
                if index < 0 or index + 19 > len(url):
                    return None
                return int(url[index+9:index+19])
            except (ValueError, IndexError):
                return None

        # 处理 id=8xxxxxxxxx 或 id=9xxxxxxxxx 格式
        if self.qq_patterns['v4'].search(url):
            try:
                index = url.find('id=')
                if index < 0 or index + 3 > len(url):
                    return None
                return int(url[index+3:index+13])
            except (ValueError, IndexError):
                return None

        # 处理短链接格式，需要获取重定向URL
        if self.qq_patterns['v1'].search(url):
            try:
                response = requests.head(url, allow_redirects=True)
                url = response.url
            except requests.RequestException:
                return None

        # 处理 details 格式链接
        if self.qq_patterns['v2'].search(url):
            try:
                # 从URL参数中获取id
                params = dict(param.split('=') for param in url.split('?')[1].split('&'))
                return int(params.get('id', '0'))
            except (ValueError, IndexError):
                return None

        # 处理 playlist 格式链接
        if self.qq_patterns['v3'].search(url):
            try:
                index = url.find('playlist')
                if index < 0 or index + 19 > len(url):
                    return None
                return int(url[index+9:index+19])
            except (ValueError, IndexError):
                return None

        return None

    def _get_neteasy_id(self, url: str) -> Optional[str]:
        """解析网易云歌单ID"""
        pattern = re.compile(r'playlist[/\?](?:id=)?(\d+)')
        match = pattern.search(url)
        return match.group(1) if match else None

    @staticmethod
    def _standardize_name(name: str) -> str:
        """标准化歌曲名称"""
        # 移除括号内容
        return re.sub(r'[\(（].*?[\)）]', '', name).strip()

    @staticmethod
    def _encrypt(param: str) -> str:
        """
        QQ音乐签名加密算法
        """
        # 初始化映射表
        k1 = {
            '0': 0, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
            'A': 10, 'B': 11, 'C': 12, 'D': 13, 'E': 14, 'F': 15
        }
        
        # 固定的加密数组
        l1 = [212, 45, 80, 68, 195, 163, 163, 203, 157, 220, 254, 91, 204, 79, 104, 6]
        
        # Base64字符表
        t = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="
        
        # 计算MD5
        md5_str = hashlib.md5(param.encode()).hexdigest().upper()
        
        # 提取特定位置的字符
        t1_indices = [21, 4, 9, 26, 16, 20, 27, 30]
        t3_indices = [18, 11, 3, 2, 1, 7, 6, 25]
        
        t1 = ''.join(md5_str[i] for i in t1_indices)
        t3 = ''.join(md5_str[i] for i in t3_indices)
        
        # 计算ls2数组
        ls2 = []
        for i in range(16):
            x1 = k1[md5_str[i * 2]]
            x2 = k1[md5_str[i * 2 + 1]]
            x3 = (x1 * 16 ^ x2) ^ l1[i]
            ls2.append(x3)
        
        # 生成t2字符串
        ls3 = []
        for i in range(6):
            if i == 5:
                ls3.append(t[ls2[-1] >> 2])
                ls3.append(t[(ls2[-1] & 3) << 4])
            else:
                x4 = ls2[i * 3] >> 2
                x5 = (ls2[i * 3 + 1] >> 4) ^ ((ls2[i * 3] & 3) << 4)
                x6 = (ls2[i * 3 + 2] >> 6) ^ ((ls2[i * 3 + 1] & 15) << 2)
                x7 = 63 & ls2[i * 3 + 2]
                ls3.append(t[x4] + t[x5] + t[x6] + t[x7])
        
        t2 = ''.join(ls3)
        # 使用与Go代码相同的替换方式
        t2 = re.sub(r'[\\/+]', '', t2)
        
        # 组合最终签名
        sign = 'zzb' + (t1 + t2 + t3).lower()
        return sign

    @staticmethod
    def _get_qqmusic_req_string(disstid: int, platform: str = "-1") -> str:
        """生成QQ音乐请求参数"""
        req_data = {
            "req_0": {
                "module": "music.srfDissInfo.aiDissInfo",
                "method": "uniform_get_Dissinfo",
                "param": {
                    "disstid": disstid,
                    "enc_host_uin": "",
                    "tag": 1,
                    "userinfo": 1,
                    "song_begin": 0,
                    "song_num": 1024
                }
            },
            "comm": {
                "g_tk": 5381,
                "uin": 0,
                "format": "json",
                "platform": platform
            }
        }
        
        return json.dumps(req_data, separators=(',', ':'))

def main():
    parser = MusicParser()
    
    # 网易云音乐示例
    # neteasy_url = "https://music.163.com/#/playlist?id=6845409713"
    # result = parser.parse_url(neteasy_url)
    # if result:
    #     print(f"歌单名称: {result.name}")
    #     print(f"歌曲数量: {result.songs_count}")
    #     print("歌曲列表:")
    #     for song in result.songs:
    #         print(f"- {song}")
            
    # QQ音乐示例
    qqmusic_url = "https://y.qq.com/n/ryqq/playlist/7275687885"
    result = parser.parse_url(qqmusic_url)
    if result:
        print(f"歌单名称: {result.name}")
        print(f"歌曲数量: {result.songs_count}")
        print("歌曲列表:")
        for song in result.songs:
            print(f"- {song}")

if __name__ == "__main__":
    main()
