import asyncio
import json
import aio_pika
import os
from pathlib import Path
from typing import List

from src.handlers.playlist import PlaylistManager

async def send_songs_to_queue(
    songs: List[str],
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/",
    queue_name: str = "music_download_queue"
) -> None:
    """发送歌曲列表到RabbitMQ队列"""
    connection = None
    try:
        connection = await aio_pika.connect_robust(rabbitmq_url)
        async with connection:
            channel = await connection.channel()
            
            print(f"共找到 {len(songs)} 首歌曲")
            
            # 发送每首歌曲到队列
            for song in songs:
                if not song.strip():
                    continue

                if song.startswith("- "):
                    song = song[2:]

                message_body = json.dumps({
                    "song_name": song,
                    "quality": 11,  # 默认音质
                    "download_lyrics": True,
                    "embed_lyrics": True,
                    "retry_count": 0
                })

                await channel.default_exchange.publish(
                    aio_pika.Message(
                        body=message_body.encode(),
                        delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                    ),
                    routing_key=queue_name
                )
                print(f"已发送到队列: {song}")

            print("所有歌曲已发送到队列")
    except Exception as e:
        print(f"发送歌曲到队列时出错: {str(e)}")
        raise
    finally:
        if connection and not connection.is_closed:
            await connection.close()

async def main():
    # 获取命令行参数
    import argparse
    parser = argparse.ArgumentParser(description='发送歌单到下载队列')
    parser.add_argument('playlist_path', help='歌单文件路径或URL')
    parser.add_argument('--rabbitmq', default="amqp://guest:guest@localhost:5672/",
                      help='RabbitMQ连接URL')
    parser.add_argument('--queue', default="music_download_queue",
                      help='队列名称')
    args = parser.parse_args()

    playlist_manager = PlaylistManager()
    
    try:
        if args.playlist_path.startswith(('http://', 'https://')):
            print(f"正在获取歌单: {args.playlist_path}")
            songs = await playlist_manager.get_playlist_songs(args.playlist_path)
        else:
            print(f"读取文件: {args.playlist_path}")
            if not os.path.exists(args.playlist_path):
                raise FileNotFoundError("找不到指定的文件")
            songs = playlist_manager.read_playlist_file(args.playlist_path)

        if not songs:
            print("没有找到要下载的歌曲")
            return

        await send_songs_to_queue(
            songs,
            rabbitmq_url=args.rabbitmq,
            queue_name=args.queue
        )

    except Exception as e:
        print(f"发送歌单到队列时出错: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 