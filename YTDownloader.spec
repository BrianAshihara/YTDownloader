# -*- mode: python ; coding: utf-8 -*-
#
# Build:  python -m PyInstaller --clean --noconfirm YTDownloader.spec
# Output: dist/YTDownloader/  (folder app, packaged by installer/YTDownloader.iss)
#
# Why "onedir" and no UPX:
#   * onefile extracts everything (~300 MB with ffmpeg/deno) to %TEMP% on every
#     launch: slow start and a classic antivirus false-positive trigger.
#   * UPX-packed executables are flagged by many antivirus engines.

import os
import re
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo,
    StringFileInfo,
    StringStruct,
    StringTable,
    VarFileInfo,
    VarStruct,
    VSVersionInfo,
)

ROOT = Path(SPECPATH)

# ── Version (single source of truth: src/constants.py) ──────────────
_constants = (ROOT / "src" / "constants.py").read_text(encoding="utf-8")
APP_VERSION = re.search(r'APP_VERSION\s*=\s*"([^"]+)"', _constants).group(1)
APP_AUTHOR = re.search(r'APP_AUTHOR\s*=\s*"([^"]+)"', _constants).group(1)
_parts = [int(p) for p in re.findall(r"\d+", APP_VERSION)][:4]
VERSION_TUPLE = tuple(_parts + [0] * (4 - len(_parts)))

version_info = VSVersionInfo(
    ffi=FixedFileInfo(filevers=VERSION_TUPLE, prodvers=VERSION_TUPLE),
    kids=[
        StringFileInfo([
            StringTable("041604B0", [  # pt-BR, Unicode
                StringStruct("CompanyName", APP_AUTHOR),
                StringStruct("FileDescription", "YTDownloader"),
                StringStruct("FileVersion", APP_VERSION),
                StringStruct("InternalName", "YTDownloader"),
                StringStruct("LegalCopyright", f"© {APP_AUTHOR}. Licença MIT."),
                StringStruct("OriginalFilename", "YTDownloader.exe"),
                StringStruct("ProductName", "YTDownloader"),
                StringStruct("ProductVersion", APP_VERSION),
            ])
        ]),
        VarFileInfo([VarStruct("Translation", [0x0416, 1200])]),
    ],
)

# ── External tools (fetched by scripts/fetch_binaries.ps1) ──────────
BIN = ROOT / "bin"
REQUIRED_BINARIES = ["ffmpeg.exe", "ffprobe.exe", "deno.exe"]
missing = [b for b in REQUIRED_BINARIES if not (BIN / b).is_file()]
if missing:
    msg = f"Missing in bin/: {', '.join(missing)}. Run: powershell -File scripts/fetch_binaries.ps1"
    if os.environ.get("YTD_ALLOW_MISSING_BINARIES") == "1":
        print(f"WARNING: {msg} (continuing because YTD_ALLOW_MISSING_BINARIES=1)")
    else:
        raise SystemExit(f"ERROR: {msg}")

# Shipped as plain data: no dependency analysis on 100+ MB third-party exes.
datas = [(str(BIN / b), "bin") for b in REQUIRED_BINARIES if (BIN / b).is_file()]
if (BIN / "licenses").is_dir():
    datas.append((str(BIN / "licenses"), "bin/licenses"))

datas += collect_data_files("customtkinter")

ICON = ROOT / "assets" / "icon.ico"
icon = [str(ICON)] if ICON.is_file() else None
if icon:
    datas.append((str(ICON), "assets"))  # also used for the window icon at runtime

for doc in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
    if (ROOT / doc).is_file():
        datas.append((str(ROOT / doc), "."))

a = Analysis(
    ["main.py"],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "IPython", "matplotlib", "numpy"],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="YTDownloader",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon,
    version=version_info,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="YTDownloader",
)
