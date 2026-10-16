from __future__ import annotations

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from app.models.translation_result import TranslationResult


class HoverPopup(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.Tool
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setObjectName("hoverPopup")
        self.setStyleSheet(
            "#hoverPopup { background: #202124; border: 1px solid #5f6368; "
            "border-radius: 7px; }"
            "QLabel { color: #f1f3f4; }"
            "QLabel#source { color: #bdc1c6; font-size: 10px; }"
            "QLabel#translation { font-size: 13px; font-weight: 600; }"
            "QLabel#explanation { color: #c7d8ff; font-size: 10px; }"
        )
        self.setMaximumWidth(480)

        self.source = QLabel()
        self.source.setObjectName("source")
        self.source.setWordWrap(True)
        self.translation = QLabel()
        self.translation.setObjectName("translation")
        self.translation.setWordWrap(True)
        self.explanation = QLabel()
        self.explanation.setObjectName("explanation")
        self.explanation.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 9, 12, 9)
        layout.setSpacing(4)
        layout.addWidget(self.source)
        layout.addWidget(self.translation)
        layout.addWidget(self.explanation)

    def show_result(self, result: TranslationResult, pointer: QPoint) -> None:
        self.source.setText(result.corrected_original or result.original)
        self.translation.setText(result.translated)
        self.explanation.setText(result.explanation)
        self.explanation.setVisible(bool(result.explanation))
        self.adjustSize()

        screen = QGuiApplication.screenAt(pointer) or QGuiApplication.primaryScreen()
        available = screen.availableGeometry()
        x = min(pointer.x() + 18, available.right() - self.width())
        y = min(pointer.y() + 24, available.bottom() - self.height())
        if x < available.left():
            x = available.left()
        if y < available.top():
            y = available.top()
        self.move(x, y)
        self.show()
        self.raise_()

    def show_status(self, text: str, pointer: QPoint) -> None:
        self.source.setText("")
        self.translation.setText(text)
        self.explanation.hide()
        self.adjustSize()
        screen = QGuiApplication.screenAt(pointer) or QGuiApplication.primaryScreen()
        available = screen.availableGeometry()
        self.move(
            min(pointer.x() + 18, available.right() - self.width()),
            min(pointer.y() + 24, available.bottom() - self.height()),
        )
        self.show()
