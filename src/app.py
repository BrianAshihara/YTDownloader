import tkinter as tk
from tkinter import ttk, messagebox

from src.constants import APP_NAME, DOWNLOAD_DIR
from src import downloader


class YTDownloaderApp:
    """Main application window for YTDownloader."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"🎬 {APP_NAME}")
        self.root.geometry("500x340")
        self.root.resizable(False, False)
        self.root.configure(bg="#1e1e1e")

        self.download_dir = DOWNLOAD_DIR
        self._setup_styles()
        self._build_ui()

    # ── Styling ──────────────────────────────────────────────

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=6)

    # ── UI Construction ──────────────────────────────────────

    def _build_ui(self):
        # Title
        tk.Label(
            self.root,
            text=f"🎬 {APP_NAME}",
            font=("Segoe UI", 20, "bold"),
            fg="white",
            bg="#1e1e1e",
        ).pack(pady=(20, 5))

        # Subtitle
        tk.Label(
            self.root,
            text="Baixe vídeos ou áudios do YouTube com alta qualidade.",
            fg="#ccc",
            bg="#1e1e1e",
            font=("Segoe UI", 10),
        ).pack(pady=(0, 15))

        # URL entry
        self.entry_url = ttk.Entry(self.root, width=55)
        self.entry_url.pack(pady=5)

        # Buttons
        frame_btns = tk.Frame(self.root, bg="#1e1e1e")
        frame_btns.pack(pady=10)

        self.btn_video = ttk.Button(
            frame_btns,
            text="📹 Baixar Vídeo (MP4)",
            command=lambda: self._start_download("video"),
        )
        self.btn_video.grid(row=0, column=0, padx=10)

        self.btn_audio = ttk.Button(
            frame_btns,
            text="🎧 Baixar Áudio (MP3)",
            command=lambda: self._start_download("audio"),
        )
        self.btn_audio.grid(row=0, column=1, padx=10)

        # Progress bar
        self.progress_bar = ttk.Progressbar(
            self.root, orient="horizontal", length=400, mode="determinate"
        )
        self.progress_bar.pack(pady=(10, 5))

        # Status label
        self.label_status = tk.Label(
            self.root, text="", fg="#bbb", bg="#1e1e1e", font=("Segoe UI", 9)
        )
        self.label_status.pack(pady=10)

        # Footer
        tk.Label(
            self.root,
            text="Desenvolvido por Brian — Projeto YTDownloader",
            fg="#666",
            bg="#1e1e1e",
            font=("Segoe UI", 8),
        ).pack(side="bottom", pady=10)

    # ── Download Logic ───────────────────────────────────────

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
        self.label_status.config(text="⏳ Preparando...")
        self.progress_bar["value"] = 0

        downloader.download(
            url=url,
            download_type=download_type,
            download_dir=self.download_dir,
            progress_hook=self._on_progress,
            on_success=lambda title: self.root.after(0, self._on_success, title),
            on_error=lambda err: self.root.after(0, self._on_error, err),
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
        self.progress_bar["value"] = value
        if text:
            self.label_status.config(text=text)
        else:
            self.label_status.config(text=f"⬇️ Baixando... {value}%")

    def _on_success(self, title: str):
        self.label_status.config(
            text=f"✅ Download concluído!\n📁 Salvo em: {self.download_dir}"
        )
        messagebox.showinfo("Sucesso", f"Download de '{title}' concluído!")

    def _on_error(self, error_msg: str):
        messagebox.showerror("Erro", error_msg)
        self.label_status.config(text="❌ Erro ao baixar.")

    def _on_complete(self):
        self._set_buttons_enabled(True)
        self.progress_bar["value"] = 0

    # ── Helpers ──────────────────────────────────────────────

    def _set_buttons_enabled(self, enabled: bool):
        state = tk.NORMAL if enabled else tk.DISABLED
        self.btn_video.config(state=state)
        self.btn_audio.config(state=state)

    # ── Run ──────────────────────────────────────────────────

    def run(self):
        self.root.mainloop()
