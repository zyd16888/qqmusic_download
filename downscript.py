import requests
import os
import argparse
from urllib.parse import quote, urlparse
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC
from mutagen.flac import FLAC, Picture
from io import BytesIO

def add_cover_to_audio(filepath, cover_url):
    # 下载封面
    try:
        cover_response = requests.get(cover_url)
        cover_data = cover_response.content
        
        # 根据文件扩展名处理不同格式
        if filepath.lower().endswith('.mp3'):
            try:
                audio = MP3(filepath, ID3=ID3)
                # 添加ID3标签如果不存在
                if audio.tags is None:
                    audio.add_tags()
                # 添加封面
                audio.tags.add(
                    APIC(
                        encoding=3,  # UTF-8
                        mime='image/jpeg',
                        type=3,  # 封面图片
                        desc='Cover',
                        data=cover_data
                    )
                )
                audio.save()
            except Exception as e:
                print(f"添加MP3封面时出错: {str(e)}")
                
        elif filepath.lower().endswith('.flac'):
            try:
                audio = FLAC(filepath)
                image = Picture()
                image.type = 3  # 封面图片
                image.mime = 'image/jpeg'
                image.desc = 'Cover'
                image.data = cover_data
                
                audio.add_picture(image)
                audio.save()
            except Exception as e:
                print(f"添加FLAC封面时出错: {str(e)}")
                
    except Exception as e:
        print(f"下载或处理封面图片时出错: {str(e)}")

def download_song(keyword, n=1, q=11, callback=None):
    # 修改所有 print 为回调函数调用
    def log(message):
        if callback:
            callback(message)
        print(message)
    
    # 创建downloads文件夹（如果不存在）
    if not os.path.exists('downloads'):
        os.makedirs('downloads')
    
    # 构建API URL
    base_url = 'https://api.lolimi.cn/API/qqdg/'
    params = {'word': keyword}
    if n:
        params['n'] = n
    if q:
        params['q'] = q
    log(f"请求参数: {params}")
    
    try:
        # 获取歌曲信息
        response = requests.get(base_url, params=params)
        data = response.json()

        log(data)
        
        if data['code'] == 200:
            song_info = data['data']
            song_url = song_info['url']
            
            # 从URL中获取文件扩展名
            file_extension = os.path.splitext(urlparse(song_url).path)[1]
            if not file_extension:
                if 'flac' in song_url.lower():
                    file_extension = '.flac'
                else:
                    file_extension = '.mp3'  # 默认为mp3
            
            # 构建文件名
            filename = f"{song_info['song']} - {song_info['singer']}{file_extension}"
            # 替换文件名中的非法字符
            filename = "".join(c if c not in r'<>:"/\|?*' else ' ' for c in filename)
            filepath = os.path.join('downloads', filename)
            
            # 下载歌曲
            log(f"正在下载: {filename}")
            log(f"音质: {song_info.get('quality', '未知')}")
            log(f"比特率: {song_info.get('kbps', '未知')}")
            
            song_response = requests.get(song_url)
            
            with open(filepath, 'wb') as f:
                f.write(song_response.content)
            
            # 添加封面
            if song_info.get('cover'):
                log("正在添加封面...")
                add_cover_to_audio(filepath, song_info['cover'])
            
            log(f"下载完成！保存在: {filepath}")
            return True
            
        else:
            log(f"获取歌曲信息失败: {data.get('msg', '未知错误')}")
            return False
            
    except Exception as e:
        log(f"发生错误: {str(e)}")
        return False

def get_existing_songs():
    """获取downloads目录下已存在的歌曲名称"""
    if not os.path.exists('downloads'):
        return set()
        
    existing_songs = set()
    for filename in os.listdir('downloads'):
        if filename.endswith(('.mp3', '.flac')):
            # 提取歌曲名(不包含歌手名)
            song_name = filename.split(' - ')[0].strip()
            existing_songs.add(song_name)
    return existing_songs

def download_from_file(filename, callback=None, stop_event=None, quality=11):
    """从文件中读取歌曲列表并下载"""
    def log(message):
        if callback:
            callback(message)
        print(message)
        
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            songs = f.read().splitlines()
            
        # 获取已存在的歌曲
        existing_songs = get_existing_songs()
        
        total = len(songs)
        success = 0
        failed = []
        skipped = []
        
        log(f"共找到 {total} 首歌曲")
        for i, song in enumerate(songs, 1):
            if stop_event and stop_event.is_set():
                log("\n下载已停止")
                break
                
            if not song.strip():  # 跳过空行
                continue
                
            # 提取歌曲名(不包含歌手名)
            song_name = song.split(' - ')[0].strip()
            
            # 检查是否已存在
            if song_name in existing_songs:
                log(f"\n[{i}/{total}] 歌曲已存在,跳过: {song}")
                skipped.append(song)
                continue
                
            log(f"\n[{i}/{total}] 正在下载: {song}")
            if download_song(song, q=quality, callback=callback):
                success += 1
                existing_songs.add(song_name)  # 添加到已存在列表
            else:
                failed.append(song)
        
        log(f"\n下载完成！")
        log(f"成功: {success}")
        log(f"失败: {len(failed)}")
        log(f"跳过: {len(skipped)}")
        
        if failed:
            log("\n以下歌曲下载失败:")
            for song in failed:
                log(f"- {song}")
                
        if skipped:
            log("\n以下歌曲已存在(已跳过):")
            for song in skipped:
                log(f"- {song}")
                
    except FileNotFoundError:
        log(f"找不到文件: {filename}")
    except Exception as e:
        log(f"读取文件时出错: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='下载QQ音乐歌曲')
    parser.add_argument('input', help='要下载的歌曲名称或歌曲列表文件')
    parser.add_argument('-f', '--file', action='store_true', help='从文件读取歌曲列表')
    parser.add_argument('-n', type=int, default=1, help='搜索结果的序号（可选）')
    parser.add_argument('-q', type=int, default=11, choices=range(1, 15), help='音质，范围1-14，从差到好（可选）')
    
    args = parser.parse_args()
    
    if args.file:
        download_from_file(args.input)
    else:
        download_song(args.input, args.n, args.q)

if __name__ == "__main__":
    main()
