from src.core.config import config


class UIConstants:
    QUALITY_OPTIONS = [opt.name for opt in config.QUALITY_OPTIONS]
    QUALITY_MAP = config.QUALITY_MAP

    LYRICS_OPTIONS = [
        ("仅下载音频", "no_lyrics"),
        ("仅下载歌词", "only_lyrics"),
        ("下载音频和歌词", "save_lyrics"),
        ("下载音频并嵌入歌词", "embed_only"),
        ("下载音频嵌入歌词并保存", "save_and_embed")
    ]
