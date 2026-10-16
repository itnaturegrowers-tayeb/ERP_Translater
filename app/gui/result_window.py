from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.models.translation_result import TranslationResult


class ResultWindow(QWidget):
    position_changed = Signal(int, int)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ERP Translator — Result")
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        self.resize(520, 560)
        self._result = TranslationResult("", "")

        self.original = QTextEdit(readOnly=True)
        self.translation = QTextEdit(readOnly=True)
        self.explanation_label = QLabel("ERP explanation")
        self.explanation = QTextEdit(readOnly=True)
        self.explanation.setMaximumHeight(110)

        self.translation_label = QLabel("English translation")
        self.copy_translation = QPushButton("Copy English")
        copy_all = QPushButton("Copy All")
        close = QPushButton("Close")
        self.copy_translation.clicked.connect(self.copy_english)
        copy_all.clicked.connect(self.copy_all)
        close.clicked.connect(self.close)

        buttons = QHBoxLayout()
        buttons.addWidget(self.copy_translation)
        buttons.addWidget(copy_all)
        buttons.addStretch()
        buttons.addWidget(close)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Original Spanish / OCR text"))
        layout.addWidget(self.original)
        layout.addWidget(self.translation_label)
        layout.addWidget(self.translation)
        layout.addWidget(self.explanation_label)
        layout.addWidget(self.explanation)
        layout.addLayout(buttons)

    def show_result(self, result: TranslationResult) -> None:
        self._result = result
        self.original.setPlainText(result.original)
        self.translation.setPlainText(result.translated)
        self.translation_label.setText(f"{result.target_language} translation")
        self.copy_translation.setText(f"Copy {result.target_language}")
        visible = bool(result.explanation)
        self.explanation_label.setVisible(visible)
        self.explanation.setVisible(visible)
        self.explanation.setPlainText(result.explanation)
        self.show()
        self.raise_()

    def copy_english(self) -> None:
        QGuiApplication.clipboard().setText(self._result.translated)

    def copy_all(self) -> None:
        parts = [
            "Original:\n" + self._result.original,
            "English:\n" + self._result.translated,
        ]
        if self._result.explanation:
            parts.append("ERP explanation:\n" + self._result.explanation)
        QGuiApplication.clipboard().setText("\n\n".join(parts))

    def moveEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        super().moveEvent(event)
        self.position_changed.emit(self.x(), self.y())
