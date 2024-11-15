import asyncio
from pathlib import Path
from typing import List


class MusicUploadService:
    def __init__(self,
                 source_dir: str,
                 remote_path: str = "alist:/天翼云盘/",
                 file_pattern: str = "*.flac"):
        self.source_dir = Path(source_dir)
        self.remote_path = remote_path
        self.file_pattern = file_pattern

    async def scan_files(self) -> List[Path]:
        """扫描指定目录下的所有FLAC文件及其对应的LRC文件，忽略temp开头的文件"""
        # 先获取所有flac文件
        flac_files = [f for f in self.source_dir.glob(self.file_pattern)
                      if not f.name.startswith('temp')]

        # 收集所有文件（包括flac和对应的lrc）
        all_files = []
        for flac_file in flac_files:
            all_files.append(flac_file)
            # 检查是否存在同名的lrc文件
            lrc_file = flac_file.with_suffix('.lrc')
            if lrc_file.exists():
                all_files.append(lrc_file)
                print(f"找到歌词文件: {lrc_file.name}")

        return all_files

    async def upload_file(self, file_path: Path) -> bool:
        """使用rclone上传单个文件"""
        try:
            cmd = ["rclone", "move", str(file_path), self.remote_path]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                print(f"成功上传文件: {file_path.name}")
                return True
            else:
                print(f"上传失败: {file_path.name}")
                print(f"错误信息: {stderr.decode()}")
                return False
        except Exception as e:
            print(f"上传过程出错: {str(e)}")
            return False

    async def start_upload(self):
        """开始上传流程"""
        try:
            files = await self.scan_files()
            if not files:
                print("没有找到需要上传的文件")
                return

            flac_count = sum(1 for f in files if f.suffix == '.flac')
            lrc_count = sum(1 for f in files if f.suffix == '.lrc')
            print(f"找到 {flac_count} 个FLAC文件和 {lrc_count} 个LRC文件待上传")

            for file in files:
                await self.upload_file(file)

        except Exception as e:
            print(f"上传服务出错: {str(e)}")
