import re
from pathlib import Path

# ── App metadata ────────────────────────────────────────────────────
APP_NAME = "YTDownloader"
APP_VERSION = "2.0.1"
APP_AUTHOR = "Brian Ashihara"
APP_URL = "https://github.com/BrianAshihara/YTDownloader"

# Default download directory
DOWNLOAD_DIR = Path.home() / "Downloads"

# ── URL validation ──────────────────────────────────────────────────
# Hosts accepted by the app. yt-dlp does the real parsing; this is only
# a fast sanity check before hitting the network.
YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "www.youtube-nocookie.com",
    "youtube-nocookie.com",
}

# Kept for backwards compatibility with older imports.
YOUTUBE_REGEX = re.compile(
    r"^(https?://)?([a-z0-9-]+\.)?(youtube\.com|youtu\.be|youtube-nocookie\.com)/.+",
    re.IGNORECASE,
)

# ── Download choices ────────────────────────────────────────────────
# Label shown in the UI -> max height (None = best available)
VIDEO_QUALITIES = {
    "Melhor disponível": None,
    "1080p": 1080,
    "720p": 720,
    "480p": 480,
    "360p": 360,
}

# Label shown in the UI -> (codec, bitrate in kbps or None)
AUDIO_FORMATS = {
    "MP3 · 320 kbps": ("mp3", 320),
    "MP3 · 192 kbps": ("mp3", 192),
    "MP3 · 128 kbps": ("mp3", 128),
    "M4A · original (sem perda)": ("m4a", None),
}

DEFAULT_VIDEO_QUALITY = "Melhor disponível"
DEFAULT_AUDIO_FORMAT = "MP3 · 192 kbps"
