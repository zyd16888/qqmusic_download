import asyncio
from datetime import datetime

from src.core.config import Config
from src.services.music_upload_service import MusicUploadService


async def run_upload():
    uploader = MusicUploadService(
        source_dir=Config.DOWNLOADS_DIR,
        remote_path="alist:/天翼云盘/music_upload/",
        file_pattern="*.flac"
    )
    await uploader.start_upload()


async def main():
    interval_minutes = 15  # 设置间隔时间（分钟）

    print(f"文件上传服务已启动，每{interval_minutes}分钟检查一次")
    while True:
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n[{current_time}] 开始检查文件...")

            await run_upload()

            print(f"等待 {interval_minutes} 分钟后进行下一次检查...")
            await asyncio.sleep(interval_minutes * 60)  # 转换为秒

        except KeyboardInterrupt:
            print("\n检测到退出信号，程序结束")
            break
        except Exception as e:
            print(f"发生错误: {str(e)}")
            print(f"等待 {interval_minutes} 分钟后重试...")
            await asyncio.sleep(interval_minutes * 60)


if __name__ == "__main__":
    asyncio.run(main())
