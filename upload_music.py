import asyncio

from src.core.config import Config
from src.services.music_upload_service import MusicUploadService


async def main():
    uploader = MusicUploadService(
        source_dir=Config.DOWNLOADS_DIR,
        remote_path="alist:/天翼云盘/",
        file_pattern="*.flac"
    )
    await uploader.start_upload()


if __name__ == "__main__":
    asyncio.run(main())
