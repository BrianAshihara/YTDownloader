from tkinter import messagebox
import customtkinter as ctk

from src.constants import APP_NAME, DOWNLOAD_DIR
from src import downloader


class YTDownloaderApp:
    """Main application window for YTDownloader."""

    def __init__(self):
        self.root = ctk.CTk()
        self.root.title(f"🎬 {APP_NAME}")
        self.root.geometry("560x420")
        self.root.resizable(False, False)

        self.download_dir = DOWNLOAD_DIR
        self._last_warning = None
        self._setup_styles()
        self._build_ui()

    # ── Styling ─────────────────────────────────────────────────────

    def _setup_styles(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

    # ── UI Construction ─────────────────────────────────────────────

    def _build_ui(self):
        self.root.configure(fg_color="#0F1214")

        container = ctk.CTkFrame(
            self.root,
            fg_color="#151A1E",
            corner_radius=18,
            border_width=1,
            border_color="#242C33",
        )
        container.pack(padx=24, pady=24, fill="both", expand=True)

        header = ctk.CTkFrame(container, fg_color="transparent")
        header.pack(fill="x", padx=22, pady=(18, 6))

        ctk.CTkLabel(
            header,
            text=f"🎬 {APP_NAME}",
            font=ctk.CTkFont("Segoe UI", size=22, weight="bold"),
            text_color="#F2F2F2",
        ).pack(anchor="w")

        ctk.CTkLabel(
            header,
            text="Baixe vídeos ou áudios do YouTube com alta qualidade.",
            font=ctk.CTkFont("Segoe UI", size=11),
            text_color="#A6B0B9",
        ).pack(anchor="w", pady=(4, 0))

        entry_wrap = ctk.CTkFrame(container, fg_color="transparent")
        entry_wrap.pack(fill="x", padx=22, pady=(12, 4))

        ctk.CTkLabel(
            entry_wrap,
            text="URL do YouTube",
            font=ctk.CTkFont("Segoe UI", size=10, weight="bold"),
            text_color="#C9D1D9",
        ).pack(anchor="w", pady=(0, 6))

        self.entry_url = ctk.CTkEntry(
            entry_wrap,
            height=38,
            corner_radius=10,
            border_width=1,
            border_color="#2A3239",
            fg_color="#1B2228",
            text_color="#E6E6E6",
            placeholder_text="Cole a URL aqui…",
        )
        self.entry_url.pack(fill="x")

        actions = ctk.CTkFrame(container, fg_color="transparent")
        actions.pack(fill="x", padx=22, pady=(18, 6))

        self.btn_video = ctk.CTkButton(
            actions,
            text="Baixar Vídeo (MP4)",
            height=40,
            corner_radius=10,
            font=ctk.CTkFont("Segoe UI", size=11, weight="bold"),
            fg_color="#1F8A63",
            hover_color="#197051",
            text_color="white",
            command=lambda: self._start_download("video"),
        )
        self.btn_video.grid(row=0, column=0, padx=(0, 10), sticky="ew")

        self.btn_audio = ctk.CTkButton(
            actions,
            text="Baixar Áudio (MP3)",
            height=40,
            corner_radius=10,
            font=ctk.CTkFont("Segoe UI", size=11, weight="bold"),
            fg_color="#2F6FB3",
            hover_color="#275E95",
            text_color="white",
            command=lambda: self._start_download("audio"),
        )
        self.btn_audio.grid(row=0, column=1, padx=(10, 0), sticky="ew")

        actions.grid_columnconfigure(0, weight=1)
        actions.grid_columnconfigure(1, weight=1)

        progress_wrap = ctk.CTkFrame(container, fg_color="transparent")
        progress_wrap.pack(fill="x", padx=22, pady=(12, 4))

        self.progress_bar = ctk.CTkProgressBar(
            progress_wrap,
            height=10,
            corner_radius=10,
            fg_color="#20262C",
            progress_color="#20262C",
        )
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x")

        self.label_status = ctk.CTkLabel(
            container,
            text="",
            font=ctk.CTkFont("Segoe UI", size=10),
            text_color="#A6B0B9",
        )
        self.label_status.pack(pady=(8, 2))

        ctk.CTkLabel(
            container,
            text="Desenvolvido por Brian — Projeto YTDownloader",
            font=ctk.CTkFont("Segoe UI", size=9),
            text_color="#7F8A94",
        ).pack(side="bottom", pady=12)

    # ── Download Logic ──────────────────────────────────────────────

    def _start_download(self, download_type: str):
        url = self.entry_url.get().strip()

        if not url:
            messagebox.showerror("Erro", "Por favor, insira a URL do vídeo.")
            return

        if not downloader.validate_url(url):
            messagebox.showerror(
                "URL inválida",
                "A URL informada não parece ser do YouTube.\n"
                "Verifique e tente novamente.",
            )
            return

        self._set_buttons_enabled(False)
        self._last_warning = None
        self.label_status.configure(text="⏳ Preparando...")
        self.progress_bar.set(0)
        self.progress_bar.configure(progress_color="#20262C")

        downloader.download(
            url=url,
            download_type=download_type,
            download_dir=self.download_dir,
            progress_hook=self._on_progress,
            on_success=lambda title: self.root.after(0, self._on_success, title),
            on_error=lambda err: self.root.after(0, self._on_error, err),
            on_retry=lambda attempt, max_attempts, delay, reason: self.root.after(
                0, self._on_retry, attempt, max_attempts, delay, reason
            ),
            on_warning=lambda msg: self.root.after(0, self._on_warning, msg),
            on_complete=lambda: self.root.after(0, self._on_complete),
        )

    def _on_progress(self, d):
        """Called from the download thread — schedules UI update on main thread."""
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
            downloaded = d.get("downloaded_bytes", 0)
            if total > 0:
                progress = int((downloaded / total) * 100)
                self.root.after(0, self._update_progress, progress)
        elif d["status"] == "finished":
            self.root.after(0, self._update_progress, 100, "✅ Finalizando download...")

    def _update_progress(self, value: int, text: str = None):
        """Thread-safe UI update via root.after()."""
        if value > 0:
            self.progress_bar.configure(progress_color="#1E7A5A")
        self.progress_bar.set(value / 100)
        if text:
            self.label_status.configure(text=text)
        else:
            self.label_status.configure(text=f"⬇️ Baixando... {value}%")

    def _on_success(self, title: str):
        if self._last_warning:
            self.label_status.configure(
                text=(
                    f"✅ Download concluído!\n📁 Salvo em: {self.download_dir}\n"
                    f"⚠️ {self._last_warning}"
                )
            )
        else:
            self.label_status.configure(
                text=f"✅ Download concluído!\n📁 Salvo em: {self.download_dir}"
            )
        messagebox.showinfo("Sucesso", f"Download de '{title}' concluído!")

    def _on_error(self, error_msg: str):
        messagebox.showerror("Erro", error_msg)
        self.label_status.configure(text="❌ Erro ao baixar.")
        self._last_warning = None

    def _on_retry(self, attempt: int, max_attempts: int, delay: int, reason: str):
        self.label_status.configure(
            text=(
                f"🔁 {reason}. Nova tentativa em {delay}s "
                f"({attempt}/{max_attempts})"
            )
        )

    def _on_warning(self, message: str):
        self._last_warning = message
        self.label_status.configure(text=f"⚠️ {message}")

    def _on_complete(self):
        self._set_buttons_enabled(True)
        self.progress_bar.set(0)
        self.progress_bar.configure(progress_color="#20262C")
        self._last_warning = None

    # ── Helpers ─────────────────────────────────────────────────────

    def _set_buttons_enabled(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        self.btn_video.configure(state=state)
        self.btn_audio.configure(state=state)

    # ── Run ─────────────────────────────────────────────────────────

    def run(self):
        self.root.mainloop()
