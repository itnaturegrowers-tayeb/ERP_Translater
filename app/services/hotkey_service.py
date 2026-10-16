from __future__ import annotations

import logging

from pynput import keyboard
from PySide6.QtCore import QObject, Signal

LOGGER = logging.getLogger(__name__)


class HotkeyService(QObject):
    activated = Signal()
    error = Signal(str)

    def __init__(self, hotkey: str = "<ctrl>+<shift>+t") -> None:
        super().__init__()
        self.hotkey = hotkey
        self._listener: keyboard.GlobalHotKeys | None = None

    def start(self) -> None:
        try:
            self._listener = keyboard.GlobalHotKeys({self.hotkey: self.activated.emit})
            self._listener.start()
            LOGGER.info("Registered global hotkey %s", self.hotkey)
        except Exception as exc:
            LOGGER.exception("Could not register global hotkey")
            self.error.emit(str(exc))

    def stop(self) -> None:
        if self._listener:
            self._listener.stop()
            self._listener = None
