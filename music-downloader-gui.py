import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
from datetime import datetime
import os
from downscript import download_song, download_from_file, get_existing_songs

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

    def setup_single_download_page(self):
        # 搜索框
        ttk.Label(self.single_frame, text="歌曲名称:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(self.single_frame, textvariable=self.search_var, width=50)
        self.search_entry.grid(row=0, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # 音质选择
        ttk.Label(self.single_frame, text="音质选择:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.quality_var = tk.IntVar(value=11)
        self.quality_combo = ttk.Combobox(self.single_frame, textvariable=self.quality_var, 
                                        values=list(range(1, 15)), width=10)
        self.quality_combo.grid(row=1, column=1, sticky=tk.W, pady=5)
        ttk.Label(self.single_frame, text="(1-14, 数字越大音质越好)").grid(row=1, column=2, sticky=tk.W, pady=5)
        
        # 搜索结果序号
        ttk.Label(self.single_frame, text="搜索结果序号:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.index_var = tk.IntVar(value=1)
        self.index_spin = ttk.Spinbox(self.single_frame, from_=1, to=10, textvariable=self.index_var, width=10)
        self.index_spin.grid(row=2, column=1, sticky=tk.W, pady=5)
        
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
        
        # 批量下载按钮
        self.batch_download_btn = ttk.Button(self.batch_frame, text="开始批量下载", 
                                           command=self.download_batch)
        self.batch_download_btn.grid(row=1, column=0, columnspan=3, pady=20)

    def log_message(self, message):
        """添加日志消息到文本框"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
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
                success = download_song(song_name, 
                                     n=self.index_var.get(),
                                     q=self.quality_var.get())
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
            
        self.batch_download_btn.state(['disabled'])
        
        def batch_download_thread():
            try:
                self.log_message(f"开始批量下载，文件: {file_path}")
                download_from_file(file_path)
                self.log_message("批量下载完成")
            except Exception as e:
                self.log_message(f"批量下载出错: {str(e)}")
            finally:
                self.root.after(0, lambda: self.batch_download_btn.state(['!disabled']))
        
        threading.Thread(target=batch_download_thread, daemon=True).start()

    def browse_file(self):
        """文件选择对话框"""
        file_path = filedialog.askopenfilename(
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if file_path:
            self.file_var.set(file_path)

def main():
    root = tk.Tk()
    app = MusicDownloaderGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
