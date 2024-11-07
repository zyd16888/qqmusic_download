# main.py
from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import httpx
import uvicorn
from pathlib import Path
import asyncio
import io
import mutagen
from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3, APIC
import aiohttp
from PIL import Image
from urllib.parse import quote
import os
from urllib.parse import urlparse, unquote
import logging
import json
from pydantic import BaseModel
from typing import AsyncGenerator, Optional
import re
from datetime import timedelta

# 设置日志
# logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# 添加下载目录配置
DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

@app.get("/")
async def read_root():
    return FileResponse("static/index.html")

@app.get("/api/search")
async def search_songs(word: str, q: int = 11, count: int = 3):
    try:
        # 并发请求指定数量的结果
        async with httpx.AsyncClient() as client:
            tasks = []
            for n in range(1, int(count) + 1):
                tasks.append(
                    client.get(
                        "https://api.lolimi.cn/API/qqdg/",
                        params={"word": word, "n": n, "q": q},
                        timeout=10.0
                    )
                )
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            results = []
            for resp in responses:
                if isinstance(resp, Exception):
                    continue
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("code") == 200 and data.get("data"):
                        results.append(data["data"])

            print(results)
            
            return {"code": 200, "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def download_cover_image(url: str) -> bytes:
    try:
        timeout = httpx.Timeout(10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
            if response.status_code != 200:
                raise Exception(f"获取封面图片失败，状态码: {response.status_code}")
            return await response.aread()
    except Exception as e:
        logger.error(f"下载封面图片失败: {e}")
        raise

async def process_audio_file(audio_data: bytes, song_info: dict, file_ext: str) -> Path:
    try:
        # 下载封面图片
        cover_data = await download_cover_image(song_info["cover"])
        
        # 构建文件名
        filename = f"{song_info['song']} - {song_info['singer']}{file_ext}"
        filename = "".join(c for c in filename if c not in r'\/:*?"<>|')  # 移除非法字符
        file_path = DOWNLOAD_DIR / filename
        
        # 写入音频数据
        with open(file_path, "wb") as f:
            f.write(audio_data)
        
        # 根据文件类型处理元数据
        if file_ext.lower() == '.flac':
            audio = FLAC(file_path)
            audio.tags.clear()
            audio["TITLE"] = song_info["song"]
            audio["ARTIST"] = song_info["singer"]
            audio["ALBUM"] = song_info["album"]
            audio["DATE"] = song_info.get("time", "").split("-")[0]
            
            # 添加更多FLAC标签
            if song_info.get("bpm"):
                audio["BPM"] = str(song_info["bpm"])
            if song_info.get("quality"):
                audio["QUALITY"] = song_info["quality"]
            
            # 添加封面
            picture = Picture()
            picture.type = 3
            picture.mime = "image/jpeg"
            picture.desc = "Cover"
            picture.data = cover_data
            
            audio.clear_pictures()
            audio.add_picture(picture)
            audio.save()
            
        elif file_ext.lower() == '.mp3':
            from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB, TDRC, TLEN, TBPM, TCON

            # 创建或加载ID3标签
            try:
                audio = ID3(file_path)
            except:
                audio = ID3()

            # 添加基本标签
            audio.add(TIT2(encoding=3, text=song_info["song"]))  # 标题
            audio.add(TPE1(encoding=3, text=song_info["singer"]))  # 艺术家
            audio.add(TALB(encoding=3, text=song_info["album"]))  # 专辑
            
            # 添加可选标签
            if song_info.get("time"):
                audio.add(TDRC(encoding=3, text=song_info["time"]))  # 日期
            if song_info.get("interval"):
                # 将时长转换为毫秒
                duration_str = song_info["interval"].replace("分", ":").replace("秒", "")
                try:
                    minutes, seconds = map(int, duration_str.split(":"))
                    duration_ms = (minutes * 60 + seconds) * 1000
                    audio.add(TLEN(encoding=3, text=str(duration_ms)))  # 时长
                except:
                    pass
            if song_info.get("bpm"):
                audio.add(TBPM(encoding=3, text=str(song_info["bpm"])))  # BPM

            # 添加封面
            audio.add(APIC(
                encoding=3,
                mime="image/jpeg",
                type=3,
                desc="Cover",
                data=cover_data
            ))
            
            audio.save(file_path)
            
        return file_path
        
    except Exception as e:
        logger.error(f"处理音频文件失败: {e}")
        raise

@app.get("/api/download")
async def download_song(url: str, song_info: str):
    try:
        if not url:
            raise HTTPException(status_code=400, detail="下载链接不能为空")
        
        if not url.startswith(('http://', 'https://')):
            raise HTTPException(status_code=400, detail="无效的下载链接")
        
        # 解析URL获取文件扩展名
        parsed_url = urlparse(url)
        path = unquote(parsed_url.path)
        file_ext = os.path.splitext(path)[1].lower()
        
        # 如果无法从URL获取扩展名，根据URL特征判断
        if not file_ext:
            if 'flac' in url.lower():
                file_ext = '.flac'
            else:
                file_ext = '.mp3'  # 默认为mp3
                
        song_info = json.loads(song_info)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, follow_redirects=True)
            
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail="无法获取音乐文件")
            
            audio_data = await response.aread()
            
            # 处理并保存文件
            file_path = await process_audio_file(audio_data, song_info, file_ext)
            
            return {
                "code": 200,
                "message": "下载成功",
                "data": {
                    "filename": file_path.name,
                    "path": str(file_path),
                    "size": os.path.getsize(file_path)
                }
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def get_content_length(url: str) -> int:
    """获取音频文件大小"""
    async with aiohttp.ClientSession() as session:
        async with session.head(url) as response:
            return int(response.headers.get('Content-Length', 0))

async def stream_audio(url: str, start: int = 0, end: Optional[int] = None) -> AsyncGenerator[bytes, None]:
    """流式传输音频,支持范围请求"""
    chunk_size = 8192
    retries = 3
    
    for attempt in range(retries):
        try:
            async with httpx.AsyncClient() as client:
                headers = {}
                if start or end:
                    headers['Range'] = f'bytes={start}-{end if end else ""}'
                
                async with client.stream('GET', url, headers=headers, follow_redirects=True) as response:
                    if response.status_code not in (200, 206):
                        raise HTTPException(status_code=400, detail="无法获取音乐文件")
                    
                    async for chunk in response.aiter_bytes(chunk_size):
                        yield chunk
                        
            break  # 成功完成,退出重试循环
            
        except (httpx.StreamClosed, ConnectionError):
            if attempt == retries - 1:  # 最后一次重试
                raise
            await asyncio.sleep(1)  # 重试前等待
            continue

@app.get("/api/play")
async def play_song(
    request: Request, 
    url: str,
    range: Optional[str] = Header(None)
):
    try:
        if not url:
            raise HTTPException(status_code=400, detail="播放链接不能为空")
            
        if not url.startswith(('http://', 'https://')):
            raise HTTPException(status_code=400, detail="无效的播放链接")

        content_length = await get_content_length(url)
        start = 0
        end = content_length - 1

        # 处理范围请求
        if range:
            match = re.match(r'bytes=(\d+)-(\d*)', range)
            if match:
                start = int(match.group(1))
                end = int(match.group(2)) if match.group(2) else content_length - 1

        # 计算实际内容长度
        content_length = end - start + 1

        headers = {
            'Accept-Ranges': 'bytes',
            'Content-Range': f'bytes {start}-{end}/{content_length}',
            'Content-Length': str(content_length),
            'Content-Type': 'audio/mpeg',
            'Content-Disposition': 'inline',
            'Cache-Control': 'public, max-age=3600',
        }

        status_code = 206 if start > 0 else 200

        return StreamingResponse(
            stream_audio(url, start, end),
            status_code=status_code,
            headers=headers
        )
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)