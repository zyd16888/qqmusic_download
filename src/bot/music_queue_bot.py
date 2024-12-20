import os

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from src.handlers.playlist import PlaylistManager
from src.handlers.send_playlist_to_queue import send_songs_to_queue


class MusicQueueBot:
    def __init__(self, token: str, rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"):
        self.token = token
        self.rabbitmq_url = rabbitmq_url
        self.playlist_manager = PlaylistManager()

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理 /start 命令"""
        await update.message.reply_text(
            "欢迎使用音乐下载队列机器人！\n"
            "请发送网易云音乐歌单链接，我会将歌曲添加到下载队列。\n"
            "使用 /help 查看帮助信息。"
        )

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理 /help 命令"""
        await update.message.reply_text(
            "使用说明：\n"
            "1. 直接发送网易云音乐歌单链接\n"
            "2. 机器人会自动解析歌单并将歌曲添加到下载队列\n"
            "支持的链接格式：\n"
            "- 网易云音乐歌单链接 \n"
            "- QQ音乐歌单链接\n"
            "3. 使用 /song 命令添加单曲"
        )

    async def process_playlist(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理收到的歌单链接"""
        message_text = update.message.text

        if not message_text.startswith(('http://', 'https://')):
            await update.message.reply_text("请发送有效的歌单链接！")
            return

        try:
            # 发送处理中的消息
            processing_message = await update.message.reply_text("正在处理歌单，请稍候...")

            # 获取歌单歌曲
            songs = await self.playlist_manager.get_playlist_songs(message_text)

            if not songs:
                await processing_message.edit_text("未在歌单中找到任何歌曲！")
                return

            # 发送歌曲到队列
            await send_songs_to_queue(
                songs,
                rabbitmq_url=self.rabbitmq_url
            )

            # 更新成功消息
            song_names = [song for song in songs]
            songs_per_message = 50  # 每条消息显示的歌曲数量
            
            # 发送总览消息
            await processing_message.edit_text(
                f"✅ 成功添加 {len(songs)} 首歌曲到下载队列！\n"
                f"正在发送歌单详情..."
            )
            
            # 分批发送歌曲列表
            for i in range(0, len(song_names), songs_per_message):
                batch = song_names[i:i + songs_per_message]
                batch_number = i // songs_per_message + 1
                total_batches = (len(song_names) + songs_per_message - 1) // songs_per_message
                
                message = (
                    f"歌单详情 ({batch_number}/{total_batches})：\n\n"
                    + "\n".join(f"{i + j + 1}. {song}" for j, song in enumerate(batch))
                )
                
                await update.message.reply_text(message)
            
            # 发送完成消息
            await update.message.reply_text("歌单处理完成。")

        except Exception as e:
            print(f"处理歌单时出错：{str(e)}")
            await processing_message.edit_text(f"处理歌单时出错：{str(e)}")

    async def song(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理 /song 命令"""
        # 检查是否提供了歌名参数
        if not context.args:
            await update.message.reply_text("请提供歌名！使用方式：/song 歌名")
            return

        # 获取歌名
        song_name = " ".join(context.args)
        
        try:
            # 发送处理中的消息
            processing_message = await update.message.reply_text("正在处理歌曲请求，请稍候...")
            
            # 将单曲包装为列表
            songs = [song_name]
            
            # 发送歌曲到队列
            await send_songs_to_queue(
                songs,
                rabbitmq_url=self.rabbitmq_url
            )
            
            # 更新成功消息
            await processing_message.edit_text(f"✅ 已将歌曲 '{song_name}' 添加到下载队列！")
            
        except Exception as e:
            print(f"处理单曲请求时出错：{str(e)}")
            await processing_message.edit_text(f"处理单曲请求时出错：{str(e)}")

    def run(self):
        """运行机器人"""
        app = Application.builder().token(self.token).build()

        # 注册命令处理器
        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(CommandHandler("help", self.help))
        app.add_handler(CommandHandler("song", self.song))

        # 注册消息处理器
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_playlist))

        # 启动机器人
        app.run_polling()


def main():
    # 从环境变量获取配置
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")

    if not token:
        print("请设置 TELEGRAM_BOT_TOKEN 环境变量！")
        return

    bot = MusicQueueBot(token, rabbitmq_url)
    bot.run()


if __name__ == "__main__":
    main()
