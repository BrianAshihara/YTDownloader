"""Pure formatting helpers used by the UI (kept separate so they're testable)."""

from __future__ import annotations


def human_bytes(n: float | None) -> str:
    if n is None or n < 0:
        return "?"
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(n)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} B"
            return f"{value:.1f} {unit}".replace(".", ",")
        value /= 1024
    return "?"


def human_duration(seconds: float | None) -> str:
    if seconds is None or seconds < 0:
        return ""
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def progress_details(downloaded: int, total: int | None, speed: float | None, eta: int | None) -> str:
    parts = []
    if total:
        parts.append(f"{human_bytes(downloaded)} de {human_bytes(total)}")
    elif downloaded:
        parts.append(human_bytes(downloaded))
    if speed:
        parts.append(f"{human_bytes(speed)}/s")
    if eta is not None and eta >= 0:
        parts.append(f"{human_duration(eta)} restantes")
    return "  ·  ".join(parts)


def shorten_middle(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    if max_len <= 3:
        return text[:max_len]
    keep = max_len - 1
    head = keep // 2
    tail = keep - head
    return f"{text[:head]}…{text[-tail:]}"
