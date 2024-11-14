import asyncio
import logging
from src.services.music_download_service import MusicDownloadService
from run_cli import CLILogger

async def main():
    # RabbitMQ连接配置
    cli_logger = CLILogger()
    rabbitmq_config = {
        "url": "amqp://guest:guest@localhost:5672/",  # Docker RabbitMQ 连接地址
        "queue_name": "music_download_queue"
    }
    
    try:
        # 创建下载服务实例
        service = MusicDownloadService(
            rabbitmq_url=rabbitmq_config["url"],
            queue_name=rabbitmq_config["queue_name"],
            callback=cli_logger.log_message,
            max_retries=6
        )
        
        # 启动服务
        print("开始监听下载队列...")
        await service.start_consuming()
        
    except KeyboardInterrupt:
        print("服务已停止")
    except Exception as e:
        print(f"服务出错: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())