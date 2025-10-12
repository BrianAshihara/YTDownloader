import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import threading
import yt_dlp

# Caminho padrão de download (pasta de Downloads do usuário)
DOWNLOAD_DIR = Path.home() / "Downloads"

# Função chamada a cada atualização do download
def hook_progresso(d):
    if d['status'] == 'downloading':
        total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
        baixado = d.get('downloaded_bytes', 0)
        if total > 0:
            progresso = int((baixado / total) * 100)
            progress_bar["value"] = progresso
            label_status.config(text=f"⬇️ Baixando... {progresso}%")
            root.update_idletasks()
    elif d['status'] == 'finished':
        progress_bar["value"] = 100
        label_status.config(text="✅ Finalizando download...")

# Função principal de download
def baixar_conteudo():
    url = entry_url.get().strip()
    tipo = tipo_var.get()

    if not url:
        messagebox.showerror("Erro", "Por favor, insira a URL do vídeo.")
        return

    btn_video.config(state=tk.DISABLED)
    btn_audio.config(state=tk.DISABLED)
    label_status.config(text="⏳ Preparando...")
    progress_bar["value"] = 0

    def tarefa():
        try:
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "progress_hooks": [hook_progresso],
                "outtmpl": str(DOWNLOAD_DIR / "%(title)s.%(ext)s"),
                "extractor_args": {"youtube": {"player_client": ["android", "web"]}},
            }

            if tipo == "video":
                # Melhor qualidade de vídeo e áudio
                ydl_opts.update({
                    "format": "bestvideo[height<=1080]+bestaudio/best",
                    "merge_output_format": "mp4",
                    "postprocessors": [{
                        "key": "FFmpegVideoConvertor",
                        "preferedformat": "mp4"
                    }],
                })
            else:
                # Apenas áudio MP3 de alta qualidade
                ydl_opts.update({
                    "format": "bestaudio/best",
                    "postprocessors": [{
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }],
                })

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                titulo = info.get("title", "vídeo")

            label_status.config(text=f"✅ Download concluído!\n📁 Salvo em: {DOWNLOAD_DIR}")
            messagebox.showinfo("Sucesso", f"Download de '{titulo}' concluído!")
        except Exception as e:
            messagebox.showerror("Erro", f"Ocorreu um erro:\n{str(e)}")
            label_status.config(text="❌ Erro ao baixar.")
        finally:
            btn_video.config(state=tk.NORMAL)
            btn_audio.config(state=tk.NORMAL)
            progress_bar["value"] = 0

    threading.Thread(target=tarefa, daemon=True).start()


# ===== INTERFACE GRÁFICA =====
root = tk.Tk()
root.title("🎬 YTDownloader")
root.geometry("500x340")
root.resizable(False, False)
root.configure(bg="#1e1e1e")

style = ttk.Style()
style.theme_use("clam")
style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=6)

# Título
label_title = tk.Label(root, text="🎬 YTDownloader", font=("Segoe UI", 20, "bold"), fg="white", bg="#1e1e1e")
label_title.pack(pady=(20, 5))

label_sub = tk.Label(root, text="Baixe vídeos ou áudios do YouTube com alta qualidade.", fg="#ccc", bg="#1e1e1e", font=("Segoe UI", 10))
label_sub.pack(pady=(0, 15))

# Campo URL
entry_url = ttk.Entry(root, width=55)
entry_url.pack(pady=5)

# Frame de botões
frame_btns = tk.Frame(root, bg="#1e1e1e")
frame_btns.pack(pady=10)

tipo_var = tk.StringVar(value="video")

btn_video = ttk.Button(frame_btns, text="📹 Baixar Vídeo (MP4)", command=lambda: [tipo_var.set("video"), baixar_conteudo()])
btn_video.grid(row=0, column=0, padx=10)

btn_audio = ttk.Button(frame_btns, text="🎧 Baixar Áudio (MP3)", command=lambda: [tipo_var.set("audio"), baixar_conteudo()])
btn_audio.grid(row=0, column=1, padx=10)

# Barra de progresso
progress_bar = ttk.Progressbar(root, orient="horizontal", length=400, mode="determinate")
progress_bar.pack(pady=(10, 5))

# Status
label_status = tk.Label(root, text="", fg="#bbb", bg="#1e1e1e", font=("Segoe UI", 9))
label_status.pack(pady=10)

# Rodapé
footer = tk.Label(root, text="Desenvolvido por Brian — Projeto YTDownloader", fg="#666", bg="#1e1e1e", font=("Segoe UI", 8))
footer.pack(side="bottom", pady=10)

root.mainloop()
