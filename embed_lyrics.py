from mutagen.mp3 import MP3
from mutagen.id3 import ID3, USLT
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
import os

def read_lrc_file(lrc_path):
    """读取 LRC 文件内容"""
    try:
        with open(lrc_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        # 如果 UTF-8 读取失败，尝试使用 GBK 编码
        with open(lrc_path, 'r', encoding='gbk') as f:
            return f.read()

def embed_lyrics(audio_path, lyrics):
    """将歌词嵌入不同格式的音频文件"""
    file_ext = os.path.splitext(audio_path)[1].lower()
    
    try:
        if file_ext == '.mp3':
            # 处理 MP3 文件
            try:
                audio = ID3(audio_path)
            except:
                audio = ID3()
            
            audio["USLT"] = USLT(encoding=3, lang="chi", desc="", text=lyrics)
            audio.save(audio_path)
            
        elif file_ext == '.flac':
            # 处理 FLAC 文件
            audio = FLAC(audio_path)
            audio["LYRICS"] = lyrics
            audio.save()
            
        elif file_ext == '.m4a':
            # 处理 M4A 文件
            audio = MP4(audio_path)
            audio["\xa9lyr"] = lyrics
            audio.save()
            
        print(f"✓ 成功将歌词嵌入到文件: {os.path.basename(audio_path)}")
        
    except Exception as e:
        print(f"✗ 处理文件 {os.path.basename(audio_path)} 时发生错误: {str(e)}")

def process_directory(directory):
    """处理指定目录下的所有音频文件"""
    supported_formats = ('.mp3', '.flac', '.m4a')
    processed_count = 0
    error_count = 0
    
    for root, _, files in os.walk(directory):
        for filename in files:
            if filename.lower().endswith(supported_formats):
                audio_path = os.path.join(root, filename)
                lrc_path = os.path.splitext(audio_path)[0] + '.lrc'
                
                if os.path.exists(lrc_path):
                    try:
                        lyrics = read_lrc_file(lrc_path)
                        embed_lyrics(audio_path, lyrics)
                        processed_count += 1
                    except Exception as e:
                        print(f"✗ 处理文件 {filename} 时发生错误: {str(e)}")
                        error_count += 1
                else:
                    print(f"- 跳过 {filename}: 找不到对应的 .lrc 文件")
    
    return processed_count, error_count

def main():
    # 指定要处理的目录
    directory = input("请输入音频文件目录路径: ").strip()
    
    if not os.path.exists(directory):
        print("❌ 目录不存在！")
        return
    
    print("\n开始处理音频文件...")
    processed, errors = process_directory(directory)
    
    print("\n处理完成！")
    print(f"成功处理: {processed} 个文件")
    print(f"处理失败: {errors} 个文件")

if __name__ == "__main__":
    main() 