from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from app.config.settings import AppSettings


class SettingsWindow(QDialog):
    settings_saved = Signal()

    def __init__(self, settings: AppSettings, parent=None) -> None:  # type: ignore[no-untyped-def]
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("ERP Translator Settings")
        self.resize(540, 180)

        self.tesseract_path = QLineEdit(settings.tesseract_path)
        browse = QPushButton("Browse…")
        browse.clicked.connect(self.browse_tesseract)
        path_row = QHBoxLayout()
        path_row.addWidget(self.tesseract_path)
        path_row.addWidget(browse)

        self.language = QLineEdit(settings.ocr_language)
        self.translation_language = QComboBox()
        self.translation_language.addItem("Spanish", "es")
        self.translation_language.addItem("English", "en")
        self.translation_language.addItem("French", "fr")
        self.translation_language.addItem("Arabic", "ar")
        selected_language = self.translation_language.findData(settings.target_language)
        self.translation_language.setCurrentIndex(selected_language if selected_language >= 0 else 1)
        self.explain = QCheckBox("Explain ERP meaning")
        self.explain.setChecked(settings.explain_erp)
        self.automatic_hover = QCheckBox("Automatically translate text under the mouse")
        self.automatic_hover.setChecked(settings.automatic_hover)

        form = QFormLayout()
        form.addRow("Tesseract executable", path_row)
        form.addRow("OCR language", self.language)
        form.addRow("Translation language", self.translation_language)
        form.addRow("", self.explain)
        form.addRow("", self.automatic_hover)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def browse_tesseract(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select tesseract.exe",
            self.tesseract_path.text(),
            "Executable (tesseract.exe);;All files (*)",
        )
        if path:
            self.tesseract_path.setText(path)

    def save(self) -> None:
        self.settings.tesseract_path = self.tesseract_path.text().strip()
        self.settings.ocr_language = self.language.text().strip() or "spa"
        self.settings.target_language = str(self.translation_language.currentData())
        self.settings.explain_erp = self.explain.isChecked()
        self.settings.automatic_hover = self.automatic_hover.isChecked()
        self.settings.save()
        self.settings_saved.emit()
        self.accept()
