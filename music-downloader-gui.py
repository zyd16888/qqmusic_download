import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
from datetime import datetime
import os
from downscript import download_song, download_from_file, get_existing_songs, download_lyrics
import time
from concurrent.futures import ThreadPoolExecutor

class MusicDownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("音乐下载器")
        self.root.geometry("800x600")
        
        # 创建主框架
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 创建标签页控件
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
        
        # 下载记录文本框
        self.log_frame = ttk.LabelFrame(self.main_frame, text="下载日志", padding="5")
        self.log_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        
        self.log_text = tk.Text(self.log_frame, height=10, wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 添加滚动条
        self.scrollbar = ttk.Scrollbar(self.log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.log_text['yscrollcommand'] = self.scrollbar.set
        
        # 设置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(1, weight=1)
        self.log_frame.columnconfigure(0, weight=1)
        self.log_frame.rowconfigure(0, weight=1)
        
        self.stop_event = threading.Event()
        self.last_progress_line = None
        self.last_update_time = 0

    def setup_single_download_page(self):
        # 搜索框
        ttk.Label(self.single_frame, text="歌曲名称:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(self.single_frame, textvariable=self.search_var, width=50)
        self.search_entry.grid(row=0, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # 音质选择
        ttk.Label(self.single_frame, text="音质选择:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.quality_var = tk.StringVar(value="无损音质")
        quality_options = [
            "标准音质",
            "HQ高音质",
            "无损音质",
            "母带",
            "其他"
        ]
        self.quality_combo = ttk.Combobox(self.single_frame, 
                                        textvariable=self.quality_var,
                                        values=quality_options,
                                        width=20,
                                        state='readonly')
        self.quality_combo.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # 添加其他音质输入框和提示标签
        self.custom_quality_var = tk.StringVar()
        quality_input_frame = ttk.Frame(self.single_frame)
        quality_input_frame.grid(row=1, column=2, sticky=tk.W, pady=5)
        
        self.custom_quality_entry = ttk.Entry(quality_input_frame, 
                                            textvariable=self.custom_quality_var,
                                            width=10)
        self.custom_quality_entry.pack(side=tk.LEFT, padx=(0, 5))
        
        self.quality_hint_label = ttk.Label(quality_input_frame, 
                                          text="(1-14, 1最低，14最高)",
                                          foreground='gray')
        self.quality_hint_label.pack(side=tk.LEFT)
        
        # 默认隐藏输入框和提示
        quality_input_frame.grid_remove()
        
        def on_quality_changed(event):
            if self.quality_combo.get() == "其他":
                quality_input_frame.grid()
            else:
                quality_input_frame.grid_remove()
        
        self.quality_combo.bind('<<ComboboxSelected>>', on_quality_changed)
        
        # 搜索结果序号
        ttk.Label(self.single_frame, text="搜索结果序号:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.index_var = tk.IntVar(value=1)
        self.index_spin = ttk.Spinbox(self.single_frame, from_=1, to=10, textvariable=self.index_var, width=10)
        self.index_spin.grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # 修改歌词下载复选框为单独的下载按钮
        lyrics_frame = ttk.Frame(self.single_frame)
        lyrics_frame.grid(row=2, column=2, sticky=tk.W, pady=5)
        
        self.download_lyrics_var = tk.BooleanVar(value=False)
        self.lyrics_checkbox = ttk.Checkbutton(lyrics_frame, 
                                             text="同时下载歌词",
                                             variable=self.download_lyrics_var)
        self.lyrics_checkbox.pack(side=tk.LEFT, padx=(0, 5))
        
        self.lyrics_only_btn = ttk.Button(lyrics_frame, 
                                        text="仅下载歌词",
                                        command=self.download_lyrics_only)
        self.lyrics_only_btn.pack(side=tk.LEFT)
        
        # 下载按钮
        self.download_btn = ttk.Button(self.single_frame, text="下载", command=self.download_single)
        self.download_btn.grid(row=3, column=0, columnspan=3, pady=20)

    def setup_batch_download_page(self):
        # 文件选择
        ttk.Label(self.batch_frame, text="歌曲列表文件:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.file_var = tk.StringVar()
        self.file_entry = ttk.Entry(self.batch_frame, textvariable=self.file_var, width=50)
        self.file_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5)
        
        self.browse_btn = ttk.Button(self.batch_frame, text="浏览", command=self.browse_file)
        self.browse_btn.grid(row=0, column=2, padx=5, pady=5)
        
        # 添加音质选择
        ttk.Label(self.batch_frame, text="音质选择:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.batch_quality_var = tk.StringVar(value="无损音质")
        quality_options = [
            "标准音质",
            "HQ高音质",
            "无损音质",
            "母带",
            "其他"
        ]
        self.batch_quality_combo = ttk.Combobox(self.batch_frame, 
                                        textvariable=self.batch_quality_var,
                                        values=quality_options,
                                        width=20,
                                        state='readonly')
        self.batch_quality_combo.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # 添加其他音质输入框和提示标签
        self.batch_custom_quality_var = tk.StringVar()
        batch_quality_input_frame = ttk.Frame(self.batch_frame)
        batch_quality_input_frame.grid(row=1, column=2, sticky=tk.W, pady=5)
        
        self.batch_custom_quality_entry = ttk.Entry(batch_quality_input_frame, 
                                                  textvariable=self.batch_custom_quality_var,
                                                  width=10)
        self.batch_custom_quality_entry.pack(side=tk.LEFT, padx=(0, 5))
        
        self.batch_quality_hint_label = ttk.Label(batch_quality_input_frame, 
                                                text="(1-14, 1最低，14最高)",
                                                foreground='gray')
        self.batch_quality_hint_label.pack(side=tk.LEFT)
        
        # 默认隐藏输入框和提示
        batch_quality_input_frame.grid_remove()
        
        def on_batch_quality_changed(event):
            if self.batch_quality_combo.get() == "其他":
                batch_quality_input_frame.grid()
            else:
                batch_quality_input_frame.grid_remove()
        
        self.batch_quality_combo.bind('<<ComboboxSelected>>', on_batch_quality_changed)
        
        # 替换原来的歌词下载复选框为单选按钮组
        lyrics_frame = ttk.LabelFrame(self.batch_frame, text="歌词下载选项", padding="5")
        lyrics_frame.grid(row=1, column=2, sticky=tk.W, pady=5)
        
        self.batch_lyrics_option = tk.StringVar(value="no_lyrics")
        ttk.Radiobutton(lyrics_frame, 
                        text="不下载歌词",
                        variable=self.batch_lyrics_option,
                        value="no_lyrics").pack(anchor=tk.W)
        ttk.Radiobutton(lyrics_frame, 
                        text="同时下载歌词",
                        variable=self.batch_lyrics_option,
                        value="with_lyrics").pack(anchor=tk.W)
        ttk.Radiobutton(lyrics_frame, 
                        text="仅下载歌词",
                        variable=self.batch_lyrics_option,
                        value="only_lyrics").pack(anchor=tk.W)
        
        # 批量下载和停止按钮
        button_frame = ttk.Frame(self.batch_frame)
        button_frame.grid(row=2, column=0, columnspan=3, pady=20)
        
        self.batch_download_btn = ttk.Button(button_frame, text="开始批量下载", 
                                           command=self.download_batch)
        self.batch_download_btn.grid(row=0, column=0, padx=5)
        
        self.stop_btn = ttk.Button(button_frame, text="停止下载", 
                                 command=self.stop_download,
                                 state='disabled')
        self.stop_btn.grid(row=0, column=1, padx=5)

    def log_message(self, message):
        """添加日志消息到文本框，支持进度更新"""
        current_time = time.time()
        
        # 对于进度信息，限制更新频率
        if "下载进度:" in message:
            if current_time - self.last_update_time < 0.5:  # 限制更新频率
                return
            self.last_update_time = current_time
            
            # 如果存在上一行进度，删除它
            if self.last_progress_line is not None:
                self.log_text.delete(self.last_progress_line, f"{self.last_progress_line}+1line")
            
            # 插入新的进度信息（不带时间戳）
            self.log_text.insert(tk.END, message + "\n")
            self.last_progress_line = self.log_text.index("end-2c linestart")
        else:
            # 普通日志消息（带时间戳）
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
            self.last_progress_line = None
            
        self.log_text.see(tk.END)

    def download_single(self):
        """单曲下载处理"""
        song_name = self.search_var.get().strip()
        if not song_name:
            messagebox.showwarning("警告", "请输入歌曲名称")
            return
            
        self.download_btn.state(['disabled'])
        
        def download_thread():
            try:
                self.log_message(f"开始下载: {song_name}")
                quality = self.get_quality_value()
                if quality is None:
                    return
                
                success = download_song(song_name, 
                                     n=self.index_var.get(),
                                     q=quality,
                                     callback=self.log_message,
                                     download_lyrics_flag=self.download_lyrics_var.get())
                if success:
                    self.log_message(f"下载完成: {song_name}")
                else:
                    self.log_message(f"下载失败: {song_name}")
            except Exception as e:
                self.log_message(f"下载出错: {str(e)}")
            finally:
                self.root.after(0, lambda: self.download_btn.state(['!disabled']))
        
        threading.Thread(target=download_thread, daemon=True).start()

    def download_batch(self):
        """批量下载处理"""
        file_path = self.file_var.get().strip()
        if not file_path or not os.path.exists(file_path):
            messagebox.showwarning("警告", "请选择有效的歌曲列表文件")
            return
        
        # 仅当需要下载音乐时才检查音质设置
        lyrics_option = self.batch_lyrics_option.get()
        if lyrics_option != "only_lyrics":
            quality = self.get_batch_quality_value()
            if quality is None:
                return
        else:
            quality = None
        
        self.stop_event.clear()
        self.batch_download_btn.state(['disabled'])
        self.stop_btn.state(['!disabled'])
        
        def batch_download_thread():
            try:
                self.log_message(f"开始批量处理，文件: {file_path}")
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    songs = f.read().splitlines()
                
                total = len(songs)
                success = 0
                failed = []
                
                for i, song in enumerate(songs, 1):
                    if self.stop_event.is_set():
                        self.log_message("\n下载已停止")
                        break
                    
                    if not song.strip():  # 跳过空行
                        continue
                    
                    self.log_message(f"\n[{i}/{total}] 处理: {song}")
                    
                    try:
                        if lyrics_option == "only_lyrics":
                            # 仅下载歌词
                            success_flag, result = download_lyrics(song, callback=self.log_message)
                            if success_flag:
                                success += 1
                            else:
                                failed.append(f"{song} (歌词下载失败)")
                        else:
                            # 下载音乐（可能包含歌词）
                            if download_song(song, 
                                          q=quality,
                                          callback=self.log_message,
                                          download_lyrics_flag=(lyrics_option == "with_lyrics")):
                                success += 1
                            else:
                                failed.append(song)
                    except Exception as e:
                        self.log_message(f"处理出错: {str(e)}")
                        failed.append(song)
                
                # 处理失败列表
                if failed:
                    failed_file = os.path.join(os.path.dirname(file_path), 'failed_downloads.txt')
                    self.log_message("\n以下项目处理失败:")
                    with open(failed_file, 'w', encoding='utf-8') as f:
                        for item in failed:
                            f.write(f"{item}\n")
                            self.log_message(f"- {item}")
                    self.log_message(f"\n失败列表已保存到: {failed_file}")
                
                self.log_message(f"\n批量处理完成！")
                self.log_message(f"成功: {success}")
                self.log_message(f"失败: {len(failed)}")
                
            except Exception as e:
                self.log_message(f"批量处理出错: {str(e)}")
            finally:
                self.root.after(0, lambda: self.batch_download_btn.state(['!disabled']))
                self.root.after(0, lambda: self.stop_btn.state(['disabled']))
        
        threading.Thread(target=batch_download_thread, daemon=True).start()

    def browse_file(self):
        """文件选择对话框"""
        file_path = filedialog.askopenfilename(
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if file_path:
            self.file_var.set(file_path)

    def get_quality_value(self):
        """获取单曲下载页面的音质值"""
        quality_map = {
            "标准音质": 4,
            "HQ高音质": 8,
            "无损音质": 11,
            "母带": 14
        }
        
        quality = self.quality_combo.get()
        if quality == "其他":
            try:
                value = int(self.custom_quality_var.get())
                if 1 <= value <= 14:
                    return value
                else:
                    raise ValueError()
            except ValueError:
                messagebox.showwarning("警告", "请输入1-14之间的数字")
                return None
        return quality_map[quality]

    def get_batch_quality_value(self):
        """获取批量下载页面的音质值"""
        quality_map = {
            "标准音质": 4,
            "HQ高音质": 8,
            "无损音质": 11,
            "母带": 14
        }
        
        quality = self.batch_quality_combo.get()
        if quality == "其他":
            try:
                value = int(self.batch_custom_quality_var.get())
                if 1 <= value <= 14:
                    return value
                else:
                    raise ValueError()
            except ValueError:
                messagebox.showwarning("警告", "请输入1-14之间的数字")
                return None
        return quality_map[quality]

    def stop_download(self):
        self.stop_event.set()
        self.log_message("正在停止下载...")
        self.stop_btn.state(['disabled'])

    def download_lyrics_only(self):
        """仅下载歌词的处理函数"""
        song_name = self.search_var.get().strip()
        if not song_name:
            messagebox.showwarning("警告", "请输入歌曲名称")
            return
            
        self.lyrics_only_btn.state(['disabled'])
        
        def download_thread():
            try:
                self.log_message(f"开始下载歌词: {song_name}")
                success, result = download_lyrics(song_name, callback=self.log_message)
                if success:
                    self.log_message(f"歌词下载完成: {result}")
                else:
                    self.log_message(f"歌词下载失败: {result}")
            except Exception as e:
                self.log_message(f"歌词下载出错: {str(e)}")
            finally:
                self.root.after(0, lambda: self.lyrics_only_btn.state(['!disabled']))
        
        threading.Thread(target=download_thread, daemon=True).start()

def main():
    root = tk.Tk()
    app = MusicDownloaderGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
