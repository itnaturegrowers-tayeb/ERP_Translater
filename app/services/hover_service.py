from __future__ import annotations

from PySide6.QtCore import QObject, QPoint, QTimer, Signal
from PySide6.QtGui import QCursor


class HoverService(QObject):
    """Detect when the global mouse pointer has remained still long enough."""

    hover_requested = Signal(QPoint)
    pointer_moved = Signal()

    def __init__(self, delay_ms: int = 1000, interval_ms: int = 200) -> None:
        super().__init__()
        self.delay_ms = delay_ms
        self.interval_ms = interval_ms
        self._last_position: QPoint | None = None
        self._stable_ms = 0
        self._emitted = False
        self._timer = QTimer(self)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self._sample_pointer)

    def start(self) -> None:
        self._last_position = QCursor.pos()
        self._stable_ms = 0
        self._emitted = False
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()
        self._stable_ms = 0
        self._emitted = False

    def _sample_pointer(self) -> None:
        position = QCursor.pos()
        if self._last_position is None or self._distance(position, self._last_position) > 2:
            self._last_position = position
            self._stable_ms = 0
            self._emitted = False
            self.pointer_moved.emit()
            return

        self._stable_ms += self.interval_ms
        if self._stable_ms >= self.delay_ms and not self._emitted:
            self._emitted = True
            self.hover_requested.emit(position)

    @staticmethod
    def _distance(first: QPoint, second: QPoint) -> int:
        return abs(first.x() - second.x()) + abs(first.y() - second.y())
