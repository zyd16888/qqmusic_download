from functools import wraps
from ..core.config import config

def ensure_downloads_dir(func):
    """确保下载目录存在的装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        config.DOWNLOADS_DIR.mkdir(exist_ok=True)
        return func(*args, **kwargs)
    return wrapper

def log_errors(func):
    """错误日志装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"{func.__name__} 发生错误: {str(e)}")
            return None
    return wrapper 