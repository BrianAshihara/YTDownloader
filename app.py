import streamlit as st
import os
import yt_dlp
from pathlib import Path
import platform

# Detecta a pasta de Downloads do usuário de forma compatível
def get_downloads_folder():
    system = platform.system()
    if system == "Windows":
        return Path(os.path.join(os.environ["USERPROFILE"], "Downloads"))
    elif system in ("Linux", "Darwin"):  # Darwin = macOS
        return Path.home() / "Downloads"
    else:
        # fallback genérico
        return Path.cwd() / "Downloads"

DOWNLOAD_DIR = get_downloads_folder()
DOWNLOAD_DIR.mkdir(exist_ok=True)

# Configuração da página
st.set_page_config(
    page_title="YTDownloader",
    page_icon="🎥",
    layout="centered"
)

st.title("🎥 YTDownloader")
st.markdown("Baixe vídeos ou áudios do YouTube diretamente para sua pasta de Downloads!")

# Entrada de URL
url = st.text_input("Cole a URL do vídeo do YouTube aqui:", placeholder="https://www.youtube.com/watch?v=...")

# Botões de ação
col1, col2 = st.columns(2)
download_video = col1.button("🎬 Baixar Vídeo (MP4)")
download_audio = col2.button("🎧 Baixar Áudio (MP3)")

def baixar_midia(url, tipo):
    """Baixa vídeo ou áudio usando yt-dlp"""
    if not url:
        st.warning("Por favor, insira uma URL válida.")
        return None

    st.info("⏳ Preparando o download...")

    # Configurações de saída
    if tipo == "video":
        ydl_opts = {
            'outtmpl': str(DOWNLOAD_DIR / '%(title)s.%(ext)s'),
            'format': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
            'merge_output_format': 'mp4',
            'quiet': True
        }
    else:
        ydl_opts = {
            'outtmpl': str(DOWNLOAD_DIR / '%(title)s.%(ext)s'),
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True
        }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            nome_arquivo = ydl.prepare_filename(info)
            if tipo == "audio":
                nome_arquivo = os.path.splitext(nome_arquivo)[0] + ".mp3"

        return nome_arquivo

    except Exception as e:
        st.error(f"❌ Erro ao baixar: {e}")
        return None


# Lógica dos botões
if download_video and url:
    arquivo = baixar_midia(url, "video")
    if arquivo and os.path.exists(arquivo):
        st.success(f"✅ Download concluído! O arquivo foi salvo em:\n📂 {DOWNLOAD_DIR}")
        with open(arquivo, "rb") as f:
            st.download_button(
                label="📥 Baixar novamente (MP4)",
                data=f,
                file_name=os.path.basename(arquivo),
                mime="video/mp4"
            )

if download_audio and url:
    arquivo = baixar_midia(url, "audio")
    if arquivo and os.path.exists(arquivo):
        st.success(f"✅ Download concluído! O arquivo foi salvo em:\n📂 {DOWNLOAD_DIR}")
        with open(arquivo, "rb") as f:
            st.download_button(
                label="🎵 Baixar novamente (MP3)",
                data=f,
                file_name=os.path.basename(arquivo),
                mime="audio/mpeg"
            )

st.markdown("---")
st.caption("Desenvolvido por Brian Ashihara — versão prévia")
