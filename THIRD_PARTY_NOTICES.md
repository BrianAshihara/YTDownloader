# Third-party software

The YTDownloader installer bundles the following software. Each component
remains under its own license.

| Component | License | Source |
|-----------|---------|--------|
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | Unlicense | https://github.com/yt-dlp/yt-dlp |
| [yt-dlp-ejs](https://github.com/yt-dlp/ejs) | Unlicense / MIT | https://github.com/yt-dlp/ejs |
| [customtkinter](https://github.com/TomSchimansky/CustomTkinter) | MIT | https://github.com/TomSchimansky/CustomTkinter |
| [Pillow](https://python-pillow.org) | MIT-CMU | https://github.com/python-pillow/Pillow |
| [Python](https://www.python.org) | PSF License | https://www.python.org |
| [FFmpeg](https://ffmpeg.org) (essentials build by gyan.dev) | **GPL v3** | https://ffmpeg.org/download.html · https://www.gyan.dev/ffmpeg/builds/ |
| [Deno](https://deno.com) | MIT | https://github.com/denoland/deno |

## FFmpeg

`ffmpeg.exe` and `ffprobe.exe` are unmodified binaries from the gyan.dev
"release essentials" build, licensed under the GNU GPL version 3. They are
separate programs invoked as external processes. Their license text and build
information are installed in `_internal\bin\licenses\`. The corresponding
source code is available from https://ffmpeg.org and from the build page
linked above.
