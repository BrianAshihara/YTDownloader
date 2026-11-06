"""
Download core built on top of yt-dlp.

The UI never calls yt-dlp directly. It creates a :class:`DownloadJob` (or
:class:`InfoJob` for the preview) and reads typed events from a
``queue.Queue`` on the Tk main thread. Worker threads never touch widgets.
"""

from __future__ import annotations

import copy
import gc
import logging
import queue
import re
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

import yt_dlp
from yt_dlp.utils import DownloadCancelled, DownloadError

from src.constants import APP_NAME, DOWNLOAD_DIR, YOUTUBE_HOSTS
from src.log import YtDlpLogger
from src.paths import binaries

logger = logging.getLogger(APP_NAME)

# How long a preview (extracted info) can be reused for the actual download.
# YouTube stream URLs expire after a few hours; stay well below that.
INFO_REUSE_SECONDS = 20 * 60
# Minimum interval between two progress events sent to the UI.
PROGRESS_THROTTLE_SECONDS = 0.1

_HTTP_5XX = re.compile(r"http error 5\d\d", re.IGNORECASE)
_SSL_TLS = re.compile(r"\b(ssl|tls)\b|certificate", re.IGNORECASE)

# Keys are yt-dlp's PostProcessor.pp_key() (class name without "FFmpeg"/"PP").
POSTPROCESSOR_LABELS = {
    "Merger": "Juntando áudio e vídeo…",
    "ExtractAudio": "Convertendo áudio…",
    "Metadata": "Gravando metadados…",
    "EmbedThumbnail": "Embutindo a capa…",
    "ThumbnailsConvertor": "Preparando a capa…",
    "MoveFilesAfterDownload": "Finalizando…",
}


def postprocessor_label(key: str) -> str:
    if key in POSTPROCESSOR_LABELS:
        return POSTPROCESSOR_LABELS[key]
    if key.startswith("Fixup"):
        return "Ajustando o arquivo…"
    return "Processando…"


# ── Requests / results ──────────────────────────────────────────────


@dataclass(frozen=True)
class DownloadRequest:
    url: str
    mode: str = "video"  # "video" | "audio"
    download_dir: Path = DOWNLOAD_DIR
    max_height: int | None = None  # video only; None = best
    audio_codec: str = "mp3"  # "mp3" | "m4a"
    audio_bitrate: int | None = 192  # mp3 only


@dataclass
class VideoInfo:
    url: str
    id: str
    title: str
    uploader: str
    duration: int | None
    thumbnail_url: str | None
    raw: dict = field(repr=False, default_factory=dict)
    fetched_at: float = field(default_factory=time.monotonic)

    def is_fresh(self) -> bool:
        return time.monotonic() - self.fetched_at < INFO_REUSE_SECONDS


# ── Events (worker thread -> UI) ────────────────────────────────────


@dataclass
class ProgressEvent:
    stage: str
    fraction: float | None  # overall 0..1, None when unknown
    downloaded: int = 0
    total: int | None = None
    speed: float | None = None
    eta: int | None = None


@dataclass
class ProcessingEvent:
    message: str


@dataclass
class RetryEvent:
    attempt: int
    max_attempts: int
    delay: int
    reason: str


@dataclass
class WarningEvent:
    message: str


@dataclass
class SuccessEvent:
    title: str
    filepath: str | None


@dataclass
class ErrorEvent:
    message: str


@dataclass
class CancelledEvent:
    pass


@dataclass
class DoneEvent:
    """Always the last event of a job."""


@dataclass
class InfoReadyEvent:
    info: VideoInfo


@dataclass
class InfoErrorEvent:
    url: str
    message: str


class PlaylistNotSupported(Exception):
    pass


# ── Validation ──────────────────────────────────────────────────────


def validate_url(url: str) -> bool:
    """Fast sanity check: is this a YouTube URL with a path or query?"""
    url = (url or "").strip()
    if not url or any(c.isspace() for c in url):
        return False
    if "://" not in url:
        url = "https://" + url
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    host = (parsed.hostname or "").lower()
    if host not in YOUTUBE_HOSTS:
        return False
    return bool(parsed.path.strip("/") or parsed.query)


# ── yt-dlp options ──────────────────────────────────────────────────


def _base_options(bins: dict[str, str | None], ydl_logger: Any = None) -> dict:
    opts: dict[str, Any] = {
        "quiet": True,
        "noprogress": True,
        "no_warnings": False,  # warnings go to our logger instead of being hidden
        "noplaylist": True,  # "watch?v=X&list=Y" downloads only X
        "socket_timeout": 20,
        "retries": 5,
        "fragment_retries": 5,
        "extractor_retries": 3,
    }
    if ydl_logger is not None:
        opts["logger"] = ydl_logger

    # YouTube needs a JavaScript runtime to unlock the full format list.
    if bins.get("deno"):
        opts["js_runtimes"] = {"deno": {"path": bins["deno"]}}

    if bins.get("ffmpeg"):
        # yt-dlp finds ffprobe in the same folder as ffmpeg.
        opts["ffmpeg_location"] = str(Path(bins["ffmpeg"]).parent)
    return opts


def build_options(
    request: DownloadRequest,
    progress_hook: Callable | None = None,
    postprocessor_hook: Callable | None = None,
    ydl_logger: Any = None,
    bins: dict[str, str | None] | None = None,
) -> dict:
    """Build the yt-dlp options dict for a download request."""
    bins = binaries() if bins is None else bins
    opts = _base_options(bins, ydl_logger)
    target_dir = Path(request.download_dir)

    opts.update({
        # .150B keeps the full path under Windows' 260-char limit in most cases.
        "outtmpl": str(target_dir / "%(title).150B.%(ext)s"),
        "writethumbnail": True,
        "convertthumbnails": "jpg",
    })
    if progress_hook:
        opts["progress_hooks"] = [progress_hook]
    if postprocessor_hook:
        opts["postprocessor_hooks"] = [postprocessor_hook]

    metadata_pp = {"key": "FFmpegMetadata", "add_metadata": True, "add_chapters": True}
    thumbnail_pp = {"key": "EmbedThumbnail"}

    if request.mode == "video":
        res = f"res:{request.max_height}" if request.max_height else "res"
        opts.update({
            "format": "bv*+ba/b",
            # Highest resolution first (capped by the chosen quality), then
            # prefer H.264/AAC in MP4 when there's a tie: plays everywhere.
            "format_sort": [res, "fps", "vcodec:h264", "acodec:aac", "ext:mp4:m4a"],
            "merge_output_format": "mp4",
            "postprocessors": [metadata_pp, thumbnail_pp],
        })
    else:
        codec = request.audio_codec if request.audio_codec in ("mp3", "m4a") else "mp3"
        extract = {"key": "FFmpegExtractAudio", "preferredcodec": codec}
        if codec == "mp3":
            extract["preferredquality"] = str(request.audio_bitrate or 192)
            fmt = "ba/b"
        else:
            # AAC streams are copied as-is (no re-encode, no quality loss).
            fmt = "ba[acodec^=mp4a]/ba/b"
        opts.update({
            "format": fmt,
            "postprocessors": [extract, metadata_pp, thumbnail_pp],
        })

    return opts


def build_info_options(bins: dict[str, str | None] | None = None, ydl_logger: Any = None) -> dict:
    bins = binaries() if bins is None else bins
    opts = _base_options(bins, ydl_logger)
    opts["skip_download"] = True
    return opts


# ── Error classification ────────────────────────────────────────────


def classify_error(error: str) -> tuple[str, bool, str]:
    """Return (user message, retryable, short reason)."""
    text = (error or "").lower()

    if (
        "unable to embed using ffprobe" in text
        or "thumbnail embedding" in text
        or "embedthumbnail" in text
    ):
        return ("Não foi possível embutir a capa. O arquivo foi salvo sem ela.", False, "thumbnail")

    if "ffmpeg" in text and ("not found" in text or "not installed" in text):
        return ("FFmpeg não encontrado. Reinstale o YTDownloader.", False, "ffmpeg ausente")

    if "http error 429" in text or "too many requests" in text or "rate limit" in text:
        return (
            "O YouTube limitou as requisições (HTTP 429).\nAguarde alguns minutos e tente de novo.",
            False,
            "muitas requisições",
        )

    if "not a bot" in text or "confirm you're not a bot" in text:
        return (
            "O YouTube pediu verificação anti-robô.\nTente novamente mais tarde.",
            False,
            "verificação anti-robô",
        )

    if "private video" in text or "is private" in text:
        return ("Este vídeo é privado.", False, "vídeo privado")

    if "members-only" in text or "join this channel" in text:
        return ("Este vídeo é exclusivo para membros do canal.", False, "somente membros")

    if (
        "not available in your country" in text
        or "not available in your region" in text
        or "not made this video available in your country" in text
    ):
        return ("Este vídeo não está disponível no seu país/região.", False, "restrição geográfica")

    if "sign in to confirm your age" in text or "age-restricted" in text:
        return ("Este vídeo requer verificação de idade.", False, "restrição de idade")

    if "live event will begin" in text or "premieres in" in text:
        return ("Esta transmissão ainda não começou.", False, "live não iniciada")

    if (
        "video unavailable" in text
        or "this video is unavailable" in text
        or "removed by the uploader" in text
    ):
        return ("Este vídeo está indisponível ou foi removido.", False, "indisponível/removido")

    if "requested format is not available" in text:
        return ("Nenhum formato compatível foi encontrado para este vídeo.", False, "formato indisponível")

    if _HTTP_5XX.search(text):
        return ("Erro temporário do servidor (HTTP 5xx).", True, "erro do servidor")

    if (
        "timed out" in text
        or "timeout" in text
        or "temporarily unavailable" in text
        or "connection reset" in text
        or "connection refused" in text
        or "connection aborted" in text
        or "network is unreachable" in text
        or "name resolution" in text
        or "getaddrinfo failed" in text
        or "incomplete read" in text
        or _SSL_TLS.search(text)
    ):
        return ("Falha de rede. Verifique sua conexão.", True, "falha de rede")

    return ("Não foi possível baixar. Verifique a URL e sua conexão.", False, "erro desconhecido")


def js_runtime_warning(warnings: list[str]) -> str | None:
    for w in warnings:
        if "javascript runtime" in w.lower():
            return "Runtime JavaScript ausente: alguns formatos (qualidades) podem não estar disponíveis."
    return None


# ── Info (preview) ──────────────────────────────────────────────────


def _thumbnail_for(raw: dict) -> str | None:
    video_id = raw.get("id")
    if video_id and "youtube" in (raw.get("extractor") or "").lower():
        # 320x180, small and always present.
        return f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg"
    return raw.get("thumbnail")


def fetch_info(url: str, bins: dict[str, str | None] | None = None, ydl_logger: Any = None) -> VideoInfo:
    """Extract metadata without downloading. Blocking; run in a thread."""
    opts = build_info_options(bins, ydl_logger)
    with yt_dlp.YoutubeDL(opts) as ydl:
        raw = ydl.extract_info(url, download=False, process=False)
        # Resolve redirects such as "watch?v=X&list=Y" -> video X.
        for _ in range(3):
            if raw.get("_type") in ("url", "url_transparent") and raw.get("url"):
                raw = ydl.extract_info(raw["url"], download=False, process=False)
            else:
                break

    if raw.get("_type") == "playlist":
        raise PlaylistNotSupported(raw.get("title") or "playlist")

    return VideoInfo(
        url=url,
        id=raw.get("id") or "",
        title=raw.get("title") or "Sem título",
        uploader=raw.get("uploader") or raw.get("channel") or "",
        duration=raw.get("duration"),
        thumbnail_url=_thumbnail_for(raw),
        raw=raw,
    )


class InfoJob:
    """Fetch the preview in the background and post the result to a queue."""

    def __init__(self, url: str, events: queue.Queue):
        self.url = url
        self.events = events
        self.thread = threading.Thread(target=self._run, name="info", daemon=True)

    def start(self) -> "InfoJob":
        self.thread.start()
        return self

    def _run(self) -> None:
        try:
            info = fetch_info(self.url, ydl_logger=YtDlpLogger())
            self.events.put(InfoReadyEvent(info))
        except PlaylistNotSupported:
            self.events.put(InfoErrorEvent(self.url, "Playlists ainda não são suportadas. Use o link de um vídeo."))
        except DownloadError as e:
            msg, _, _ = classify_error(str(e))
            self.events.put(InfoErrorEvent(self.url, msg))
        except Exception as e:  # noqa: BLE001 - must never crash the thread silently
            logger.exception("Preview failed")
            self.events.put(InfoErrorEvent(self.url, f"Não foi possível carregar a prévia: {e}"))


# ── Download job ────────────────────────────────────────────────────


class _ProgressTracker:
    """Turns raw yt-dlp progress dicts into overall progress events."""

    def __init__(self, mode: str):
        self.mode = mode
        self._last_emit = 0.0
        self.touched_files: set[str] = set()
        # yt-dlp strips "requested_formats" from the per-stream info passed to
        # progress hooks, so we capture it once before the download starts.
        self.formats: list[dict] = []

    def stage_info(self, info: dict) -> tuple[str, float, float]:
        """Return (label, offset, weight) of the current stream in the overall bar."""
        formats = info.get("requested_formats") or self.formats
        current = info.get("format_id")
        is_video = (info.get("vcodec") or "none") != "none"
        label = "Baixando vídeo" if is_video and self.mode == "video" else "Baixando áudio"

        if len(formats) < 2:
            return label, 0.0, 1.0

        ids = [f.get("format_id") for f in formats]
        idx = ids.index(current) if current in ids else 0
        sizes = [f.get("filesize") or f.get("filesize_approx") for f in formats]
        if all(sizes):
            total = float(sum(sizes))
            offset = sum(sizes[:idx]) / total
            weight = sizes[idx] / total
        else:
            offset, weight = idx / len(formats), 1 / len(formats)
        return f"{label} ({idx + 1}/{len(formats)})", offset, weight

    def to_event(self, d: dict, force: bool = False) -> ProgressEvent | None:
        # Only files we are actively writing are eligible for cleanup on cancel.
        # (An already-downloaded file only reports "finished", never "downloading".)
        if d.get("status") == "downloading":
            for key in ("tmpfilename", "filename"):
                if d.get(key):
                    self.touched_files.add(d[key])

        now = time.monotonic()
        if not force and now - self._last_emit < PROGRESS_THROTTLE_SECONDS:
            return None
        self._last_emit = now

        label, offset, weight = self.stage_info(d.get("info_dict") or {})
        downloaded = d.get("downloaded_bytes") or 0
        total = d.get("total_bytes") or d.get("total_bytes_estimate") or None
        if d.get("status") == "finished":
            stream_fraction = 1.0
        elif total:
            stream_fraction = min(downloaded / total, 1.0)
        else:
            stream_fraction = None

        overall = None if stream_fraction is None else offset + weight * stream_fraction
        return ProgressEvent(
            stage=label,
            fraction=overall,
            downloaded=downloaded,
            total=total,
            speed=d.get("speed"),
            eta=d.get("eta"),
        )


class _FormatSpy(yt_dlp.postprocessor.PostProcessor):
    """Runs right before the download and records the selected streams."""

    def __init__(self, tracker: _ProgressTracker):
        super().__init__()
        self.tracker = tracker

    def run(self, info):
        self.tracker.formats = list(info.get("requested_formats") or [])
        return [], info


class DownloadJob:
    """One download running in a background thread."""

    def __init__(
        self,
        request: DownloadRequest,
        events: queue.Queue,
        info: VideoInfo | None = None,
        max_attempts: int = 3,
        base_delay: int = 3,
        bins: dict[str, str | None] | None = None,
    ):
        self.request = request
        self.events = events
        self.info = info if info and info.url == request.url else None
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.bins = binaries() if bins is None else bins
        self._cancel = threading.Event()
        self._started_at = time.time()
        self._tracker = _ProgressTracker(request.mode)
        self._last_filepath: str | None = None
        self._last_stage_label: str | None = None
        self.thread = threading.Thread(target=self._run_safe, name="download", daemon=True)

    # Public API ------------------------------------------------------

    def start(self) -> "DownloadJob":
        self.thread.start()
        return self

    def cancel(self) -> None:
        self._cancel.set()

    @property
    def cancelled(self) -> bool:
        return self._cancel.is_set()

    def is_alive(self) -> bool:
        return self.thread.is_alive()

    # Hooks (run on the worker thread) --------------------------------

    def _progress_hook(self, d: dict) -> None:
        if self._cancel.is_set():
            raise DownloadCancelled()
        status = d.get("status")
        if status not in ("downloading", "finished"):
            return
        event = self._tracker.to_event(d, force=status == "finished")
        if event:
            self.events.put(event)

    def _postprocessor_hook(self, d: dict) -> None:
        if self._cancel.is_set():
            raise DownloadCancelled()
        info = d.get("info_dict") or {}
        if info.get("filepath"):
            self._last_filepath = info["filepath"]
        if d.get("status") == "started":
            label = postprocessor_label(d.get("postprocessor") or "")
            if label != self._last_stage_label:
                self._last_stage_label = label
                self.events.put(ProcessingEvent(label))

    # Worker ------------------------------------------------------------

    def _emit(self, event) -> None:
        self.events.put(event)

    def _run_safe(self) -> None:
        try:
            self._run()
        except Exception as e:  # noqa: BLE001
            logger.exception("Unexpected download failure")
            self._emit(ErrorEvent(f"Ocorreu um erro inesperado:\n{e}"))
        finally:
            self._emit(DoneEvent())

    def _title(self) -> str:
        return self.info.title if self.info else "arquivo"

    def _run(self) -> None:
        if not self.bins.get("ffmpeg"):
            self._emit(ErrorEvent("FFmpeg não encontrado.\nReinstale o YTDownloader ou instale o FFmpeg."))
            return

        logger.info("Download start: %s", self.request)
        if self._attempt_loop() == "cancelled":
            # Cleanup must happen *after* the exception is gone: its traceback
            # keeps yt-dlp's frames (and their open file handles) alive.
            gc.collect()
            self._handle_cancel()

    def _attempt_loop(self) -> str | None:
        """Run the download with retries. Returns "cancelled" if cancelled."""
        for attempt in range(1, self.max_attempts + 1):
            ydl_logger = YtDlpLogger()
            opts = build_options(
                self.request,
                progress_hook=self._progress_hook,
                postprocessor_hook=self._postprocessor_hook,
                ydl_logger=ydl_logger,
                bins=self.bins,
            )
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.add_post_processor(_FormatSpy(self._tracker), when="before_dl")
                    if self.info and self.info.is_fresh() and attempt == 1:
                        # Reuse the preview extraction: saves several seconds.
                        result = ydl.process_ie_result(copy.deepcopy(self.info.raw), download=True)
                    else:
                        result = ydl.extract_info(self.request.url, download=True)

                if result and result.get("_type") == "playlist":
                    self._emit(ErrorEvent("Playlists ainda não são suportadas."))
                    return

                warning = js_runtime_warning(ydl_logger.warnings)
                if warning:
                    self._emit(WarningEvent(warning))

                title = (result or {}).get("title") or self._title()
                self._emit(SuccessEvent(title, self._final_path(result)))
                logger.info("Download finished: %s", title)
                return

            except DownloadCancelled:
                return "cancelled"

            except DownloadError as e:
                if self._cancel.is_set():
                    return "cancelled"

                logger.warning("Attempt %d failed: %s", attempt, e)
                user_msg, retryable, reason = classify_error(str(e))

                if reason == "thumbnail":
                    self._emit(WarningEvent(user_msg))
                    self._emit(SuccessEvent(self._title(), self._last_filepath))
                    return

                if retryable and attempt < self.max_attempts:
                    delay = self.base_delay * (2 ** (attempt - 1))
                    self._emit(RetryEvent(attempt, self.max_attempts, delay, reason))
                    if self._cancel.wait(delay):
                        return "cancelled"
                    continue

                if retryable:
                    user_msg += "\nTentativas esgotadas."
                self._emit(ErrorEvent(user_msg))
                return

    def _final_path(self, result: dict | None) -> str | None:
        if result:
            downloads = result.get("requested_downloads") or []
            if downloads and downloads[-1].get("filepath"):
                return downloads[-1]["filepath"]
            if result.get("filepath"):
                return result["filepath"]
        return self._last_filepath

    def _handle_cancel(self) -> None:
        logger.info("Download cancelled; cleaning up partial files")
        cleanup_partial_files(self._tracker.touched_files, since=self._started_at)
        self._emit(CancelledEvent())


_STREAM_SUFFIX = re.compile(r"\.f[\w-]+\.\w+$")
_LEFTOVER = re.compile(r"(\.part(-Frag\d+(\.part)?)?|\.ytdl|\.temp\.\w+|\.(webp|jpg|jpeg|png))$", re.IGNORECASE)


def _base_name(filename: str) -> str:
    """'Title.f137.mp4.part' -> 'Title'; 'Title.webm' -> 'Title'."""
    name = re.sub(r"\.part$", "", filename)
    if _STREAM_SUFFIX.search(name):
        return _STREAM_SUFFIX.sub("", name)
    return name.rsplit(".", 1)[0] if "." in name else name


def cleanup_partial_files(paths, since: float = 0.0, attempts: int = 5, wait: float = 0.3) -> None:
    """
    Remove what a cancelled download leaves behind: .part pieces, fragment
    files, separate audio/video streams and the downloaded thumbnail.

    Only files sharing the base name of a file we were writing *and* modified
    after the job started are touched, so existing downloads are never removed.
    """
    targets: set[Path] = set()
    for raw in paths:
        p = Path(raw)
        base = _base_name(p.name)
        if not base:
            continue
        try:
            siblings = list(p.parent.iterdir())
        except OSError:
            continue
        for f in siblings:
            if not f.is_file() or not f.name.startswith(base + "."):
                continue
            rest = f.name[len(base):]
            if not (_LEFTOVER.search(rest) or _STREAM_SUFFIX.match(rest)):
                continue
            try:
                if f.stat().st_mtime + 1 < since:
                    continue
            except OSError:
                continue
            targets.add(f)

    # On Windows the downloader may still hold a handle for a moment.
    for attempt in range(attempts):
        for f in list(targets):
            try:
                f.unlink()
                targets.discard(f)
            except FileNotFoundError:
                targets.discard(f)
            except OSError:
                pass
        if not targets:
            return
        time.sleep(wait)
    logger.warning("Could not remove partial files: %s", [str(f) for f in targets])
