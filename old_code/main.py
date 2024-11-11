import asyncio
import argparse
from src.core.downloader import MusicDownloader
from src.core.batch_downloader import BatchDownloader

def main():
    parser = argparse.ArgumentParser(description='下载QQ音乐歌曲')
    parser.add_argument('input', help='要下载的歌曲名称或歌曲列表文件')
    parser.add_argument('-f', '--file', action='store_true', help='从文件读取歌曲列表')
    parser.add_argument('-n', type=int, default=1, help='搜索结果的序号（可选）')
    parser.add_argument('-q', type=int, default=11, choices=range(1, 15),
                        help='音质，范围1-14，从差到好（可选）')
    parser.add_argument('--lyrics', action='store_true', help='下载歌词文件')
    parser.add_argument('--embed-lyrics', action='store_true', help='嵌入歌词到音频文件')

    args = parser.parse_args()

    if args.file:
        downloader = BatchDownloader()
        asyncio.run(downloader.download_from_file(
            args.input,
            quality=args.q,
            download_lyrics=args.lyrics,
            embed_lyrics=args.embed_lyrics
        ))
    else:
        downloader = MusicDownloader()
        asyncio.run(downloader.download_song(
            args.input,
            args.n,
            args.q,
            download_lyrics=args.lyrics,
            embed_lyrics=args.embed_lyrics
        ))

if __name__ == "__main__":
    main() 