"""Persistent user preferences stored as JSON."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from src.constants import (
    APP_NAME,
    AUDIO_FORMATS,
    DEFAULT_AUDIO_FORMAT,
    DEFAULT_VIDEO_QUALITY,
    DOWNLOAD_DIR,
    VIDEO_QUALITIES,
)
from src.paths import config_dir

logger = logging.getLogger(APP_NAME)


@dataclass
class Settings:
    download_dir: str = str(DOWNLOAD_DIR)
    mode: str = "video"  # "video" | "audio"
    video_quality: str = DEFAULT_VIDEO_QUALITY
    audio_format: str = DEFAULT_AUDIO_FORMAT

    def normalized(self) -> "Settings":
        """Replace invalid/stale values with defaults."""
        if self.mode not in ("video", "audio"):
            self.mode = "video"
        if self.video_quality not in VIDEO_QUALITIES:
            self.video_quality = DEFAULT_VIDEO_QUALITY
        if self.audio_format not in AUDIO_FORMATS:
            self.audio_format = DEFAULT_AUDIO_FORMAT
        if not self.download_dir or not Path(self.download_dir).is_dir():
            self.download_dir = str(DOWNLOAD_DIR)
        return self


def _settings_file(folder: Path | None = None) -> Path:
    return (folder or config_dir()) / "settings.json"


def load_settings(folder: Path | None = None) -> Settings:
    path = _settings_file(folder)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        known = {f.name for f in fields(Settings)}
        data = {k: v for k, v in raw.items() if k in known and isinstance(v, str)}
        return Settings(**data).normalized()
    except FileNotFoundError:
        return Settings().normalized()
    except (OSError, ValueError, TypeError, AttributeError) as e:
        logger.warning("Could not read settings (%s); using defaults", e)
        return Settings().normalized()


def save_settings(settings: Settings, folder: Path | None = None) -> None:
    path = _settings_file(folder)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(settings), indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)
    except OSError as e:
        logger.warning("Could not save settings: %s", e)
