from __future__ import annotations

import logging

from PIL import Image
from PySide6.QtCore import QObject, QPoint, QRunnable, Signal, Slot

from app.services.ocr_service import OCRService
from app.services.translation_service import TranslationService

LOGGER = logging.getLogger(__name__)


class HoverWorkerSignals(QObject):
    completed = Signal(object, QPoint, str)
    failed = Signal(str)


class HoverTranslationWorker(QRunnable):
    def __init__(
        self,
        image: Image.Image,
        pointer: QPoint,
        ocr_service: OCRService,
        translation_service: TranslationService,
        explain: bool,
    ) -> None:
        super().__init__()
        self.image = image
        self.pointer = pointer
        self.ocr_service = ocr_service
        self.translation_service = translation_service
        self.explain = explain
        self.signals = HoverWorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            text = self.ocr_service.extract_hover_line(self.image).strip()
            result = self.translation_service.translate(text, self.explain) if text else None
            self.signals.completed.emit(result, self.pointer, text)
        except Exception as exc:
            LOGGER.exception("Hover translation worker failed")
            self.signals.failed.emit(str(exc))
