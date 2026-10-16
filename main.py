from __future__ import annotations

import ctypes
import logging
import sys

from PySide6.QtWidgets import QApplication

from app.config.settings import AppSettings
from app.gui.main_window import MainWindow


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def enable_windows_dpi_awareness() -> None:
    """Keep Qt selection coordinates aligned with physical screenshot pixels."""
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            logging.getLogger(__name__).warning("Could not enable Windows DPI awareness")


def main() -> int:
    configure_logging()
    enable_windows_dpi_awareness()
    app = QApplication(sys.argv)
    app.setApplicationName("ERP Translator")
    app.setOrganizationName("ERP Translator")
    app.setQuitOnLastWindowClosed(False)

    settings = AppSettings.load()
    window = MainWindow(settings)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
