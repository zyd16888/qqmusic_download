import json
import time
import random
from typing import Optional, Callable

import aio_pika
import asyncio

from ..core.batch_downloader import BatchDownloader
from ..utils.song_scanner import SongScanner
from ..core.config import Config


class MusicDownloadService(BatchDownloader):
    def __init__(self,
                 rabbitmq_url: str,
                 queue_name: str,
                 callback: Optional[Callable] = None,
                 max_retries: int = 3):
        super().__init__(callback=callback, auto_retry=False)
        self.rabbitmq_url = rabbitmq_url
        self.queue_name = queue_name
        self.max_retries = max_retries
        self.connection = None
        self.channel = None
        self.queue = None
        self.existing_songs = SongScanner.get_existing_songs(Config.DOWNLOADS_DIR, Config.DOWNLOADS_FILE)

    async def connect(self):
        """连接到RabbitMQ"""
        try:
            self.connection = await aio_pika.connect_robust(self.rabbitmq_url)
            self.channel = await self.connection.channel()
            
            # 设置 QoS，限制未确认消息的数量为 10
            await self.channel.set_qos(prefetch_count=10)

            # 声明一个持久化的队列
            self.queue = await self.channel.declare_queue(
                self.queue_name,
                durable=True
            )

            # 声明一个死信队列用于存放失败的消息
            await self.channel.declare_queue(
                f"{self.queue_name}_failed",
                durable=True
            )

            self.log("已连接到RabbitMQ")
        except Exception as e:
            self.log(f"连接RabbitMQ失败: {str(e)}")
            raise

    async def process_message(self, message: aio_pika.IncomingMessage):
        """处理队列消息"""
        try:
            async with message.process():
                body = json.loads(message.body.decode())
                song_name = body.get("song_name")
                retry_count = body.get("retry_count", 0)

                # 检查歌曲是否已存在
                song_key = song_name.split(' - ')[0].strip()
                if song_key in self.existing_songs:
                    self.log(f"歌曲已存在，跳过: {song_name}")
                    return

                self.log(f"开始下载歌曲: {song_name} (重试次数: {retry_count})")

                success = await self.download_song(
                    song_name,
                    quality=body.get("quality", 11),
                    download_lyrics=body.get("download_lyrics", True),
                    embed_lyrics=body.get("embed_lyrics", True)
                )


                if success:
                    # 下载成功，将歌曲添加到已存在列表中
                    self.existing_songs.add(song_key)
                    time.sleep(random.randint(5, 10))
                elif retry_count < self.max_retries:
                    # 下载失败，重新入队
                    await self.requeue_failed_message(song_name, retry_count + 1, 
                                                    body.get("quality", 11), 
                                                    body.get("download_lyrics", True), 
                                                    body.get("embed_lyrics", True))
                    time.sleep(random.randint(10, 20))
                else:
                    # 超过最大重试次数，发送到死信队列
                    await self.send_to_failed_queue(song_name)

        except aio_pika.exceptions.ChannelClosed:
            # 向上层抛出channel关闭异常，触发重连
            raise
        except Exception as e:
            self.log(f"处理消息时出错: {str(e)}")
            raise

    async def requeue_failed_message(self, song_name: str, retry_count: int, 
                                       quality: int, download_lyrics: bool, 
                                       embed_lyrics: bool):
        """重新将失败的消息加入队列"""
        message_body = json.dumps({
            "song_name": song_name,
            "retry_count": retry_count,
            "quality": quality,
            "download_lyrics": download_lyrics,
            "embed_lyrics": embed_lyrics
        })
        
        await self.channel.default_exchange.publish(
            aio_pika.Message(
                body=message_body.encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=self.queue_name
        )
        
        self.log(f"消息已重新入队: {song_name} (重试次数: {retry_count})")

    async def send_to_failed_queue(self, song_name: str):
        """将彻底失败的消息发送到死信队列"""
        message_body = json.dumps({"song_name": song_name})

        await self.channel.default_exchange.publish(
            aio_pika.Message(
                body=message_body.encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=f"{self.queue_name}_failed"
        )

        self.log(f"消息已发送到失败队列: {song_name}")

    async def start_consuming(self):
        """开始消费队列消息"""
        while True:  # 添加永久循环
            try:
                if not self.connection or self.connection.is_closed:
                    await self.connect()

                self.log(f"已扫描到 {len(self.existing_songs)} 首已存在歌曲")

                async with self.queue.iterator() as queue_iter:
                    self.log("开始监听下载队列...")
                    async for message in queue_iter:
                        try:
                            await self.process_message(message)
                        except aio_pika.exceptions.ChannelClosed:
                            # 如果channel关闭，尝试重连
                            self.log("Channel已关闭，尝试重新连接...")
                            if await self.reconnect():
                                # 重新发送消息到队列
                                await message.nack(requeue=True)
                            break
                        except Exception as e:
                            self.log(f"处理消息时出错: {str(e)}")
                            await message.nack(requeue=True)
                            continue

            except Exception as e:
                self.log(f"消费消息时出错: {str(e)}")
                # 等待一段时间后重试
                await asyncio.sleep(5)
            finally:
                if self.connection and not self.connection.is_closed:
                    await self.connection.close()

    async def reconnect(self):
        """重新连接到RabbitMQ"""
        try:
            if self.connection and not self.connection.is_closed:
                await self.connection.close()
            
            await self.connect()
            self.log("已重新连接到RabbitMQ")
            return True
        except Exception as e:
            self.log(f"重新连接RabbitMQ失败: {str(e)}")
            return False
