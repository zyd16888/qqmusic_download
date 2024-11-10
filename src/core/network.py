import ssl
import urllib3
import requests
from typing import Optional

class NetworkManager:
    """网络请求管理类"""
    def __init__(self):
        self.session = self._setup_ssl()

    def _setup_ssl(self) -> requests.Session:
        """配置SSL会话"""
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        session = requests.Session()
        session.verify = False
        session.trust_env = False

        try:
            default_context = ssl.create_default_context()
            default_context.set_ciphers("DEFAULT:@SECLEVEL=1")
            session.mount("https://", requests.adapters.HTTPAdapter(max_retries=3))
        except Exception as e:
            print(f"SSL配置警告: {str(e)}")

        return session

    def get(self, url: str, **kwargs) -> Optional[requests.Response]:
        """发送GET请求"""
        try:
            return self.session.get(url, **kwargs)
        except Exception as e:
            print(f"请求失败: {str(e)}")
            return None

# 全局网络管理器实例
network = NetworkManager() 