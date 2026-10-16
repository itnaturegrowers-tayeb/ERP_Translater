from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QKeyEvent, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import QApplication, QWidget


class CaptureOverlay(QWidget):
    area_selected = Signal(QRect)
    cancelled = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._start: QPoint | None = None
        self._current: QPoint | None = None
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setCursor(Qt.CrossCursor)

    def begin(self) -> None:
        screens = QApplication.screens()
        geometry = screens[0].geometry()
        for screen in screens[1:]:
            geometry = geometry.united(screen.geometry())
        self.setGeometry(geometry)
        self._start = None
        self._current = None
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus(Qt.ActiveWindowFocusReason)

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 115))
        selection = self.selection_rect()
        if not selection.isNull():
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.fillRect(selection, Qt.transparent)
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            painter.setPen(QPen(QColor("#4da3ff"), 2))
            painter.drawRect(selection)
        painter.setPen(Qt.white)
        painter.drawText(20, 35, "Drag to select ERP text  •  Esc to cancel")

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self._start = event.position().toPoint()
            self._current = self._start
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._start is not None:
            self._current = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.LeftButton or self._start is None:
            return
        self._current = event.position().toPoint()
        rectangle = self.selection_rect()
        if rectangle.width() >= 5 and rectangle.height() >= 5:
            global_rectangle = QRect(self.mapToGlobal(rectangle.topLeft()), rectangle.size())
            self.hide()
            self.area_selected.emit(global_rectangle)
        else:
            self._start = None
            self._current = None
            self.update()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_Escape:
            self.hide()
            self.cancelled.emit()
        else:
            super().keyPressEvent(event)

    def selection_rect(self) -> QRect:
        if self._start is None or self._current is None:
            return QRect()
        return QRect(self._start, self._current).normalized()
