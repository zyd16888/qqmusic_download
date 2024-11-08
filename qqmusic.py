import requests
import json
import html


def get_lyrics(songmid):
    # 歌词接口
    lyric_url = "https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg"
    
    # 构造请求参数
    params = {
        "nobase64": 1,
        "songmid": songmid,
        "platform": "yqq",
        "inCharset": "utf8",
        "outCharset": "utf-8",
        "g_tk": 5381
    }
    
    # 设置请求头
    headers = {
        "Referer": "https://y.qq.com/"
    }
    
    response = requests.get(lyric_url, params=params, headers=headers)
    
    # 处理返回数据
    lyric_data = response.text.strip('MusicJsonCallback(').strip(')')
    lyric_json = json.loads(lyric_data)
    print(lyric_json) # 打印原始返回数据
    
    # 获取原歌词和翻译
    original_lyric = html.unescape(html.unescape(lyric_json.get("lyric", "")))
    translate_lyric = html.unescape(html.unescape(lyric_json.get("trans", "")))
    
    return original_lyric, translate_lyric

def save_lyrics_to_lrc(original_lyric, translate_lyric, output_file):
    # 解析原文和翻译歌词
    original_lines = original_lyric.split('\n')
    translate_lines = translate_lyric.split('\n') if translate_lyric else []
    
    # 创建时间戳到歌词的映射
    lyrics_dict = {}
    
    # 处理原文歌词
    for line in original_lines:
        if line.startswith('[') and ']' in line:
            timestamp = line[:line.find(']')+1]
            content = line[line.find(']')+1:]
            lyrics_dict[timestamp] = {'original': content, 'translate': ''}
    
    # 处理翻译歌词
    for line in translate_lines:
        if line.startswith('[') and ']' in line:
            timestamp = line[:line.find(']')+1]
            content = line[line.find(']')+1:]
            if timestamp in lyrics_dict:
                lyrics_dict[timestamp]['translate'] = content
    
    # 按时间戳排序并写入文件
    with open(output_file, 'w', encoding='utf-8') as f:
        for timestamp in sorted(lyrics_dict.keys()):
            lyric_pair = lyrics_dict[timestamp]
            if lyric_pair['original'].strip():
                f.write(f"{timestamp}{lyric_pair['original']}\n")
                if lyric_pair['translate'].strip():
                    f.write(f"{timestamp}{lyric_pair['translate']}\n")

def main():
    
    try:
        songmid = "003aAYrm3GE0Ac"
        print(f"获取到 songmid: {songmid}")
        
        # 获取歌词
        original_lyric, translate_lyric = get_lyrics(songmid)
        
        print("\n原歌词:")
        print(original_lyric)
        
        if translate_lyric:
            print("\n翻译歌词:")
            print(translate_lyric)
            
        # 保存为lrc文件
        output_file = "output2.lrc"
        save_lyrics_to_lrc(original_lyric, translate_lyric, output_file)
        print(f"\n歌词已保存到: {output_file}")
            
    except Exception as e:
        print(f"发生错误: {str(e)}")

if __name__ == "__main__":
    main()
