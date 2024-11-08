import requests
import os
import argparse
from urllib.parse import quote, urlparse
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC
from mutagen.flac import FLAC, Picture
from io import BytesIO
import time
import humanize  # 用于格式化文件大小
from concurrent.futures import ThreadPoolExecutor

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

def download_with_progress(url, filepath, callback=None):
    """带进度和速度显示的下载函数"""
    try:
        response = requests.get(url, stream=True)
        total_size = int(response.headers.get('content-length', 0))
        block_size = 8192  # 增加到 8KB
        downloaded = 0
        start_time = time.time()
        last_update_time = 0  # 上次更新时间
        
        with open(filepath, 'wb') as f:
            for data in response.iter_content(block_size):
                downloaded += len(data)
                f.write(data)
                
                # 每0.5秒更新一次进度
                current_time = time.time()
                if current_time - last_update_time >= 0.5:
                    duration = current_time - start_time
                    if duration > 0:
                        speed = downloaded / duration
                        progress = (downloaded / total_size * 100) if total_size else 0
                        
                        speed_text = humanize.naturalsize(speed) + '/s'
                        progress_text = f"{progress:.1f}%" if total_size else "未知"
                        
                        if callback:
                            callback(f"下载进度: {progress_text} | 速度: {speed_text}")
                            
                    last_update_time = current_time
        
        if callback:
            callback("下载完成！")
        return True
        
    except Exception as e:
        if callback:
            callback(f"下载出错: {str(e)}")
        return False

def download_lyrics(keyword, audio_filename, callback=None):
    """下载歌词的函数
    Args:
        keyword: 搜索关键词
        audio_filename: 音频文件名(不含路径)
        callback: 日志回调函数
    """
    def log(message):
        if callback:
            callback(message)
        print(message)
        
    url = f"https://api.lolimi.cn/API/wydg/?msg={keyword}&n=1"
    log(f"正在搜索歌词: {keyword}")
    
    try:
        response = requests.get(url)
        data = response.json()
        
        if data["code"] != 200:
            log(f"获取歌词失败: {data.get('msg', '未知错误')}")
            return False, f"获取歌词失败: {data.get('msg', '未知错误')}"
            
        log(f"找到歌词: {data['name']} - {data['author']}")
        
        # 使用音频文件名作为歌词文件名,仅改变扩展名
        lyrics_filename = os.path.splitext(audio_filename)[0] + '.lrc'
        output_file = os.path.join('downloads', lyrics_filename)
        
        log(f"正在保存歌词文件: {lyrics_filename}")
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"[ti:{data['name']}]\n")
            f.write(f"[ar:{data['author']}]\n")
            f.write(f"[by:lyrics.py]\n\n")
            
            lyric_count = 0
            for line in data["lyric"]:
                if line["name"].strip():
                    time = line.get("time", "00:00.00")
                    if ':' in time and '.' in time:
                        minutes, rest = time.split(':')
                        seconds, milliseconds = rest.split('.')
                        formatted_time = f"[{int(minutes):02d}:{int(seconds):02d}.{milliseconds[:2]}]"
                        f.write(f"{formatted_time}{line['name']}\n")
                    else:
                        f.write(f"[00:00.00]{line['name']}\n")
                    lyric_count += 1
                    
        log(f"歌词保存完成，共 {lyric_count} 行")
        return True, output_file
        
    except Exception as e:
        error_msg = f"下载歌词时出错: {str(e)}"
        log(error_msg)
        return False, error_msg

def download_song(keyword, n=1, q=11, callback=None, download_lyrics_flag=False):
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
            
            # 使用线程池来处理下载
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(download_with_progress, song_url, filepath, callback=log)
                result = future.result()  # 等待下载完成
                
                if result:
                    # 添加封面
                    if song_info.get('cover'):
                        log("正在添加封面...")
                        add_cover_to_audio(filepath, song_info['cover'])
                    
                    # 下载歌词 (使用文件名而不是搜索关键词)
                    if download_lyrics_flag:
                        log("正在下载歌词...")
                        lyrics_success, lyrics_result = download_lyrics(keyword, filename, callback=log)
                        if lyrics_success:
                            log(f"歌词下载成功: {lyrics_result}")
                        else:
                            log(f"歌词下载失败: {lyrics_result}")
                    
                    log(f"下载完成！保存在: {filepath}")
                    return True
                else:
                    return False
            
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

def download_from_file(filename, callback=None, stop_event=None, quality=11, download_lyrics_flag=False):
    """从文件中读取歌曲列表并下载
    Args:
        filename: 歌曲列表文件路径
        callback: 日志回调函数
        stop_event: 停止事件标志
        quality: 音质选项
        download_lyrics_flag: 是否下载歌词
    """
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
            if download_song(song, q=quality, callback=callback, download_lyrics_flag=download_lyrics_flag):
                success += 1
                existing_songs.add(song_name)  # 添加到已存在列表
            else:
                failed.append(song)
        
        # 准备失败列表文件路径
        failed_file = os.path.join(os.path.dirname(filename), 'failed_downloads.txt')
        
        if failed:
            log("\n以下歌曲下载失败:")
            # 写入失败列表到文件
            with open(failed_file, 'w', encoding='utf-8') as f:
                for song in failed:
                    f.write(f"{song}\n")
                    log(f"- {song}")
            log(f"\n失败列表已保存到: {failed_file}")
                
        if skipped:
            log("\n以下歌曲已存在(已跳过):")
            for song in skipped:
                log(f"- {song}")
        
        log(f"\n下载完成！")
        log(f"成功: {success}")
        log(f"失败: {len(failed)}")
        log(f"跳过: {len(skipped)}")

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
