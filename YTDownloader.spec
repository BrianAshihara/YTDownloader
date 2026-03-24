# -*- mode: python ; coding: utf-8 -*-

import os
import importlib.util
from PyInstaller.utils.hooks import collect_data_files, collect_submodules


def _find_binary(name):
    candidates = [
        os.path.join(os.getcwd(), name),
        os.path.join(r"C:\ffmpeg\bin", name),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


ffmpeg_path = _find_binary("ffmpeg.exe")
ffprobe_path = _find_binary("ffprobe.exe")

_binaries = []
if ffmpeg_path:
    _binaries.append((ffmpeg_path, '.'))
if ffprobe_path:
    _binaries.append((ffprobe_path, '.'))

_ctk_spec = importlib.util.find_spec("customtkinter")
if _ctk_spec and _ctk_spec.submodule_search_locations:
    _ctk_datas = collect_data_files('customtkinter')
    _ctk_hidden = collect_submodules('customtkinter')
else:
    _ctk_datas = []
    _ctk_hidden = []

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=_binaries,
    datas=_ctk_datas + [('src', 'src')],
    hiddenimports=['src', 'src.app', 'src.downloader', 'src.constants', 'customtkinter'] + _ctk_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='YTDownloader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['YTD.ico'],
)
