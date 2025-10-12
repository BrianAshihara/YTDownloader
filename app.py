import streamlit as st
import yt_dlp
import os
from pathlib import Path

# Caminho para a pasta de downloads do usuário
DOWNLOAD_DIR = Path.home() / "Downloads"

# Configuração do Streamlit
st.set_page_config(page_title="YTDownloader", page_icon="🎬", layout="centered")

st.title("🎬 YTDownloader")
st.write("Baixe vídeos ou áudios do YouTube de forma simples e gratuita.")

# Campo de entrada da URL
url = st.text_input("Cole a URL do vídeo do YouTube aqui:")

# Botões de escolha
col1, col2 = st.columns(2)
with col1:
    baixar_video = st.button("📹 Baixar Vídeo (MP4)")
with col2:
    baixar_audio = st.button("🎧 Baixar Áudio (MP3)")

# Função principal de download
def baixar_conteudo(url, formato):
    try:
        st.info("⏳ Preparando download...")

        # Configuração base do yt-dlp
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "outtmpl": str(DOWNLOAD_DIR / "%(title)s.%(ext)s"),
            "extractor_args": {"youtube": {"player_client": ["android", "web"]}},  # Modo Android
        }

        if formato == "video":
            ydl_opts.update({
                "format": "bestvideo+bestaudio/best",
                "merge_output_format": "mp4",
            })
        elif formato == "audio":
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
            st.success(f"✅ Download concluído com sucesso!\n\n📁 Arquivo salvo em: {DOWNLOAD_DIR}")
            return titulo

    except Exception as e:
        st.error(f"❌ Erro ao baixar: {str(e)}")

# Ação dos botões
if baixar_video and url:
    baixar_conteudo(url, "video")

if baixar_audio and url:
    baixar_conteudo(url, "audio")

st.markdown("---")
st.caption("Desenvolvido por Brian Ashihara — Projeto YTDownloader 🎬")
