import logging
import sys


def _set_windows_app_id() -> None:
    """Group the taskbar icon under our own ID instead of python.exe/pythonw.exe."""
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("BrianAshihara.YTDownloader")
        except (AttributeError, OSError):
            pass


def main() -> None:
    _set_windows_app_id()
    from src.app import YTDownloaderApp

    try:
        YTDownloaderApp().run()
    except Exception as e:  # noqa: BLE001 - last-resort crash report
        logging.getLogger("YTDownloader").exception("Fatal error")
        try:
            from tkinter import messagebox

            from src.paths import log_dir

            messagebox.showerror(
                "YTDownloader",
                f"O aplicativo encontrou um erro e precisa fechar.\n\n{e}\n\nDetalhes em:\n{log_dir()}",
            )
        except Exception:  # noqa: BLE001
            pass
        raise


if __name__ == "__main__":
    main()
