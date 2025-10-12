# 🎬 YTDownloader

[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![yt-dlp](https://img.shields.io/badge/yt--dlp-v2025.10.12-orange)](https://github.com/yt-dlp/yt-dlp)

**YTDownloader** é uma aplicação desktop desenvolvida em **Python** que permite baixar vídeos e áudios do YouTube com alta qualidade diretamente para a pasta de downloads do usuário.  
Ideal para quem deseja uma interface simples, funcional e moderna para gerenciar downloads de mídia.

---

## 🛠️ Funcionalidades

- Baixar vídeos em **MP4** na melhor qualidade disponível (até 1080p).  
- Baixar apenas o áudio em **MP3** (192 kbps).  
- Barra de progresso em tempo real durante o download.  
- Mensagens de status: preparação, progresso e conclusão do download.  
- Interface moderna com tema escuro, utilizando **Tkinter**.  
- Salva os arquivos automaticamente na pasta padrão de **Downloads**.  
- Multithreading para manter a interface responsiva durante downloads.  

---

## 🖥️ Tecnologias utilizadas

| Tecnologia | Função |
|------------|--------|
| Python 3 | Linguagem principal do projeto |
| Tkinter | Interface gráfica desktop leve e nativa |
| yt-dlp | Biblioteca de download do YouTube |
| threading | Mantém a interface responsiva durante o download |
| pathlib | Manipulação de caminhos de arquivos de forma cross-platform |
| FFmpeg | Mescla vídeo e áudio quando necessário |

---

## 📦 Pré-requisitos

1. **Python 3.10+** instalado.  
2. Biblioteca **yt-dlp**:
   ```bash
   pip install yt-dlp
3. **FFmpeg** instalado e acessível via PATH (ou embutido no executável).  

> Para Windows, você pode baixar FFmpeg aqui: [https://www.gyan.dev/ffmpeg/builds/](https://www.gyan.dev/ffmpeg/builds/)

---

## ⚡ Instalação e execução

1. Clone ou baixe o projeto:  
   ```bash
   git clone https://github.com/seu-usuario/YTDownloader.git
   cd YTDownloader
2. Instale as dependências necessárias:

   pip install yt-dlp
3. Execute o aplicativo:

   python main.py


## 🎨 Uso

1. Abra o YTDownloader.
2. Cole a URL do vídeo do YouTube no campo de texto.
3. Clique em “Baixar Vídeo (MP4)” para vídeo completo ou “Baixar Áudio (MP3)” para áudio apenas.
4. Acompanhe o progresso pelo indicador de barra.
5. Ao finalizar, uma mensagem informará que o download foi concluído.