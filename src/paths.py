"""Filesystem locations: bundled resources, external binaries and app data."""

from __future__ import annotations

import os
import shutil
import sys
from functools import lru_cache
from pathlib import Path

from src.constants import APP_NAME

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def resource_dir() -> Path:
    """Folder that holds bundled files (``_internal`` in a PyInstaller build)."""
    meipass = getattr(sys, "_MEIPASS", None)
    return Path(meipass) if meipass else PROJECT_ROOT


def resource_path(*parts: str) -> Path:
    return resource_dir().joinpath(*parts)


def _exe_name(name: str) -> str:
    return f"{name}.exe" if os.name == "nt" else name


def find_binary(name: str, search_dirs: list[Path] | None = None) -> str | None:
    """
    Locate an external executable (ffmpeg, ffprobe, deno).

    Order: bundled ``bin/`` folder -> project root -> system PATH.
    """
    exe = _exe_name(name)
    dirs = search_dirs if search_dirs is not None else [
        resource_path("bin"),
        resource_dir(),
    ]
    for folder in dirs:
        candidate = Path(folder) / exe
        if candidate.is_file():
            return str(candidate)
    return shutil.which(name)


@lru_cache(maxsize=None)
def binaries() -> dict[str, str | None]:
    """Cached lookup of every external tool the app uses."""
    return {name: find_binary(name) for name in ("ffmpeg", "ffprobe", "deno")}


def _windows_dir(env_var: str, fallback: Path) -> Path:
    value = os.environ.get(env_var)
    return Path(value) if value else fallback


def config_dir() -> Path:
    """Per-user settings folder (%APPDATA%\\YTDownloader on Windows)."""
    if os.name == "nt":
        base = _windows_dir("APPDATA", Path.home() / "AppData" / "Roaming")
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / APP_NAME


def log_dir() -> Path:
    """Per-user log folder (%LOCALAPPDATA%\\YTDownloader\\logs on Windows)."""
    if os.name == "nt":
        base = _windows_dir("LOCALAPPDATA", Path.home() / "AppData" / "Local")
    else:
        base = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    return base / APP_NAME / "logs"
