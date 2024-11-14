import argparse
import asyncio
import sys
import platform
import logging
from datetime import datetime
from pathlib import Path
from src.core.downloader import MusicDownloader
from src.core.batch_downloader import BatchDownloader
from src.core.config import config

# Windows 平台特定的异步 IO 修复
if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

class CLILogger:
    def __init__(self):
        self.logger = self._setup_logger()
        self.last_progress = None
        
    def _setup_logger(self):
        """设置日志系统"""
        logger = logging.getLogger('MusicDownloader')
        logger.setLevel(logging.INFO)
        
        # 创建文件处理器
        log_file = config.LOGS_DIR / f'download_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(file_handler)
        
        return logger
    
    def log_message(self, message: str) -> None:
        """处理日志消息"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if "下载进度:" in message:
            # 使用 \r 来覆盖当前行显示进度
            print(f"\r[{timestamp}] {message}", end='', flush=True)
            self.last_progress = message
        else:
            # 如果上一条是进度消息，先打印换行
            if self.last_progress:
                print()
                self.last_progress = None
            # 其他消息正常打印并换行
            print(f"[{timestamp}] {message}")
            
        self.logger.info(message)

async def download_single(args):
    cli_logger = CLILogger()
    downloader = MusicDownloader(callback=cli_logger.log_message)
    
    success = await downloader.download_song(
        keyword=args.keyword,
        n=args.number,
        quality=args.quality,
        download_lyrics=args.lyrics,
        embed_lyrics=args.embed_lyrics,
        only_lyrics=args.only_lyrics
    )
    if success:
        print("\n下载完成！")
    else:
        print("\n下载失败！")

async def download_batch(args):
    cli_logger = CLILogger()
    downloader = BatchDownloader(callback=cli_logger.log_message)
    
    await downloader.download_from_file(
        file_path=args.file,
        quality=args.quality,
        download_lyrics=args.lyrics,
        embed_lyrics=args.embed_lyrics,
        only_lyrics=args.only_lyrics
    )

def main():
    parser = argparse.ArgumentParser(description='音乐下载器命令行工具')
    subparsers = parser.add_subparsers(dest='command', help='选择下载模式')

    # 单曲下载参数
    single_parser = subparsers.add_parser('single', help='单曲下载')
    single_parser.add_argument('keyword', help='歌曲关键词')
    single_parser.add_argument('-n', '--number', type=int, default=1, help='搜索结果序号，默认为1')
    single_parser.add_argument('-q', '--quality', type=int, default=11, help='音质等级(4-14)，默认为11')
    single_parser.add_argument('-l', '--lyrics', action='store_true', help='下载歌词')
    single_parser.add_argument('-e', '--embed-lyrics', action='store_true', help='嵌入歌词')
    single_parser.add_argument('--only-lyrics', action='store_true', help='仅下载歌词')

    # 批量下载参数
    batch_parser = subparsers.add_parser('batch', help='批量下载')
    batch_parser.add_argument('file', help='歌单文件路径或URL')
    batch_parser.add_argument('-q', '--quality', type=int, default=11, help='音质等级(4-14)，默认为11')
    batch_parser.add_argument('-l', '--lyrics', action='store_true', help='下载歌词')
    batch_parser.add_argument('-e', '--embed-lyrics', action='store_true', help='嵌入歌词')
    batch_parser.add_argument('--only-lyrics', action='store_true', help='仅下载歌词')

    args = parser.parse_args()

    if args.command == 'single':
        asyncio.run(download_single(args))
    elif args.command == 'batch':
        asyncio.run(download_batch(args))
    else:
        parser.print_help()

if __name__ == "__main__":
    main() 