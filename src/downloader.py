import threading
import yt_dlp
from src.constants import DOWNLOAD_DIR, YOUTUBE_REGEX


def validate_url(url: str) -> bool:
    """Check if the URL matches a known YouTube pattern."""
    return bool(YOUTUBE_REGEX.match(url))


def build_options(download_type: str, download_dir=None, progress_hook=None):
    """
    Build yt-dlp options dict for video or audio download.

    Args:
        download_type: "video" or "audio"
        download_dir: Target directory (defaults to DOWNLOAD_DIR)
        progress_hook: Callable invoked on download progress updates
    """
    target_dir = download_dir or DOWNLOAD_DIR

    import os
    import sys

    # Se estiver rodando como executável (PyInstaller), o ffmpeg estará na raiz do sys._MEIPASS
    # Caso contrário, tenta usar do caminho C:\ffmpeg\bin\ffmpeg.exe ou do PATH.
    base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ffmpeg_local = os.path.join(base_dir, 'ffmpeg.exe')
    
    if os.path.exists(ffmpeg_local):
        ffmpeg_path = ffmpeg_local
    elif os.path.exists(r"C:\ffmpeg\bin\ffmpeg.exe"):
        ffmpeg_path = r"C:\ffmpeg\bin\ffmpeg.exe"
    else:
        ffmpeg_path = "ffmpeg"

    opts = {
        "quiet": True,
        "no_warnings": True,
        "outtmpl": str(target_dir / "%(title)s.%(ext)s"),
        "extractor_args": {"youtube": {"player_client": ["default"]}},
        "ffmpeg_location": ffmpeg_path,
    }

    if progress_hook:
        opts["progress_hooks"] = [progress_hook]

    if download_type == "video":
        opts.update({
            # Prefer 1080p, then best available resolution
            # Don't filter by ext — YouTube serves 1080p as webm (VP9)
            # FFmpeg will handle merging/remuxing into mp4
            "format": (
                "bestvideo[height>=1080]+bestaudio/"
                "bestvideo+bestaudio/"
                "best"
            ),
            "merge_output_format": "mp4",
            # Ensure the audio is compatible with standard MP4 players (like Windows native player)
            # VP9/AV1 video + Opus audio in MP4 often has no sound.
            "postprocessors": [{
                "key": "FFmpegVideoConvertor",
                "preferedformat": "mp4",
            }],
            # Force audio conversion to AAC, but COPY video so we don't lose quality
            "postprocessor_args": [
                "-c:v", "copy",
                "-c:a", "aac"
            ],
        })
    else:
        opts.update({
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        })

    return opts


def download(url: str, download_type: str, download_dir=None,
             progress_hook=None, on_success=None, on_error=None,
             on_complete=None):
    """
    Download a YouTube video or audio in a background thread.

    Args:
        url: YouTube video URL
        download_type: "video" or "audio"
        download_dir: Target directory (defaults to DOWNLOAD_DIR)
        progress_hook: Callable for progress updates
        on_success: Callable(title: str) on successful download
        on_error: Callable(error: str) on failure
        on_complete: Callable() always runs after download (finally)
    """
    def task():
        try:
            opts = build_options(download_type, download_dir, progress_hook)
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get("title", "vídeo")

            if on_success:
                on_success(title)

        except yt_dlp.utils.DownloadError as e:
            if on_error:
                on_error(f"Não foi possível baixar o vídeo.\n"
                         f"Verifique a URL e sua conexão.\n\n{e}")
        except Exception as e:
            if on_error:
                on_error(f"Ocorreu um erro inesperado:\n{e}")
        finally:
            if on_complete:
                on_complete()

    threading.Thread(target=task, daemon=True).start()
