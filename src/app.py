"""Main window. All widget access happens on the Tk main thread."""

from __future__ import annotations

import io
import logging
import os
import queue
import subprocess
import threading
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image, ImageDraw

from src import downloader, theme as t
from src.constants import (
    APP_AUTHOR,
    APP_NAME,
    APP_VERSION,
    AUDIO_FORMATS,
    VIDEO_QUALITIES,
)
from src.downloader import (
    CancelledEvent,
    DoneEvent,
    DownloadJob,
    DownloadRequest,
    ErrorEvent,
    InfoErrorEvent,
    InfoJob,
    InfoReadyEvent,
    ProcessingEvent,
    ProgressEvent,
    RetryEvent,
    SuccessEvent,
    VideoInfo,
    WarningEvent,
)
from src.log import setup_logging
from src.paths import binaries, log_dir, resource_path
from src.settings import load_settings, save_settings
from src.ui_format import human_duration, progress_details, shorten_middle

logger = logging.getLogger(APP_NAME)

POLL_MS = 60
PREVIEW_DEBOUNCE_MS = 450
MODE_LABELS = {"video": "Vídeo (MP4)", "audio": "Somente áudio"}


@dataclass
class ThumbnailEvent:
    url: str
    image: Image.Image | None


def _rounded(img: Image.Image, size: tuple[int, int], radius: int) -> Image.Image:
    img = img.convert("RGB")
    # Cover-crop to the target aspect ratio.
    tw, th = size
    scale = max(tw / img.width, th / img.height)
    img = img.resize((max(tw, round(img.width * scale)), max(th, round(img.height * scale))), Image.LANCZOS)
    left, top = (img.width - tw) // 2, (img.height - th) // 2
    img = img.crop((left, top, left + tw, top + th))
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, tw - 1, th - 1), radius=radius, fill=255)
    out = Image.new("RGBA", size, (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    return out


def _fetch_thumbnail(url: str, events: queue.Queue) -> None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": f"{APP_NAME}/{APP_VERSION}"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read(2_000_000)
        img = _rounded(Image.open(io.BytesIO(data)), t.THUMB_SIZE, 10)
        events.put(ThumbnailEvent(url, img))
    except Exception as e:  # noqa: BLE001 - a missing thumbnail is cosmetic
        logger.debug("Thumbnail failed: %s", e)
        events.put(ThumbnailEvent(url, None))


def _font(size: int = 13, weight: str = "normal") -> ctk.CTkFont:
    return ctk.CTkFont(t.FONT_FAMILY, size=size, weight=weight)


class YTDownloaderApp:
    def __init__(self):
        setup_logging()
        ctk.set_appearance_mode("dark")

        self.settings = load_settings()
        self.events: queue.Queue = queue.Queue()
        self.job: DownloadJob | None = None
        self.info: VideoInfo | None = None
        self._pending_info_url: str | None = None
        self._debounce_id: str | None = None
        self._closing = False
        self._last_success_path: str | None = None
        self._thumb_image: ctk.CTkImage | None = None
        self._pending_warning: str | None = None

        self.root = ctk.CTk(fg_color=t.BG)
        self.root.title(APP_NAME)
        self.root.geometry("760x720")
        self.root.minsize(660, 700)
        self._set_icon()

        self._build_ui()
        self._apply_settings_to_ui()
        self._check_binaries()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.bind("<Return>", lambda _e: self._on_primary())
        self.root.bind("<Escape>", lambda _e: self._cancel_download())
        self.root.after(POLL_MS, self._poll_events)
        self.root.after(150, self.entry_url.focus_set)

    # ── Window setup ────────────────────────────────────────────────

    def _set_icon(self):
        icon = resource_path("assets", "icon.ico")
        if icon.is_file():
            # customtkinter resets the icon ~200 ms after start; set it after that.
            self.root.after(250, lambda: self.root.iconbitmap(str(icon)))

    # ── UI construction ─────────────────────────────────────────────

    def _card(self, parent, **pack) -> ctk.CTkFrame:
        card = ctk.CTkFrame(
            parent, fg_color=t.SURFACE, corner_radius=t.RADIUS, border_width=1, border_color=t.BORDER
        )
        card.pack(fill="x", **pack)
        return card

    def _build_ui(self):
        # Footer first so it's never squeezed out when the window is short.
        self._build_footer()
        main = ctk.CTkFrame(self.root, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=t.PAD, pady=(t.PAD - 4, 10))

        self._build_header(main)
        self._build_url_card(main)
        self._build_preview_card(main)
        self._build_options_card(main)
        self._build_action_area(main)

    def _build_header(self, parent):
        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.pack(fill="x", pady=(0, 14))

        logo = ctk.CTkLabel(
            header, text="▶", width=36, height=36, corner_radius=10,
            fg_color=t.ACCENT, text_color=t.ACCENT_TEXT, font=_font(16, "bold"),
        )
        logo.pack(side="left")

        titles = ctk.CTkFrame(header, fg_color="transparent")
        titles.pack(side="left", padx=12)
        ctk.CTkLabel(titles, text=APP_NAME, font=_font(20, "bold"), text_color=t.TEXT).pack(anchor="w")
        ctk.CTkLabel(
            titles, text="Baixe vídeos e músicas do YouTube", font=_font(12), text_color=t.TEXT_MUTED
        ).pack(anchor="w")

        ctk.CTkLabel(
            header, text=f"v{APP_VERSION}", font=_font(11), text_color=t.TEXT_FAINT,
            fg_color=t.SURFACE_2, corner_radius=8, width=56, height=24,
        ).pack(side="right")

    def _build_url_card(self, parent):
        card = self._card(parent, pady=(0, 12))
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=14)

        ctk.CTkLabel(inner, text="Link do vídeo", font=_font(12, "bold"), text_color=t.TEXT_MUTED).pack(anchor="w")

        row = ctk.CTkFrame(inner, fg_color="transparent")
        row.pack(fill="x", pady=(6, 0))

        # No textvariable: customtkinter disables the placeholder when one is set.
        self.entry_url = ctk.CTkEntry(
            row, height=40, corner_radius=t.RADIUS_SM, border_width=1,
            border_color=t.BORDER, fg_color=t.SURFACE_2, text_color=t.TEXT, font=_font(13),
            placeholder_text="https://www.youtube.com/watch?v=…", placeholder_text_color=t.TEXT_FAINT,
        )
        self.entry_url.pack(side="left", fill="x", expand=True)
        self.entry_url.bind("<FocusIn>", lambda _e: self.entry_url.configure(border_color=t.BORDER_FOCUS))
        self.entry_url.bind("<FocusOut>", lambda _e: self.entry_url.configure(border_color=t.BORDER))
        for seq in ("<KeyRelease>", "<<Paste>>", "<<Cut>>"):
            self.entry_url.bind(seq, lambda _e: self.root.after_idle(self._on_url_changed), add="+")

        self.btn_paste = ctk.CTkButton(
            row, text="Colar", width=84, height=40, corner_radius=t.RADIUS_SM, font=_font(13),
            fg_color=t.NEUTRAL, hover_color=t.NEUTRAL_HOVER, text_color=t.TEXT, command=self._paste,
        )
        self.btn_paste.pack(side="left", padx=(8, 0))

    def _build_preview_card(self, parent):
        card = self._card(parent, pady=(0, 12))
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=14)

        w, h = t.THUMB_SIZE
        self.thumb = ctk.CTkLabel(
            inner, text="▶", width=w, height=h, corner_radius=10, fg_color=t.SURFACE_2,
            text_color=t.TEXT_FAINT, font=_font(28),
        )
        self.thumb.pack(side="left")

        meta = ctk.CTkFrame(inner, fg_color="transparent")
        meta.pack(side="left", fill="both", expand=True, padx=(14, 0))

        self.lbl_title = ctk.CTkLabel(
            meta, text="Nenhum vídeo selecionado", font=_font(15, "bold"), text_color=t.TEXT,
            anchor="w", justify="left", wraplength=380,
        )
        self.lbl_title.pack(anchor="w", fill="x")
        self.lbl_meta = ctk.CTkLabel(
            meta, text="Cole um link acima para ver a prévia.", font=_font(12),
            text_color=t.TEXT_MUTED, anchor="w", justify="left",
        )
        self.lbl_meta.pack(anchor="w", pady=(4, 0))
        self.lbl_preview_status = ctk.CTkLabel(meta, text="", font=_font(12), text_color=t.TEXT_FAINT, anchor="w")
        self.lbl_preview_status.pack(anchor="w", pady=(8, 0))

        # Keep the title wrapping in sync with the window width.
        meta.bind("<Configure>", lambda e: self.lbl_title.configure(wraplength=max(200, e.width - 8)))

    def _option_row(self, parent, label: str) -> ctk.CTkFrame:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=5)
        ctk.CTkLabel(row, text=label, width=90, anchor="w", font=_font(13), text_color=t.TEXT_MUTED).pack(side="left")
        return row

    def _build_options_card(self, parent):
        card = self._card(parent, pady=(0, 14))
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=10)

        row = self._option_row(inner, "Formato")
        self.seg_mode = ctk.CTkSegmentedButton(
            row, values=list(MODE_LABELS.values()), height=34, corner_radius=t.RADIUS_SM, font=_font(13),
            fg_color=t.SURFACE_2, selected_color=t.SELECTED, selected_hover_color=t.SELECTED,
            unselected_color=t.SURFACE_2, unselected_hover_color=t.NEUTRAL, text_color=t.TEXT,
            command=self._on_mode_changed,
        )
        self.seg_mode.pack(side="left")

        row = self._option_row(inner, "Qualidade")
        self.opt_quality = ctk.CTkOptionMenu(
            row, values=list(VIDEO_QUALITIES), width=230, height=34, corner_radius=t.RADIUS_SM,
            font=_font(13), dropdown_font=_font(13), fg_color=t.SURFACE_2, button_color=t.NEUTRAL,
            button_hover_color=t.NEUTRAL_HOVER, text_color=t.TEXT, dropdown_fg_color=t.SURFACE_2,
            dropdown_hover_color=t.NEUTRAL, dropdown_text_color=t.TEXT, command=self._on_quality_changed,
        )
        self.opt_quality.pack(side="left")

        row = self._option_row(inner, "Salvar em")
        self.btn_folder = ctk.CTkButton(
            row, text="Alterar", width=84, height=34, corner_radius=t.RADIUS_SM, font=_font(13),
            fg_color=t.NEUTRAL, hover_color=t.NEUTRAL_HOVER, text_color=t.TEXT, command=self._choose_folder,
        )
        self.btn_folder.pack(side="right")
        self.lbl_folder = ctk.CTkLabel(row, text="", anchor="w", font=_font(13), text_color=t.TEXT)
        self.lbl_folder.pack(side="left", fill="x", expand=True)

    def _build_action_area(self, parent):
        self.btn_primary = ctk.CTkButton(
            parent, text="Baixar", height=46, corner_radius=t.RADIUS, font=_font(15, "bold"),
            fg_color=t.ACCENT, hover_color=t.ACCENT_HOVER, text_color=t.ACCENT_TEXT,
            text_color_disabled="#F0B3B5", command=self._on_primary,
        )
        self.btn_primary.pack(fill="x")

        prog = self.prog_frame = ctk.CTkFrame(parent, fg_color="transparent")
        prog.pack(fill="x", pady=(14, 0))
        top = ctk.CTkFrame(prog, fg_color="transparent")
        top.pack(fill="x")
        self.lbl_stage = ctk.CTkLabel(top, text="Pronto", font=_font(13), text_color=t.TEXT_MUTED, anchor="w")
        self.lbl_stage.pack(side="left")
        self.lbl_percent = ctk.CTkLabel(top, text="", font=_font(13, "bold"), text_color=t.TEXT)
        self.lbl_percent.pack(side="right")

        self.progress = ctk.CTkProgressBar(
            prog, height=8, corner_radius=4, fg_color=t.PROGRESS_TRACK, progress_color=t.PROGRESS_TRACK,
            mode="determinate",
        )
        self.progress.set(0)
        self.progress.pack(fill="x", pady=(6, 4))
        self.lbl_details = ctk.CTkLabel(prog, text="", font=_font(12), text_color=t.TEXT_FAINT, anchor="w")
        self.lbl_details.pack(fill="x")

        # Result banner (hidden until a job finishes)
        self.banner = ctk.CTkFrame(parent, corner_radius=t.RADIUS_SM, fg_color=t.SUCCESS_BG)
        self.lbl_banner = ctk.CTkLabel(
            self.banner, text="", font=_font(13), anchor="w", justify="left", text_color=t.TEXT, wraplength=420
        )
        self.lbl_banner.pack(side="left", fill="x", expand=True, padx=14, pady=10)
        self.btn_open_file = ctk.CTkButton(
            self.banner, text="Abrir", width=70, height=30, corner_radius=t.RADIUS_SM, font=_font(12),
            fg_color=t.NEUTRAL, hover_color=t.NEUTRAL_HOVER, text_color=t.TEXT, command=self._open_file,
        )
        self.btn_open_folder = ctk.CTkButton(
            self.banner, text="Mostrar na pasta", width=120, height=30, corner_radius=t.RADIUS_SM,
            font=_font(12), fg_color=t.NEUTRAL, hover_color=t.NEUTRAL_HOVER, text_color=t.TEXT,
            command=self._open_folder,
        )
        self.banner.bind("<Configure>", lambda e: self.lbl_banner.configure(wraplength=max(200, e.width - 260)))

    def _build_footer(self):
        footer = ctk.CTkFrame(self.root, fg_color="transparent")
        footer.pack(side="bottom", fill="x", padx=t.PAD, pady=(0, 10))
        ctk.CTkLabel(
            footer, text=f"Desenvolvido por {APP_AUTHOR}", font=_font(11), text_color=t.TEXT_FAINT
        ).pack(side="left")
        logs = ctk.CTkLabel(footer, text="Abrir logs", font=_font(11, "bold"), text_color=t.TEXT_MUTED, cursor="hand2")
        logs.pack(side="right")
        logs.bind("<Button-1>", lambda _e: self._open_path(log_dir(), select=False))

    # ── Settings <-> UI ─────────────────────────────────────────────

    def _apply_settings_to_ui(self):
        s = self.settings
        self.seg_mode.set(MODE_LABELS[s.mode])
        self._refresh_quality_menu()
        self._refresh_folder_label()

    def _refresh_quality_menu(self):
        if self.settings.mode == "video":
            self.opt_quality.configure(values=list(VIDEO_QUALITIES))
            self.opt_quality.set(self.settings.video_quality)
        else:
            self.opt_quality.configure(values=list(AUDIO_FORMATS))
            self.opt_quality.set(self.settings.audio_format)

    def _refresh_folder_label(self):
        self.lbl_folder.configure(text=shorten_middle(self.settings.download_dir, 48))

    def _on_mode_changed(self, label: str):
        self.settings.mode = next(k for k, v in MODE_LABELS.items() if v == label)
        self._refresh_quality_menu()
        save_settings(self.settings)

    def _on_quality_changed(self, value: str):
        if self.settings.mode == "video":
            self.settings.video_quality = value
        else:
            self.settings.audio_format = value
        save_settings(self.settings)

    def _choose_folder(self):
        folder = filedialog.askdirectory(initialdir=self.settings.download_dir, title="Escolha onde salvar")
        if folder:
            self.settings.download_dir = str(Path(folder))
            self._refresh_folder_label()
            save_settings(self.settings)

    def _check_binaries(self):
        bins = binaries()
        if not bins.get("ffmpeg"):
            self._show_banner("FFmpeg não encontrado. Reinstale o YTDownloader para baixar vídeos.", "error")
        elif not bins.get("deno"):
            self._show_banner(
                "Runtime JavaScript (Deno) não encontrado: só qualidades baixas estarão disponíveis.", "warning"
            )

    # ── URL / preview ───────────────────────────────────────────────

    def _paste(self):
        try:
            text = self.root.clipboard_get().strip()
        except Exception:  # noqa: BLE001 - empty or non-text clipboard
            return
        self.entry_url.delete(0, "end")
        self.entry_url.insert(0, text)
        self.entry_url.icursor("end")
        self._on_url_changed()

    def _on_url_changed(self):
        if self._debounce_id:
            self.root.after_cancel(self._debounce_id)
        self._debounce_id = self.root.after(PREVIEW_DEBOUNCE_MS, self._request_preview)

    def _current_url(self) -> str:
        return self.entry_url.get().strip()

    def _request_preview(self):
        self._debounce_id = None
        url = self._current_url()
        if self.info and self.info.url == url:
            return
        if not url:
            self.info = None
            self._pending_info_url = None
            self._reset_preview()
            return
        if not downloader.validate_url(url):
            self.info = None
            self._pending_info_url = None
            self._reset_preview("Link inválido", "Use um link do YouTube (youtube.com ou youtu.be).", t.WARNING)
            return
        if url == self._pending_info_url:
            return
        self._pending_info_url = url
        self.info = None
        self._set_thumbnail(None)
        self.lbl_title.configure(text="Carregando…")
        self.lbl_meta.configure(text="")
        self.lbl_preview_status.configure(text="⏳ Buscando informações do vídeo…", text_color=t.TEXT_FAINT)
        InfoJob(url, self.events).start()

    def _reset_preview(self, title="Nenhum vídeo selecionado", meta="Cole um link acima para ver a prévia.",
                       meta_color=t.TEXT_MUTED):
        self._set_thumbnail(None)
        self.lbl_title.configure(text=title)
        self.lbl_meta.configure(text=meta, text_color=meta_color)
        self.lbl_preview_status.configure(text="")

    def _set_thumbnail(self, img: Image.Image | None):
        if img is None:
            self._thumb_image = None
            self.thumb.configure(image=None, text="▶")
            return
        self._thumb_image = ctk.CTkImage(light_image=img, dark_image=img, size=t.THUMB_SIZE)
        self.thumb.configure(image=self._thumb_image, text="")

    def _on_info_ready(self, info: VideoInfo):
        if info.url != self._current_url():
            return  # user already typed something else
        self.info = info
        self._pending_info_url = None
        self.lbl_title.configure(text=info.title)
        bits = [b for b in (info.uploader, human_duration(info.duration)) if b]
        self.lbl_meta.configure(text="  ·  ".join(bits), text_color=t.TEXT_MUTED)
        self.lbl_preview_status.configure(text="✓ Pronto para baixar", text_color=t.SUCCESS)
        if info.thumbnail_url:
            threading.Thread(
                target=_fetch_thumbnail, args=(info.thumbnail_url, self.events), daemon=True
            ).start()

    def _on_info_error(self, event: InfoErrorEvent):
        if event.url != self._current_url():
            return
        self._pending_info_url = None
        self._reset_preview("Não foi possível carregar a prévia", event.message, t.DANGER)

    def _on_thumbnail(self, event: ThumbnailEvent):
        if self.info and self.info.thumbnail_url == event.url and event.image is not None:
            self._set_thumbnail(event.image)

    # ── Download ────────────────────────────────────────────────────

    def _on_primary(self):
        if self.job and self.job.is_alive():
            self._cancel_download()
        else:
            self._start_download()

    def _build_request(self, url: str) -> DownloadRequest:
        s = self.settings
        codec, bitrate = AUDIO_FORMATS[s.audio_format]
        return DownloadRequest(
            url=url,
            mode=s.mode,
            download_dir=Path(s.download_dir),
            max_height=VIDEO_QUALITIES[s.video_quality],
            audio_codec=codec,
            audio_bitrate=bitrate,
        )

    def _start_download(self):
        url = self._current_url()
        if not url:
            self._show_banner("Cole o link de um vídeo do YouTube.", "warning")
            self.entry_url.focus_set()
            return
        if not downloader.validate_url(url):
            self._show_banner("Esse link não parece ser do YouTube.", "warning")
            return
        folder = Path(self.settings.download_dir)
        if not folder.is_dir():
            self._show_banner("A pasta de destino não existe mais. Escolha outra.", "error")
            return

        self._hide_banner()
        self._pending_warning = None
        self._set_busy(True)
        self._set_stage("Preparando…", None)
        self.lbl_details.configure(text="")
        self.job = DownloadJob(self._build_request(url), self.events, info=self.info).start()

    def _cancel_download(self):
        if self.job and self.job.is_alive() and not self.job.cancelled:
            self.job.cancel()
            self.btn_primary.configure(state="disabled", text="Cancelando…")
            self._set_stage("Cancelando…", None)

    def _set_busy(self, busy: bool):
        state = "disabled" if busy else "normal"
        for w in (self.entry_url, self.btn_paste, self.seg_mode, self.opt_quality, self.btn_folder):
            w.configure(state=state)
        if busy:
            self.btn_primary.configure(
                text="Cancelar", fg_color=t.NEUTRAL, hover_color=t.NEUTRAL_HOVER, text_color=t.TEXT, state="normal"
            )
        else:
            self.btn_primary.configure(
                text="Baixar", fg_color=t.ACCENT, hover_color=t.ACCENT_HOVER, text_color=t.ACCENT_TEXT,
                state="normal",
            )

    def _set_stage(self, text: str, fraction: float | None):
        self.lbl_stage.configure(text=text)
        if fraction is None:
            if self.progress.cget("mode") != "indeterminate":
                self.progress.configure(mode="indeterminate", progress_color=t.PROGRESS_FILL)
                self.progress.start()
            self.lbl_percent.configure(text="")
        else:
            if self.progress.cget("mode") != "determinate":
                self.progress.stop()
                self.progress.configure(mode="determinate")
            self.progress.configure(progress_color=t.PROGRESS_FILL)
            self.progress.set(fraction)
            self.lbl_percent.configure(text=f"{int(fraction * 100)}%")

    def _reset_progress(self, stage: str = "Pronto"):
        self.progress.stop()
        self.progress.configure(mode="determinate", progress_color=t.PROGRESS_TRACK)
        self.progress.set(0)
        self.lbl_stage.configure(text=stage)
        self.lbl_percent.configure(text="")
        self.lbl_details.configure(text="")

    # ── Event loop ──────────────────────────────────────────────────

    def _poll_events(self):
        try:
            while True:
                self._handle_event(self.events.get_nowait())
        except queue.Empty:
            pass
        if not self._closing or (self.job and self.job.is_alive()):
            self.root.after(POLL_MS, self._poll_events)

    def _handle_event(self, e):
        if isinstance(e, ProgressEvent):
            self._set_stage(e.stage, e.fraction)
            self.lbl_details.configure(text=progress_details(e.downloaded, e.total, e.speed, e.eta))
        elif isinstance(e, ProcessingEvent):
            self._set_stage(e.message, None)
            self.lbl_details.configure(text="")
        elif isinstance(e, RetryEvent):
            self._set_stage(f"{e.reason.capitalize()}: tentando de novo em {e.delay}s "
                            f"({e.attempt}/{e.max_attempts})", None)
        elif isinstance(e, WarningEvent):
            self._pending_warning = e.message
        elif isinstance(e, SuccessEvent):
            self._on_success(e)
        elif isinstance(e, ErrorEvent):
            self._reset_progress("Falhou")
            self._show_banner(e.message, "error")
        elif isinstance(e, CancelledEvent):
            self._reset_progress("Cancelado")
            self._show_banner("Download cancelado.", "warning")
        elif isinstance(e, DoneEvent):
            self._set_busy(False)
            self.job = None
            if self._closing:
                self.root.destroy()
        elif isinstance(e, InfoReadyEvent):
            self._on_info_ready(e.info)
        elif isinstance(e, InfoErrorEvent):
            self._on_info_error(e)
        elif isinstance(e, ThumbnailEvent):
            self._on_thumbnail(e)

    def _on_success(self, e: SuccessEvent):
        self._reset_progress("Concluído")
        self.progress.configure(progress_color=t.PROGRESS_FILL)
        self.progress.set(1)
        self._last_success_path = e.filepath
        warning = self._pending_warning
        self._pending_warning = None
        text = f"✓ Download concluído\n{e.title}"
        if warning:
            text += f"\n⚠ {warning}"
        self._show_banner(text, "warning" if warning else "success", with_actions=True)

    # ── Banner ──────────────────────────────────────────────────────

    def _show_banner(self, text: str, kind: str, with_actions: bool = False):
        colors = {
            "success": (t.SUCCESS_BG, t.TEXT),
            "warning": (t.WARNING_BG, t.TEXT),
            "error": (t.DANGER_BG, t.TEXT),
        }
        bg, fg = colors.get(kind, colors["success"])
        self.banner.configure(fg_color=bg)
        self.lbl_banner.configure(text=text, text_color=fg)
        self.btn_open_folder.pack_forget()
        self.btn_open_file.pack_forget()
        if with_actions:
            self.btn_open_folder.pack(side="right", padx=(0, 12), pady=10)
            if self._last_success_path and Path(self._last_success_path).is_file():
                self.btn_open_file.pack(side="right", padx=(0, 8), pady=10)
        # The banner takes the place of the progress area (keeps the window height stable).
        self.prog_frame.pack_forget()
        if not self.banner.winfo_ismapped():
            self.banner.pack(fill="x", pady=(14, 0), after=self.btn_primary)

    def _hide_banner(self):
        self.banner.pack_forget()
        if not self.prog_frame.winfo_ismapped():
            self.prog_frame.pack(fill="x", pady=(14, 0), after=self.btn_primary)

    # ── Shell helpers ───────────────────────────────────────────────

    def _open_path(self, path: Path, select: bool):
        try:
            path = Path(path)
            if os.name == "nt":
                if select and path.is_file():
                    subprocess.Popen(["explorer", "/select,", str(path)])
                else:
                    path.mkdir(parents=True, exist_ok=True)
                    os.startfile(str(path))  # noqa: S606 - opening a local folder/file
            else:
                subprocess.Popen(["xdg-open", str(path if not select else path.parent)])
        except OSError as e:
            logger.warning("Could not open %s: %s", path, e)

    def _open_folder(self):
        if self._last_success_path and Path(self._last_success_path).is_file():
            self._open_path(Path(self._last_success_path), select=True)
        else:
            self._open_path(Path(self.settings.download_dir), select=False)

    def _open_file(self):
        if self._last_success_path and Path(self._last_success_path).is_file():
            try:
                os.startfile(self._last_success_path)  # noqa: S606
            except (OSError, AttributeError) as e:
                logger.warning("Could not open file: %s", e)

    # ── Lifecycle ───────────────────────────────────────────────────

    def _on_close(self):
        if self.job and self.job.is_alive():
            if not messagebox.askyesno(
                "Download em andamento", "Um download está em andamento.\nCancelar e sair?", parent=self.root
            ):
                return
            self._closing = True
            self.job.cancel()
            self.root.withdraw()
            # DoneEvent will destroy the window; hard-stop after 5 s just in case.
            self.root.after(5000, self.root.destroy)
            return
        save_settings(self.settings)
        self.root.destroy()

    def run(self):
        self.root.mainloop()
