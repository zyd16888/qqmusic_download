from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict


def get_default_quality_map() -> Dict[str, int]:
    return {
        "标准音质": 4,
        "HQ高音质": 8,
        "无损音质": 11,
        "母带": 14
    }


@dataclass
class Config:
    """全局配置类"""
    DOWNLOADS_DIR: Path = field(default=Path('downloads'))
    DEFAULT_QUALITY: int = 11
    BLOCK_SIZE: int = 8192
    PROGRESS_UPDATE_INTERVAL: float = 0.5

    # 使用 default_factory 来处理可变默认值
    QUALITY_MAP: Dict[str, int] = field(default_factory=get_default_quality_map)

    def __post_init__(self):
        """确保下载目录存在"""
        self.DOWNLOADS_DIR.mkdir(exist_ok=True)


# 全局配置实例
config = Config()
