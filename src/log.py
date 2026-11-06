"""Logging setup: rotating file in the user's local app data folder."""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

from src.constants import APP_NAME, APP_VERSION
from src.paths import binaries, is_frozen, log_dir

logger = logging.getLogger(APP_NAME)


def setup_logging() -> None:
    if logger.handlers:
        return

    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    try:
        folder = log_dir()
        folder.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            folder / "ytdownloader.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
        handler.setFormatter(fmt)
        handler.setLevel(logging.DEBUG)
        logger.addHandler(handler)
    except OSError:
        pass  # Logging must never prevent the app from starting.

    if not is_frozen() and sys.stderr:
        console = logging.StreamHandler()
        console.setFormatter(fmt)
        console.setLevel(logging.INFO)
        logger.addHandler(console)

    logger.info("%s %s starting (frozen=%s)", APP_NAME, APP_VERSION, is_frozen())
    logger.info("Binaries: %s", binaries())


class YtDlpLogger:
    """Adapter that routes yt-dlp messages to our logger and keeps warnings."""

    def __init__(self):
        self.warnings: list[str] = []

    def debug(self, msg: str) -> None:
        # yt-dlp sends info-level messages through debug() prefixed with "[".
        logger.debug("yt-dlp: %s", msg)

    def info(self, msg: str) -> None:
        logger.info("yt-dlp: %s", msg)

    def warning(self, msg: str) -> None:
        self.warnings.append(msg)
        logger.warning("yt-dlp: %s", msg)

    def error(self, msg: str) -> None:
        logger.error("yt-dlp: %s", msg)
