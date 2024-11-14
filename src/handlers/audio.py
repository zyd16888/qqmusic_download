from pathlib import Path
from typing import Union, Optional, Callable

from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3, APIC, USLT, SYLT
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4, MP4Cover

from ..core.metadata import AudioMetadata


class AudioHandler:
    """音频处理类"""

    def __init__(self, filepath: Union[str, Path], callback: Optional[Callable] = None):
        self.filepath = Path(filepath)
        self.callback = callback or print
        self.audio = self._load_audio()

    def log(self, message: str):
        """日志输出"""
        self.callback(message)

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
            self.log("封面添加成功")
            return True
        except Exception as e:
            self.log(f"添加封面时出错: {str(e)}")
            return False

    def add_lyrics(self, lyrics: str) -> bool:
        """添加歌词"""
        try:
            ext = self.filepath.suffix.lower()
            if ext == '.mp3':
                if not hasattr(self.audio, 'tags'):
                    self.audio.add_tags()
                # 添加非同步歌词
                self.audio.tags["USLT"] = USLT(encoding=3, lang="chi", desc="", text=lyrics)
                # 添加同步歌词
                synced_lyrics = self._format_lyrics_with_timestamps(lyrics)
                if synced_lyrics:  # 只有在成功解析到同步歌词时才添加
                    self.audio.tags['SYLT'] = SYLT(encoding=3, lang="chi", desc="",
                                                 format=2,  # 2表示毫秒为单位
                                                 type=1,    # 1表示歌词
                                                 text=synced_lyrics)
            elif ext == '.flac':
                self.audio["LYRICS"] = lyrics
            elif ext == '.m4a':
                self.audio["\xa9lyr"] = lyrics

            self.audio.save()
            self.log("歌词添加成功")
            return True
        except Exception as e:
            self.log(f"添加歌词时出错: {str(e)}")
            return False

    def _format_lyrics_with_timestamps(self, lyrics: str) -> list:
        """将歌词格式化为 SYLT 所需的格式
        返回格式为: [(text, timestamp), ...]
        """
        result = []
        lines = lyrics.splitlines()
        for line in lines:
            if '[' in line and ']' in line:
                try:
                    time_part = line[1:line.find(']')]  # 提取时间戳
                    text = line[line.find(']')+1:].strip()  # 提取歌词文本
                    if text:  # 确保有歌词文本
                        # 将时间戳转换为毫秒
                        minutes, seconds = time_part.split(':')
                        timestamp = (int(minutes) * 60 + float(seconds)) * 1000
                        result.append((text, int(timestamp)))
                except:
                    continue
        return result

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
