# 🎬 YTDownloader

[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![yt-dlp](https://img.shields.io/badge/yt--dlp-latest-orange)](https://github.com/yt-dlp/yt-dlp)

**YTDownloader** é uma aplicação desktop desenvolvida em **Python** que permite baixar vídeos e áudios do YouTube com alta qualidade diretamente para a pasta de downloads do usuário.
Ideal para quem deseja uma interface simples, funcional e moderna para gerenciar downloads de mídia.

---

## 🛠️ Funcionalidades

- Baixar vídeos em **MP4** na melhor qualidade disponível (até 1080p)
- Baixar apenas o áudio em **MP3** (192 kbps)
- Barra de progresso em tempo real durante o download
- Validação de URL do YouTube antes de iniciar
- Interface moderna com tema escuro, utilizando **Tkinter**
- Salva os arquivos automaticamente na pasta padrão de **Downloads**
- Multithreading para manter a interface responsiva durante downloads

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

## 📁 Estrutura do projeto

```
YTDownloader/
├── main.py              # Ponto de entrada da aplicação
├── src/
│   ├── __init__.py
│   ├── app.py           # Interface gráfica (classe YTDownloaderApp)
│   ├── downloader.py    # Lógica de download (yt-dlp)
│   └── constants.py     # Constantes e configurações
├── requirements.txt     # Dependências do projeto
├── YTDownloader.spec    # Configuração do PyInstaller
├── YTD.ico              # Ícone da aplicação
└── README.md
```

---

## 📦 Pré-requisitos

1. **Python 3.10+** instalado
2. **FFmpeg** instalado e acessível via PATH (ou embutido no executável)

> Para Windows, você pode baixar FFmpeg aqui: [https://www.gyan.dev/ffmpeg/builds/](https://www.gyan.dev/ffmpeg/builds/)

---

## ⚡ Instalação e execução

1. Clone o projeto:
   ```bash
   git clone https://github.com/BrianAshihara/YTDownloader.git
   cd YTDownloader
   ```

2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

3. Execute o aplicativo:
   ```bash
   python main.py
   ```

> 💡 Ou baixe diretamente o executável `.exe` na aba [Releases](https://github.com/BrianAshihara/YTDownloader/releases).

---

## 🎨 Uso

1. Abra o YTDownloader
2. Cole a URL do vídeo do YouTube no campo de texto
3. Clique em **"Baixar Vídeo (MP4)"** para vídeo completo ou **"Baixar Áudio (MP3)"** para áudio apenas
4. Acompanhe o progresso pelo indicador de barra
5. Ao finalizar, uma mensagem informará que o download foi concluído

---

## 🏗️ Build (gerar executável)

Para gerar o `.exe` com PyInstaller:

1. Baixe o **FFmpeg** em [gyan.dev](https://www.gyan.dev/ffmpeg/builds/)
2. Extraia o arquivo `ffmpeg.exe` da pasta `bin/` do download
3. Cole o arquivo `ffmpeg.exe` na pasta raiz do projeto (junto ao `main.py`)
4. Instale o PyInstaller e gere o executável:

```bash
pip install pyinstaller
pyinstaller YTDownloader.spec
```

O executável completo será gerado na pasta `dist/YTDownloader.exe`, já com o FFmpeg embutido (necessário para baixar vídeos em 1080p+ e conversão de áudio).

---

## 📝 Licença

Este projeto está licenciado sob a licença MIT — veja o arquivo [LICENSE](LICENSE) para detalhes.

---

Desenvolvido por **Brian Ashihara** — Projeto YTDownloader