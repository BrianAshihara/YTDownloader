import re
import threading
import time
import yt_dlp
from src.constants import DOWNLOAD_DIR, YOUTUBE_REGEX

HTTP_5XX_REGEX = re.compile(r"http error 5\d\d", re.IGNORECASE)


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
    ffprobe_local = os.path.join(base_dir, 'ffprobe.exe')

    if os.path.exists(ffmpeg_local):
        ffmpeg_path = ffmpeg_local
        ffprobe_path = ffprobe_local if os.path.exists(ffprobe_local) else None
    elif os.path.exists(r"C:\ffmpeg\bin\ffmpeg.exe"):
        ffmpeg_path = r"C:\ffmpeg\bin\ffmpeg.exe"
        ffprobe_path = r"C:\ffmpeg\bin\ffprobe.exe" if os.path.exists(r"C:\ffmpeg\bin\ffprobe.exe") else None
    else:
        ffmpeg_path = "ffmpeg"
        ffprobe_path = "ffprobe"

    opts = {
        "quiet": True,
        "no_warnings": True,
        "outtmpl": str(target_dir / "%(title)s.%(ext)s"),
        "extractor_args": {"youtube": {"player_client": ["default"]}},
        "ffmpeg_location": ffmpeg_path,
        "ffprobe_location": ffprobe_path,
        "writethumbnail": True,
        "convertthumbnails": "jpg",
    }

    if progress_hook:
        opts["progress_hooks"] = [progress_hook]

    if download_type == "video":
        opts.update({
            # Prefer MP4/H.264 + M4A/AAC for compatibility and lower CPU usage
            "format": (
                "bestvideo[vcodec^=avc1][ext=mp4]+bestaudio[acodec^=mp4a][ext=m4a]/"
                "best[ext=mp4]"
            ),
            "merge_output_format": "mp4",
            "postprocessors": [
                {
                    "key": "FFmpegMetadata",
                },
                {
                    "key": "EmbedThumbnail",
                },
            ],
        })
    else:
        opts.update({
            "format": "bestaudio/best",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                },
                {
                    "key": "FFmpegMetadata",
                },
                {
                    "key": "EmbedThumbnail",
                },
            ],
        })

    return opts


def classify_error(error: str):
    text = (error or "").lower()

    if "http error 429" in text or "too many requests" in text or "rate limit" in text:
        return (
            "Muitas requisições (HTTP 429). Aguarde e tente novamente.",
            True,
            "muitas requisições",
        )

    if "private video" in text or "is private" in text:
        return ("Este vídeo é privado.", False, "vídeo privado")

    if (
        "not available in your country" in text
        or "not available in your region" in text
        or "not made this video available in your country" in text
    ):
        return ("Este vídeo não está disponível no seu país/região.", False, "restrição geográfica")

    if "sign in to confirm your age" in text or "age-restricted" in text:
        return ("Este vídeo requer verificação de idade.", False, "restrição de idade")

    if (
        "video unavailable" in text
        or "this video is unavailable" in text
        or "removed by the uploader" in text
    ):
        return ("Este vídeo está indisponível ou foi removido.", False, "indisponível/removido")

    if HTTP_5XX_REGEX.search(text):
        return ("Erro temporário do servidor (HTTP 5xx).", True, "erro do servidor")

    if (
        "timed out" in text
        or "timeout" in text
        or "temporarily unavailable" in text
        or "connection reset" in text
        or "connection refused" in text
        or "network is unreachable" in text
        or "name resolution" in text
        or "ssl" in text
        or "tls" in text
    ):
        return ("Falha de rede/timeout. Verifique sua conexão.", True, "falha de rede")

    if "unable to embed using ffprobe" in text or "unable to embed using ffprobe & ffmpeg" in text:
        return ("Não foi possível embutir a thumbnail no MP4. O vídeo será salvo sem capa.", False, "thumbnail")

    return ("Não foi possível baixar o vídeo. Verifique a URL e sua conexão.", False, "erro desconhecido")


def _download_with_retries(
    url: str,
    download_type: str,
    download_dir=None,
    progress_hook=None,
    on_success=None,
    on_error=None,
    on_retry=None,
    on_warning=None,
    max_attempts: int = 3,
    base_delay: int = 2,
):
    last_warning = None
    for attempt in range(1, max_attempts + 1):
        try:
            opts = build_options(download_type, download_dir, progress_hook)
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get("title", "vídeo")

            if last_warning and on_warning:
                on_warning(last_warning)

            if on_success:
                on_success(title)
            return

        except yt_dlp.utils.DownloadError as e:
            user_msg, retryable, reason = classify_error(str(e))

            if reason == "thumbnail":
                last_warning = user_msg
                if on_warning:
                    on_warning(user_msg)
                if on_success:
                    on_success("vídeo")
                return

            if retryable and attempt < max_attempts:
                delay = base_delay * (2 ** (attempt - 1))
                if on_retry:
                    on_retry(attempt, max_attempts, delay, reason)
                time.sleep(delay)
                continue

            if on_error:
                if retryable and attempt >= max_attempts:
                    on_error(f"{user_msg}\nTentativas esgotadas.")
                else:
                    on_error(user_msg)
            return

        except Exception as e:
            if on_error:
                on_error(f"Ocorreu um erro inesperado:\n{e}")
            return


def download(url: str, download_type: str, download_dir=None,
             progress_hook=None, on_success=None, on_error=None,
             on_complete=None, on_retry=None, on_warning=None):
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
        on_retry: Callable(attempt: int, max_attempts: int, delay: int, reason: str)
        on_warning: Callable(message: str) for non-fatal issues
    """
    def task():
        try:
            _download_with_retries(
                url=url,
                download_type=download_type,
                download_dir=download_dir,
                progress_hook=progress_hook,
                on_success=on_success,
                on_error=on_error,
                on_retry=on_retry,
                on_warning=on_warning,
            )
        finally:
            if on_complete:
                on_complete()

    threading.Thread(target=task, daemon=True).start()
