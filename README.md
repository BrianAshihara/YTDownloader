# 🎬 YTDownloader

[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![yt-dlp](https://img.shields.io/badge/yt--dlp-latest-orange)](https://github.com/yt-dlp/yt-dlp)

**YTDownloader** é um app desktop em **Python** para baixar vídeos e áudios do YouTube com uma interface moderna, simples e rápida.

---

## 🛠️ Funcionalidades

- Download em **MP4** priorizando **H.264/AAC** (mais compatível e leve)
- Download de **MP3** em 192 kbps
- Metadados e thumbnail embutidos (best‑effort no MP4)
- Retentativas automáticas com backoff em falhas transitórias
- Barra de progresso em tempo real
- Validação de URL antes de iniciar
- Interface moderna com **customtkinter** (tema escuro)
- Salva direto na pasta **Downloads**

---

## 🧰 Tecnologias

| Tecnologia | Função |
|-----------|--------|
| Python 3 | Linguagem principal |
| customtkinter | UI moderna e responsiva |
| yt-dlp | Download do YouTube |
| FFmpeg/FFprobe | Merge e pós‑processamento |
| threading | UI não bloqueante |
| pathlib | Caminhos cross‑platform |

---

## 📁 Estrutura do projeto

```
YTDownloader/
├── main.py
├── src/
│   ├── __init__.py
│   ├── app.py
│   ├── downloader.py
│   └── constants.py
├── tests/
│   └── test_downloader.py
├── requirements.txt
├── YTDownloader.spec
├── YTD.ico
└── README.md
```

---

## 📦 Pré‑requisitos

1. **Python 3.10+**
2. **FFmpeg + FFprobe** no PATH (ou embutidos no executável)

> Windows: baixe em https://www.gyan.dev/ffmpeg/builds/

---

## ⚡ Instalação e execução

```bash
python -m pip install -r requirements.txt
python main.py
```

---

## 🎨 Uso

1. Cole a URL do YouTube
2. Clique em **Baixar Vídeo (MP4)** ou **Baixar Áudio (MP3)**
3. Acompanhe o progresso

---

## ✅ Testes

```bash
python -m unittest -v
```

---

## 🏗️ Build (gerar executável)

1. Baixe o **FFmpeg** e tenha `ffmpeg.exe` e `ffprobe.exe` em um destes locais:
   - Raiz do projeto (mesma pasta do `main.py`)
   - `C:\ffmpeg\bin` (se já estiver instalado no sistema)
2. Instale o PyInstaller e gere o executável:

```bash
python -m pip install pyinstaller
python -m PyInstaller --clean YTDownloader.spec
```

O executável será gerado em `dist/YTDownloader.exe`.

---

## 📝 Licença

MIT — veja o arquivo [LICENSE](LICENSE).

---

Desenvolvido por **Brian Ashihara** — Projeto YTDownloader