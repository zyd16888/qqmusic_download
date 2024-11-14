import os
from typing import Set
from pathlib import Path

class SongScanner:
    """歌曲扫描器，用于检查已存在的歌曲"""
    
    @staticmethod
    def get_existing_songs(downloads_dir: Path, downloads_file: Path) -> Set[str]:
        """获取所有已存在的歌曲"""
        folder_songs = SongScanner._get_existing_songs_from_folder(downloads_dir)
        file_songs = SongScanner._get_existing_songs_from_file(downloads_file)
        return folder_songs | file_songs

    @staticmethod
    def _get_existing_songs_from_folder(downloads_dir: Path) -> Set[str]:
        """获取下载目录中已存在的歌曲"""
        return downloads_dir.exists() and {
            filename.split(' - ')[0].strip()
            for filename in os.listdir(downloads_dir)
            if filename.endswith(('.mp3', '.flac'))
        } or set()

    @staticmethod
    def _get_existing_songs_from_file(downloads_file: Path) -> Set[str]:
        """获取下载记录文件中已存在的歌曲"""
        if downloads_file.exists():
            with open(downloads_file, 'r', encoding='utf-8') as f:
                return {line.split(' - ')[0].strip() for line in f if line.endswith(('.mp3\n', '.flac\n'))}
        return set() 