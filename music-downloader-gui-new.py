import logging
import os
import threading
import time
import tkinter as tk
from datetime import datetime
from tkinter import ttk, filedialog, messagebox
from typing import Optional

from downscript import MusicDownloader, BatchDownloader


class MusicDownloaderGUI:
    # 常量定义
    QUALITY_OPTIONS = [
        "标准音质",
        "HQ高音质",
        "无损音质",
        "母带",
        "其他"
    ]

    QUALITY_MAP = {
        "标准音质": 4,
        "HQ高音质": 8,
        "无损音质": 11,
        "母带": 14
    }

    LYRICS_OPTIONS = [
        ("仅下载音频", "no_lyrics"),
        ("仅下载歌词", "only_lyrics"),
        ("下载音频和歌词", "save_lyrics"),
        ("下载音频并嵌入歌词", "embed_only"),
        ("下载音频嵌入歌词并保存", "save_and_embed")
    ]

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self._init_variables()
        self._setup_logger()
        self._init_ui()

    def _init_variables(self) -> None:
        """初始化变量"""
        self.stop_event = threading.Event()
        self.last_progress_line = None
        self.last_update_time = 0
        self.download_thread: Optional[threading.Thread] = None

    def _setup_logger(self) -> None:
        """设置日志系统"""
        if not os.path.exists('logs'):
            os.makedirs('logs')

        self.logger = logging.getLogger('MusicDownloader')
        self.logger.setLevel(logging.INFO)

        # 添加文件处理器
        log_file = f'logs/download_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        fh = logging.FileHandler(log_file, encoding='utf-8')
        fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(fh)

    def _init_ui(self) -> None:
        """初始化UI组件"""
        self.root.title("音乐下载器")
        self.root.geometry("800x600")

        self._setup_main_frame()
        self._setup_notebook()
        self._setup_log_frame()
        self._setup_grid_weights()

    def _setup_main_frame(self) -> None:
        """设置主框架"""
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    def _setup_notebook(self) -> None:
        """设置标签页"""
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 单曲下载页面
        self.single_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.single_frame, text="单曲下载")
        self.setup_single_download_page()

        # 批量下载页面
        self.batch_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.batch_frame, text="批量下载")
        self.setup_batch_download_page()

    def _setup_log_frame(self) -> None:
        """设置日志框架"""
        self.log_frame = ttk.LabelFrame(self.main_frame, text="下载日志", padding="5")
        self.log_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)

        self.log_text = tk.Text(self.log_frame, height=10, wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.scrollbar = ttk.Scrollbar(self.log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.log_text['yscrollcommand'] = self.scrollbar.set

    def _setup_grid_weights(self) -> None:
        """设置网格权重"""
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(1, weight=1)
        self.log_frame.columnconfigure(0, weight=1)
        self.log_frame.rowconfigure(0, weight=1)

    def setup_single_download_page(self) -> None:
        """设置单曲下载页面"""
        # 搜索框
        ttk.Label(self.single_frame, text="歌曲名称:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(self.single_frame, textvariable=self.search_var, width=50)
        self.search_entry.grid(row=0, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        # 音质选择
        self._setup_quality_selection(self.single_frame)

        # 搜索结果序号
        self._setup_search_index()

        # 歌词选项
        self._setup_lyrics_options(self.single_frame, is_batch=False)

        # 下载按钮
        self.download_btn = ttk.Button(self.single_frame, text="下载", command=self.download_single)
        self.download_btn.grid(row=3, column=0, columnspan=3, pady=20)

    def _setup_quality_selection(self, parent: ttk.Frame, is_batch: bool = False) -> None:
        """设置音质选择部分"""
        prefix = "batch_" if is_batch else ""

        ttk.Label(parent, text="音质选择:").grid(row=1, column=0, sticky=tk.W, pady=5)
        quality_var = tk.StringVar(value="无损音质")
        setattr(self, f"{prefix}quality_var", quality_var)

        quality_combo = ttk.Combobox(
            parent,
            textvariable=quality_var,
            values=self.QUALITY_OPTIONS,
            width=20,
            state='readonly'
        )
        quality_combo.grid(row=1, column=1, sticky=tk.W, pady=5)
        setattr(self, f"{prefix}quality_combo", quality_combo)

        # 自定义音质输入框
        custom_quality_var = tk.StringVar()
        setattr(self, f"{prefix}custom_quality_var", custom_quality_var)

        quality_input_frame = ttk.Frame(parent)
        quality_input_frame.grid(row=1, column=2, sticky=tk.W, pady=5)

        custom_quality_entry = ttk.Entry(
            quality_input_frame,
            textvariable=custom_quality_var,
            width=10
        )
        custom_quality_entry.pack(side=tk.LEFT, padx=(0, 5))

        ttk.Label(
            quality_input_frame,
            text="(1-14, 1最低，14最高)",
            foreground='gray'
        ).pack(side=tk.LEFT)

        # 默认隐藏输入框
        quality_input_frame.grid_remove()

        # 绑定事件
        def on_quality_changed(event):
            if quality_combo.get() == "其他":
                quality_input_frame.grid()
            else:
                quality_input_frame.grid_remove()

        quality_combo.bind('<<ComboboxSelected>>', on_quality_changed)

    def _setup_search_index(self) -> None:
        """设置搜索结果序号选择"""
        ttk.Label(self.single_frame, text="搜索结果序号:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.index_var = tk.IntVar(value=1)
        self.index_spin = ttk.Spinbox(
            self.single_frame,
            from_=1,
            to=10,
            textvariable=self.index_var,
            width=10
        )
        self.index_spin.grid(row=2, column=1, sticky=tk.W, pady=5)

    def _setup_lyrics_options(self, parent: ttk.Frame, is_batch: bool = False) -> None:
        """设置歌词选项"""
        prefix = "batch_" if is_batch else ""
        lyrics_frame = ttk.LabelFrame(parent, text="歌词选项", padding="5")
        lyrics_frame.grid(row=2, column=2, sticky=tk.W, pady=5)

        lyrics_var = tk.StringVar(value="no_lyrics")
        setattr(self, f"{prefix}lyrics_option", lyrics_var)

        for text, value in self.LYRICS_OPTIONS:
            ttk.Radiobutton(
                lyrics_frame,
                text=text,
                variable=lyrics_var,
                value=value
            ).pack(anchor=tk.W)

    def setup_batch_download_page(self) -> None:
        """设置批量下载页面"""
        # 文件选择
        ttk.Label(self.batch_frame, text="歌列表文件:").grid(
            row=0, column=0, sticky=tk.W, pady=5
        )
        self.file_var = tk.StringVar()
        self.file_entry = ttk.Entry(self.batch_frame, textvariable=self.file_var, width=50)
        self.file_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5)

        self.browse_btn = ttk.Button(self.batch_frame, text="浏览", command=self.browse_file)
        self.browse_btn.grid(row=0, column=2, padx=5, pady=5)

        # 音质选择
        self._setup_quality_selection(self.batch_frame, is_batch=True)

        # 歌词选项
        self._setup_lyrics_options(self.batch_frame, is_batch=True)

        # 按钮区域
        self._setup_batch_buttons()

    def _setup_batch_buttons(self) -> None:
        """设置批量下载页面的按钮"""
        button_frame = ttk.Frame(self.batch_frame)
        button_frame.grid(row=4, column=0, columnspan=3, pady=(40, 20))

        self.batch_download_btn = ttk.Button(
            button_frame,
            text="开始批量下载",
            command=self.download_batch
        )
        self.batch_download_btn.grid(row=0, column=0, padx=5)

        self.stop_btn = ttk.Button(
            button_frame,
            text="停止下载",
            command=self.stop_download,
            state='disabled'
        )
        self.stop_btn.grid(row=0, column=1, padx=5)

    def log_message(self, message: str) -> None:
        """添加日志消息到文本框和日志文件"""
        current_time = time.time()

        # 对于进度信息，限制更新频率
        if "下载进度:" in message:
            if current_time - self.last_update_time < 0.5:
                return
            self.last_update_time = current_time

            if self.last_progress_line is not None:
                self.log_text.delete(self.last_progress_line, f"{self.last_progress_line}+1line")

            self.log_text.insert(tk.END, message + "\n")
            self.last_progress_line = self.log_text.index("end-2c linestart")
        else:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_message = f"[{timestamp}] {message}"
            self.log_text.insert(tk.END, log_message + "\n")
            self.last_progress_line = None
            self.logger.info(message)

        self.log_text.see(tk.END)

    def download_single(self) -> None:
        """处理单曲下载"""
        try:
            song_name = self.search_var.get().strip()
            if not song_name:
                messagebox.showwarning("警告", "请输入歌曲名称")
                return

            self.download_btn.state(['disabled'])
            self.download_thread = threading.Thread(
                target=self._run_async_download_single, args=(song_name,), daemon=True
            )
            self.download_thread.start()
        except Exception as e:
            self.log_message(f"启动下载线程时出错: {str(e)}")
            self.download_btn.state(['!disabled'])

    def _run_async_download_single(self, song_name: str) -> None:
        """运行异步下载任务的包装器"""
        import asyncio

        try:
            # 在Windows上可能需要使用不同的事件循环策略
            if os.name == "nt":
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # 运行异步任务
            loop.run_until_complete(self._download_single_thread(song_name))
        except Exception as e:
            self.log_message(f"下载出错: {str(e)}")
        finally:
            loop.close()
            self.root.after(0, lambda: self.download_btn.state(["!disabled"]))

    async def _download_single_thread(self, song_name: str) -> None:
        """单曲下载线程"""
        try:
            lyrics_option = self.lyrics_option.get()
            downloader = MusicDownloader(callback=self.log_message)

            # 如果只下载歌词
            if lyrics_option == "only_lyrics":
                self.log_message(f"开始下载歌词: {song_name}")
                success, lyrics_content = (
                    await downloader.lyrics_manager.download_lyrics_from_qq(
                        "0",  # 传入"0"作为songmid
                        audio_filename=song_name,  # 传入歌名用于获取歌曲信息
                        return_content=True,
                    )
                )
                if success:
                    self.log_message(f"歌词下载完成")
                else:
                    self.log_message(f"歌词下载失败: {lyrics_content}")
                return

            # 下载音乐（可能包含歌词）
            self.log_message(f"开始下载: {song_name}")
            quality = self._get_quality_value()
            if quality is None:
                return

            download_lyrics = lyrics_option in ("save_lyrics", "save_and_embed")
            embed_lyrics = lyrics_option in ("embed_only", "save_and_embed")

            success = await downloader.download_song(
                song_name,
                n=self.index_var.get(),
                quality=quality,
                download_lyrics=download_lyrics,
                embed_lyrics=embed_lyrics,
            )

            if success:
                self.log_message(f"下载完成: {song_name}")
            else:
                self.log_message(f"下载失败: {song_name}")
        except Exception as e:
            self.log_message(f"下载出错: {str(e)}")

    def download_batch(self) -> None:
        """处理批量下载"""
        try:
            file_path = self.file_var.get().strip()
            if not file_path or not os.path.exists(file_path):
                messagebox.showwarning("警告", "请选择有效的歌曲列表文件")
                return

            # 获取歌词选项
            lyrics_option = self.batch_lyrics_option.get()

            quality = self._get_batch_quality_value()

            # 仅当需要下载音乐时才检查音质设置
            if lyrics_option != "only_lyrics":
                if quality is None:
                    return
            else:
                # 仅下载歌词时, 默认使用标准音质
                quality = 4

            self.stop_event.clear()
            self.batch_download_btn.state(['disabled'])
            self.stop_btn.state(['!disabled'])

            self.download_thread = threading.Thread(
                target=self._run_async_download_batch,
                args=(file_path, quality, lyrics_option),
                daemon=True,
            )
            self.download_thread.start()
        except Exception as e:
            self.log_message(f"启动批量下载时出错: {str(e)}")
            self._reset_batch_buttons()

    def _run_async_download_batch(
            self, file_path: str, quality: Optional[int], lyrics_option: str
    ) -> None:
        """运行异步批量下载任务的包装器"""
        import asyncio

        try:
            if os.name == "nt":
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            loop.run_until_complete(
                self._download_batch_thread(file_path, quality, lyrics_option)
            )
        except Exception as e:
            self.log_message(f"批量下载出错: {str(e)}")
        finally:
            loop.close()
            self.root.after(0, self._reset_batch_buttons)

    async def _download_batch_thread(
            self, file_path: str, quality: Optional[int], lyrics_option: str
    ) -> None:
        """批量下载线程"""
        try:
            downloader = BatchDownloader(callback=self.log_message)

            download_lyrics = lyrics_option in ("save_lyrics", "save_and_embed")
            embed_lyrics = lyrics_option in ("embed_only", "save_and_embed")

            await downloader.download_from_file(
                file_path,
                quality=quality,
                download_lyrics=download_lyrics,
                embed_lyrics=embed_lyrics,
                only_lyrics=lyrics_option == "only_lyrics",
            )

        except Exception as e:
            self.log_message(f"批量下载出错: {str(e)}")

    def _reset_batch_buttons(self) -> None:
        """重置批量下载页面的按钮状态"""
        self.batch_download_btn.state(['!disabled'])
        self.stop_btn.state(['disabled'])

    def browse_file(self) -> None:
        """打开文件选择对话框"""
        file_path = filedialog.askopenfilename(
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if file_path:
            self.file_var.set(file_path)

    def _get_quality_value(self) -> Optional[int]:
        """获取单曲下载页面的音质值"""
        return self._get_quality_value_common(self.quality_combo, self.custom_quality_var)

    def _get_batch_quality_value(self) -> Optional[int]:
        """获取批量下载页面的音质值"""
        return self._get_quality_value_common(self.batch_quality_combo, self.batch_custom_quality_var)

    def _get_quality_value_common(self, combo: ttk.Combobox, custom_var: tk.StringVar) -> Optional[int]:
        """通用的音质值获取方法"""
        quality = combo.get()
        if quality == "其他":
            try:
                value = int(custom_var.get())
                if 1 <= value <= 14:
                    return value
                raise ValueError()
            except ValueError:
                messagebox.showwarning("警告", "请输入1-14之间的数字")
                return None
        return self.QUALITY_MAP[quality]

    def stop_download(self) -> None:
        """停止下载"""
        if self.download_thread and self.download_thread.is_alive():
            self.stop_event.set()
            self.log_message("正在停止下载...")
            self.stop_btn.state(["disabled"])


def main():
    root = tk.Tk()
    app = MusicDownloaderGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
