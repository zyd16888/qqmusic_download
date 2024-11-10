from pathlib import Path
from typing import Union

from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3, APIC, USLT
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4, MP4Cover

from ..core.metadata import AudioMetadata


class AudioHandler:
    """音频处理类"""

    def __init__(self, filepath: Union[str, Path]):
        self.filepath = Path(filepath)
        self.audio = self._load_audio()

    def _load_audio(self):
        """加载音频文件"""
        handlers = {
            '.mp3': lambda p: MP3(p, ID3=ID3),
            '.flac': FLAC,
            '.m4a': MP4
        }
        handler = handlers.get(self.filepath.suffix.lower())
        if not handler:
            raise ValueError(f"不支持的音频格式: {self.filepath.suffix}")
        return handler(self.filepath)

    def add_cover(self, cover_data: bytes, mime_type: str = 'image/jpeg') -> bool:
        """添加封面"""
        try:
            ext = self.filepath.suffix.lower()
            if ext == '.mp3':
                if not hasattr(self.audio, 'tags'):
                    self.audio.add_tags()
                self.audio.tags.add(
                    APIC(encoding=3, mime=mime_type, type=3, desc='Cover', data=cover_data)
                )
            elif ext == '.flac':
                image = Picture()
                image.type = 3
                image.mime = mime_type
                image.desc = 'Cover'
                image.data = cover_data
                self.audio.add_picture(image)
            elif ext == '.m4a':
                cover_format = MP4Cover.FORMAT_PNG if mime_type.endswith('png') else MP4Cover.FORMAT_JPEG
                self.audio.tags['covr'] = [MP4Cover(cover_data, imageformat=cover_format)]

            self.audio.save()
            return True
        except Exception as e:
            print(f"添加封面时出错: {str(e)}")
            return False

    def add_lyrics(self, lyrics: str) -> bool:
        """添加歌词"""
        try:
            ext = self.filepath.suffix.lower()
            if ext == '.mp3':
                if not hasattr(self.audio, 'tags'):
                    self.audio.add_tags()
                self.audio.tags["USLT"] = USLT(encoding=3, lang="chi", desc="", text=lyrics)
            elif ext == '.flac':
                self.audio["LYRICS"] = lyrics
            elif ext == '.m4a':
                self.audio["\xa9lyr"] = lyrics

            self.audio.save()
            return True
        except Exception as e:
            print(f"添加歌词时出错: {str(e)}")
            return False

    def get_metadata(self) -> AudioMetadata:
        """获取音频元数据"""
        try:
            ext = self.filepath.suffix.lower()
            if ext == '.mp3':
                return AudioMetadata(
                    title=str(self.audio.get('TIT2', [''])[0]),
                    artist=str(self.audio.get('TPE1', [''])[0])
                )
            elif ext == '.flac':
                return AudioMetadata(
                    title=self.audio.get('title', [''])[0] if self.audio.get('title') else None,
                    artist=self.audio.get('artist', [''])[0] if self.audio.get('artist') else None
                )
            elif ext == '.m4a':
                return AudioMetadata(
                    title=self.audio.get('\xa9nam', [''])[0] if self.audio.get('\xa9nam') else None,
                    artist=self.audio.get('\xa9ART', [''])[0] if self.audio.get('\xa9ART') else None
                )
        except Exception as e:
            print(f"读取元数据时出错: {str(e)}")
            return AudioMetadata(None, None)
