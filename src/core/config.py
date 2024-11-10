from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, NamedTuple, List, Union


class QualityOption(NamedTuple):
    name: str
    value: Union[int, None]  # None 表示自定义值


def get_default_quality_options() -> List[QualityOption]:
    return [
        QualityOption("标准音质-192kbps(4)", 4),
        QualityOption("HQ高音质-320kbps(8)", 8),
        QualityOption("无损音质-FLAC(11)", 11),
        QualityOption("臻品母带-FLAC(14)", 14),
        QualityOption("自定义音质", None)  # 特殊选项
    ]


@dataclass
class Config:
    """全局配置类"""
    DOWNLOADS_DIR: Path = field(default=Path('downloads'))
    DEFAULT_QUALITY: int = 11
    BLOCK_SIZE: int = 8192
    PROGRESS_UPDATE_INTERVAL: float = 0.5

    # 使用 default_factory 来处理可变默认值
    QUALITY_OPTIONS: List[QualityOption] = field(default_factory=get_default_quality_options)

    @property
    def QUALITY_MAP(self) -> Dict[str, int]:
        return {opt.name: opt.value for opt in self.QUALITY_OPTIONS if opt.value is not None}

    def __post_init__(self):
        """确保下载目录存在"""
        self.DOWNLOADS_DIR.mkdir(exist_ok=True)


# 全局配置实例
config = Config()
