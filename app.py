import streamlit as st
import yt_dlp
from pathlib import Path
import os
import sys

# ==============================================
# 🚀 YTDownloader — versão MVP 1.1
# ==============================================

st.set_page_config(
    page_title="YTDownloader",
    page_icon="🎥",
    layout="centered"
)

st.title("🎥 YTDownloader")
st.markdown("Baixe vídeos ou áudios do YouTube diretamente para sua pasta **Downloads**.")

# ==============================================
# 📂 Define a pasta de destino (Downloads)
# ==============================================
if sys.platform.startswith("win"):
    download_path = Path(os.path.join(os.path.expanduser("~"), "Downloads"))
else:
    download_path = Path.home() / "Downloads"

# ==============================================
# 📥 Entrada de URL
# ==============================================
url = st.text_input("Cole a URL do vídeo do YouTube aqui:")

# Placeholder para mensagens dinâmicas
status_placeholder = st.empty()

# ==============================================
# ⚙️ Função de Download
# ==============================================
def baixar_video(url: str, somente_audio=False):
    try:
        # Define as opções básicas
        if somente_audio:
            formato = {
                "format": "bestaudio/best",
                "outtmpl": str(download_path / "%(title)s.%(ext)s"),
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
                "quiet": True,
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "extractor_args": {"youtube": {"player_client": ["android"]}},
            }
        else:
            formato = {
                "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4",
                "outtmpl": str(download_path / "%(title)s.%(ext)s"),
                "merge_output_format": "mp4",
                "quiet": True,
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "extractor_args": {"youtube": {"player_client": ["android"]}},
            }

        status_placeholder.info("⏳ Preparando o download...")

        with yt_dlp.YoutubeDL(formato) as ydl:
            ydl.download([url])

        status_placeholder.empty()
        st.success(f"✅ Download concluído!\n\n📂 Arquivo salvo em: `{download_path}`")

    except Exception as e:
        status_placeholder.empty()
        st.error(f"❌ Erro ao baixar: {e}")

# ==============================================
# 🎬 Botões de ação
# ==============================================
col1, col2 = st.columns(2)

with col1:
    if st.button("🎬 Baixar Vídeo (MP4)"):
        if url.strip():
            baixar_video(url, somente_audio=False)
        else:
            st.warning("Por favor, insira uma URL válida.")

with col2:
    if st.button("🎧 Baixar Áudio (MP3)"):
        if url.strip():
            baixar_video(url, somente_audio=True)
        else:
            st.warning("Por favor, insira uma URL válida.")

# Rodapé
st.markdown("---")
st.caption("Desenvolvido por Brian Ashihara • Versão Prévia 1.2")
