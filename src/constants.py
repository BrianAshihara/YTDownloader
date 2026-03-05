import re
from pathlib import Path

# App metadata
APP_NAME = "YTDownloader"
APP_VERSION = "1.0.0"

# Default download directory
DOWNLOAD_DIR = Path.home() / "Downloads"

# YouTube URL validation pattern
YOUTUBE_REGEX = re.compile(
    r"(https?://)?(www\.)?(youtube\.com|youtu\.be|m\.youtube\.com)/.+"
)
