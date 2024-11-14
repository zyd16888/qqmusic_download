import json
from typing import Optional, Callable

import aio_pika

from ..core.batch_downloader import BatchDownloader


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

    async def connect(self):
        """连接到RabbitMQ"""
        try:
            self.connection = await aio_pika.connect_robust(self.rabbitmq_url)
            self.channel = await self.connection.channel()

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
        async with message.process():
            try:
                body = json.loads(message.body.decode())
                song_name = body.get("song_name")
                retry_count = body.get("retry_count", 0)

                self.log(f"开始下载歌曲: {song_name} (重试次数: {retry_count})")

                success = await self.download_song(
                    song_name,
                    quality=body.get("quality", 11),
                    download_lyrics=body.get("download_lyrics", True),
                    embed_lyrics=body.get("embed_lyrics", True)
                )

                if not success and retry_count < self.max_retries:
                    # 下载失败，重新入队
                    await self.requeue_failed_message(song_name, retry_count + 1, 
                                                       body.get("quality", 11), 
                                                       body.get("download_lyrics", True), 
                                                       body.get("embed_lyrics", True))
                elif not success:
                    # 超过最大重试次数，发送到死信队列
                    await self.send_to_failed_queue(song_name)

            except Exception as e:
                self.log(f"处理消息时出错: {str(e)}")
                # 发生异常时，消息会自动返回队列
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
        try:
            await self.connect()

            async with self.queue.iterator() as queue_iter:
                self.log("开始监听下载队列...")
                async for message in queue_iter:
                    await self.process_message(message)

        except Exception as e:
            self.log(f"消费消息时出错: {str(e)}")
        finally:
            if self.connection:
                await self.connection.close()
