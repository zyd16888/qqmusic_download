from dataclasses import dataclass
from enum import Enum
from typing import List, Callable, Optional


class DownloadStatus(Enum):
    IDLE = "idle"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class DownloadState:
    status: DownloadStatus = DownloadStatus.IDLE
    progress: float = 0
    current_song: str = ""
    completed_count: int = 0
    failed_count: int = 0
    total_count: int = 0


@dataclass
class BatchDownloadState:
    file_path: str = ""
    quality: Optional[int] = None
    auto_retry: bool = True
    total_songs: int = 0
    current_index: int = 0


class AppState:
    def __init__(self):
        self._observers: List[Callable] = []
        self.download = DownloadState()
        self.batch = BatchDownloadState()
        self.is_custom_quality: bool = False
        self.is_batch_custom_quality: bool = False
        
    def add_observer(self, observer: Callable) -> None:
        if observer not in self._observers:
            self._observers.append(observer)
            
    def remove_observer(self, observer: Callable) -> None:
        if observer in self._observers:
            self._observers.remove(observer)
            
    def notify_observers(self) -> None:
        for observer in self._observers:
            observer(self)
            
    def update_download_state(self, **kwargs) -> None:
        for key, value in kwargs.items():
            if hasattr(self.download, key):
                setattr(self.download, key, value)
        self.notify_observers()
        
    def update_batch_state(self, **kwargs) -> None:
        for key, value in kwargs.items():
            if hasattr(self.batch, key):
                setattr(self.batch, key, value)
        self.notify_observers()