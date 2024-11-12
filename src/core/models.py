from dataclasses import dataclass
from datetime import date
from typing import List


@dataclass
class SongResponse:
    """歌曲API返回数据模型"""
    code: int
    data: 'SongData'


@dataclass
class SongData:
    """歌曲详细信息数据模型"""
    id: int
    song: str
    subtitle: str
    singer: str
    album: str
    pay: str
    time: date
    bpm: int
    quality: str
    interval: str
    size: str
    kbps: str
    cover: str
    link: str
    url: str


@dataclass
class SearchSongData:
    """搜索结果歌曲数据模型"""
    id: int
    mid: str
    vid: str
    song: str
    cover: str
    subtitle: str
    singer: str
    album: str
    type: int
    grp: str


@dataclass
class SearchResponse:
    """搜索API返回数据模型"""
    code: int
    data: List[SearchSongData]
