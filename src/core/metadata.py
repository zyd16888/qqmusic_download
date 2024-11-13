from dataclasses import dataclass
from typing import Optional


@dataclass
class AudioMetadata:
    """音频元数据类"""
    title: Optional[str]
    artist: Optional[str]


@dataclass
class SongInfo:
    """歌曲信息类"""
    song: str
    singer: str
    url: str
    cover: Optional[str]
    songmid: str
    quality: str
    size: str
