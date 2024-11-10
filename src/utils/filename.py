def sanitize_filename(filename: str) -> str:
    """处理文件名中的非法字符"""
    # Windows 文件名中不允许的字符
    invalid_chars = r'<>:"/\|?*'
    # 替换非法字符为空格
    sanitized = "".join(c if c not in invalid_chars else ' ' for c in filename)
    # 去除首尾空格
    sanitized = sanitized.strip()
    # 如果文件名为空，返回默认名称
    return sanitized or "untitled" 