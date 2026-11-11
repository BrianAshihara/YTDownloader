# 🎬 YTDownloader

[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![yt-dlp](https://img.shields.io/badge/yt--dlp-latest-orange)](https://github.com/yt-dlp/yt-dlp)
[![CI](https://github.com/BrianAshihara/YTDownloader/actions/workflows/ci.yml/badge.svg)](https://github.com/BrianAshihara/YTDownloader/actions/workflows/ci.yml)

**YTDownloader** é um app desktop para Windows, feito em **Python**, que baixa vídeos e músicas do YouTube por uma interface simples e leve.

---

## ⬇️ Instalação (usuários)

1. Baixe o `YTDownloader-Setup-x.y.z.exe` na página de [Releases](https://github.com/BrianAshihara/YTDownloader/releases/latest).
2. Execute o instalador. Ele não pede permissão de administrador e instala só para o seu usuário.
3. Abra o **YTDownloader** pelo Menu Iniciar.

> O instalador não é assinado digitalmente, então o Windows pode exibir "O Windows protegeu o computador".
> Clique em **Mais informações → Executar assim mesmo**. Para conferir a integridade do arquivo, compare o hash com o `SHA256SUMS.txt` da release (veja [Transparência dos binários](#-transparência-dos-binários)).

Também existe uma versão **portátil** (`.zip`), que roda sem instalar.

---

## 🛠️ Funcionalidades

- **Prévia do vídeo** (capa, título, canal e duração) assim que o link é colado
- **Vídeo MP4** em até 4K, ou limitado a 1080p, 720p, 480p ou 360p. Em resoluções iguais, prefere H.264/AAC, que roda em qualquer player
- **Áudio** em MP3 (128, 192 ou 320 kbps) ou M4A original, sem perda de qualidade
- Capa e metadados embutidos no arquivo
- Progresso real em etapas (vídeo -> áudio -> processamento) com velocidade e tempo restante
- **Cancelamento** a qualquer momento, com limpeza dos arquivos parciais
- Escolha da pasta de destino e preferências salvas
- Retentativas automáticas em falhas de rede
- Link de playlist (`watch?v=…&list=…`) baixa apenas o vídeo selecionado
- Logs em `%LOCALAPPDATA%\YTDownloader\logs`, acessíveis pelo botão "Abrir logs"

---

## 🧰 Tecnologias

| Tecnologia | Função |
|-----------|--------|
| Python 3.10+ | Linguagem principal |
| customtkinter | Interface |
| yt-dlp + yt-dlp-ejs | Extração e download do YouTube |
| Deno | Runtime JavaScript exigido pelo yt-dlp para o YouTube |
| FFmpeg / FFprobe | Junção, conversão e metadados |
| PyInstaller + Inno Setup | Executável e instalador |
| GitHub Actions | Testes, build e release automatizados |

---

## 📁 Estrutura do projeto

```
YTDownloader/
├── main.py                    # ponto de entrada
├── src/
│   ├── app.py                 # interface (thread principal do Tk)
│   ├── downloader.py          # núcleo: jobs, eventos, yt-dlp
│   ├── settings.py            # preferências (%APPDATA%\YTDownloader)
│   ├── paths.py               # localização de recursos e binários
│   ├── log.py                 # logging em arquivo
│   ├── theme.py               # cores e medidas da UI
│   ├── ui_format.py           # formatação (bytes, tempo…)
│   └── constants.py           # versão e opções de qualidade
├── assets/icon.ico           # ícone do app e do instalador
├── tests/
├── scripts/fetch_binaries.ps1 # baixa FFmpeg e Deno para bin/
├── installer/YTDownloader.iss # instalador (Inno Setup)
├── YTDownloader.spec          # build do PyInstaller
└── .github/workflows/         # CI e release
```

---

## 💻 Desenvolvimento

Pré-requisitos: **Python 3.10+**, além do **FFmpeg** e do **Deno** no PATH ou na pasta `bin/`.

```powershell
python -m pip install -r requirements.txt
powershell -ExecutionPolicy Bypass -File scripts\fetch_binaries.ps1   # baixa ffmpeg/ffprobe/deno em bin\
python main.py
```

> Sem o Deno, o YouTube só entrega formatos de baixa qualidade, e o app avisa sobre isso.

### Testes

```powershell
python -m unittest -v
```

---

## 🏗️ Build local

```powershell
python -m pip install -r requirements-dev.txt
powershell -ExecutionPolicy Bypass -File scripts\fetch_binaries.ps1
python -m PyInstaller --clean --noconfirm YTDownloader.spec       # → dist\YTDownloader\
iscc /DAppVersion=2.0.1 installer\YTDownloader.iss                # → dist\installer\ (requer Inno Setup 6)
```

## 🚀 Release

1. Atualize `APP_VERSION` em `src/constants.py`.
2. Crie e envie a tag correspondente: `git tag v2.0.1 && git push origin v2.0.1`.
3. O GitHub Actions roda os testes, compila, gera o instalador e o `.zip` portátil, calcula os SHA-256 e cria uma **release rascunho**. Revise e publique.

---

## 🔏 Transparência dos binários

- Os binários publicados (instalador e `.zip` portátil) são gerados **exclusivamente pelo GitHub Actions** a partir deste repositório ([`release.yml`](.github/workflows/release.yml)). Nenhum binário é compilado manualmente.
- Cada release traz um `SHA256SUMS.txt` e uma [atestação de proveniência](https://docs.github.com/actions/security-for-github-actions/using-artifact-attestations) do GitHub. Para conferir a origem de um arquivo, use `gh attestation verify <arquivo> -R BrianAshihara/YTDownloader`.
- `ffmpeg.exe` e `deno.exe` são distribuídos sem modificação, como seus autores os publicam.
- **Privacidade:** o YTDownloader não coleta nem envia dados. Ele só se conecta à internet para buscar o vídeo que o usuário pede, no YouTube, e as configurações e logs ficam apenas no computador do usuário.

---

## ⚖️ Aviso

Use apenas para conteúdo que você tem direito de baixar e respeite os Termos de Serviço do YouTube.

## 📝 Licença

MIT. Veja [LICENSE](LICENSE). Componentes de terceiros estão listados em [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

---

Desenvolvido por **Brian Ashihara**
