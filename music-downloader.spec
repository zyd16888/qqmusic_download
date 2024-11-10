# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=[],
    datas=[('fonts', 'fonts')],
    hiddenimports=[
        'src.core.config',
        'src.core.downloader',
        'src.core.batch_downloader',
        'src.core.metadata',
        'src.core.network',
        'src.handlers.audio',
        'src.handlers.lyrics',
        'src.handlers.playlist',
        'src.handlers.report',
        'src.handlers.musicInfo',
        'src.utils.decorators',
        'src.utils.helpers',
        'src.ui.app',
        'src.ui.event_handler',
        'src.ui.ui_components',
        'src.ui.constants'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=True,
    win_private_assemblies=True,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='music-downloader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch='x86',
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico'
) 