import requests
import json
import argparse
import sys

def download_lyrics(keyword, output_file=None):
    # API URL
    url = f"https://api.lolimi.cn/API/wydg/?msg={keyword}&n=1"
    
    try:
        # 发送请求
        response = requests.get(url)
        data = response.json()
        
        # 检查请求是否成功
        if data["code"] != 200:
            print(f"错误: {data.get('msg', '未知错误')}")
            return
        
        # 获取歌曲信息
        song_name = data["name"]
        author = data["author"]
        
        # 如果没有指定输出文件，使用歌名和歌手作为文件名，扩展名改为.lrc
        if not output_file:
            output_file = f"{song_name} - {author}.lrc"
        elif not output_file.endswith('.lrc'):
            output_file = f"{output_file}.lrc"
        
        # 打开文件准备写入
        with open(output_file, "w", encoding="utf-8") as f:
            # 写入LRC文件头信息
            f.write(f"[ti:{song_name}]\n")
            f.write(f"[ar:{author}]\n")
            f.write(f"[by:lyrics.py]\n\n")
            
            # 写入带时间轴的歌词
            for line in data["lyric"]:
                if line["name"].strip():  # 跳过空行
                    time = line.get("time", "00:00.00")
                    # 确保时间格式正确（分:秒.毫秒）
                    if ':' in time and '.' in time:
                        minutes, rest = time.split(':')
                        seconds, milliseconds = rest.split('.')
                        # 格式化时间，确保两位数
                        formatted_time = f"[{int(minutes):02d}:{int(seconds):02d}.{milliseconds[:2]}]"
                        f.write(f"{formatted_time}{line['name']}\n")
                    else:
                        # 如果没有时间信息，使用占位符
                        f.write(f"[00:00.00]{line['name']}\n")
        
        print(f"LRC歌词文件已保存到 {output_file}")
        
    except requests.exceptions.RequestException as e:
        print(f"网络请求错误: {e}")
        sys.exit(1)
    except json.JSONDecodeError:
        print("JSON解析错误")
        sys.exit(1)
    except Exception as e:
        print(f"发生错误: {e}")
        sys.exit(1)

def main():
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='下载网易云音乐歌词')
    parser.add_argument('keyword', help='要搜索的歌名')
    parser.add_argument('-o', '--output', help='输出文件名 (可选)')
    
    # 解析命令行参数
    args = parser.parse_args()
    
    # 下载歌词
    download_lyrics(args.keyword, args.output)

if __name__ == "__main__":
    main()
