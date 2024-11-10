import ssl
import json
import aiohttp
import urllib3
import requests
import asyncio
from typing import Optional, Dict, Any, Union
from aiohttp import ClientSession

class NetworkManager:
    """网络请求管理类"""
    def __init__(self):
        self.session = self._setup_ssl()
        self.aiohttp_session = None

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

    async def _ensure_aiohttp_session(self):
        """确保异步会话存在"""
        if self.aiohttp_session is None:
            self.aiohttp_session = ClientSession()
        return self.aiohttp_session

    async def close(self):
        """关闭异步会话"""
        if self.aiohttp_session:
            await self.aiohttp_session.close()
            self.aiohttp_session = None

    def get(self, url: str, **kwargs) -> Optional[requests.Response]:
        """发送同步GET请求"""
        try:
            return self.session.get(url, **kwargs)
        except Exception as e:
            print(f"请求失败: {str(e)}")
            return None

    async def async_get(self, url: str, params: Optional[Dict] = None, 
                       headers: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """发送异步GET请求"""
        try:
            session = await self._ensure_aiohttp_session()
            async with session.get(url, params=params, headers=headers) as response:
                if response.status != 200:
                    return None
                return await response.json()
        except Exception as e:
            print(f"异步请求失败: {str(e)}")
            return None

    async def async_get_text(self, url: str, params: Optional[Dict] = None, 
                           headers: Optional[Dict] = None) -> Optional[str]:
        """发送异步GET请求并返回文本"""
        try:
            session = await self._ensure_aiohttp_session()
            async with session.get(url, params=params, headers=headers) as response:
                if response.status != 200:
                    return None
                return await response.text()
        except Exception as e:
            print(f"异步请求失败: {str(e)}")
            return None

    async def async_post(self, url: str, data: Optional[Dict] = None,
                        headers: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """发送异步POST请求"""
        try:
            session = await self._ensure_aiohttp_session()
            async with session.post(url, data=data, headers=headers) as response:
                if response.status != 200:
                    return None
                return await response.json()
        except Exception as e:
            print(f"异步请求失败: {str(e)}")
            return None

    async def async_get_bytes(self, url: str, headers: Optional[Dict] = None) -> Optional[bytes]:
        """发送异步GET请求并返回二进制数据"""
        try:
            session = await self._ensure_aiohttp_session()
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    return None
                return await response.read()
        except Exception as e:
            print(f"异步请求失败: {str(e)}")
            return None

    def close_sync(self):
        """同步方式关闭会话"""
        if self.aiohttp_session:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.close())
            finally:
                loop.close()

# 全局网络管理器实例
network = NetworkManager()
