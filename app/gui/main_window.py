from __future__ import annotations

import logging

from PIL import Image
from PySide6.QtCore import QPoint, QRect, QThreadPool, QTimer, Qt
from PySide6.QtGui import QAction, QCloseEvent, QCursor, QGuiApplication
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStyle,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
    QMenu,
)

from app.config.settings import AppSettings
from app.gui.capture_overlay import CaptureOverlay
from app.gui.hover_popup import HoverPopup
from app.gui.result_window import ResultWindow
from app.gui.settings_window import SettingsWindow
from app.services.glossary_service import GlossaryService
from app.services.hotkey_service import HotkeyService
from app.services.hover_service import HoverService
from app.services.hover_translation_worker import HoverTranslationWorker
from app.services.local_model_provider import LocalModelTranslationProvider
from app.services.ocr_service import OCRService
from app.services.screenshot_service import ScreenshotService
from app.services.translation_service import TranslationService
from app.utils.resources import resource_root

LOGGER = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self, settings: AppSettings) -> None:
        super().__init__()
        self.settings = settings
        self._quitting = False
        self._capture_pending = False
        self.setWindowTitle("ERP Translator")
        self.setFixedWidth(330)

        self.root = resource_root()
        glossary = GlossaryService(self.root / "data" / "glossary.json")
        self.translation_service = TranslationService(
            glossary,
            LocalModelTranslationProvider(self.root / "models"),
        )
        self.screenshot_service = ScreenshotService()
        self.ocr_service = self._make_ocr_service()
        self.overlay = CaptureOverlay()
        self.result_window = ResultWindow()
        self.hover_popup = HoverPopup()
        self._last_hover_text = ""
        self._hover_busy = False
        self.thread_pool = QThreadPool.globalInstance()
        if settings.result_x is not None and settings.result_y is not None:
            self.result_window.move(settings.result_x, settings.result_y)
        self.result_window.position_changed.connect(self.remember_result_position)

        title = QLabel("Translate visible Spanish ERP text")
        title.setAlignment(Qt.AlignCenter)
        translate_area = QPushButton("Translate Area")
        clipboard = QPushButton("Translate Clipboard Image")
        settings_button = QPushButton("Settings")
        exit_button = QPushButton("Exit")
        self.explain = QCheckBox("Explain ERP meaning")
        self.explain.setChecked(settings.explain_erp)
        self.automatic_hover = QPushButton()
        self.automatic_hover.setCheckable(True)
        self.automatic_hover.setChecked(settings.automatic_hover)
        self._update_bot_button(settings.automatic_hover)
        hint = QLabel("Global hotkey: Ctrl+Shift+T")
        hint.setAlignment(Qt.AlignCenter)

        translate_area.clicked.connect(self.start_capture)
        clipboard.clicked.connect(self.translate_clipboard_image)
        settings_button.clicked.connect(self.open_settings)
        exit_button.clicked.connect(self.quit_application)
        self.explain.toggled.connect(self.explanation_toggled)
        self.automatic_hover.toggled.connect(self.automatic_hover_toggled)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)
        layout.addWidget(title)
        layout.addWidget(translate_area)
        layout.addWidget(clipboard)
        layout.addWidget(self.automatic_hover)
        layout.addWidget(self.explain)
        layout.addWidget(settings_button)
        layout.addWidget(exit_button)
        layout.addWidget(hint)
        self.setCentralWidget(central)

        self.overlay.area_selected.connect(self.capture_area)
        self.hotkey = HotkeyService()
        self.hotkey.activated.connect(self.start_capture)
        self.hotkey.error.connect(self.show_hotkey_error)
        self.hotkey.start()
        self.hover_service = HoverService()
        self.hover_service.hover_requested.connect(self.translate_hovered_text)
        self.hover_service.pointer_moved.connect(self.hover_popup.hide)
        if settings.automatic_hover:
            self.hover_service.start()
        self._create_tray()

    def _make_ocr_service(self) -> OCRService:
        bundled_tesseract = self.root / "tesseract" / "tesseract.exe"
        configured_path = self.settings.tesseract_path
        if not configured_path and bundled_tesseract.exists():
            configured_path = str(bundled_tesseract)
        bundled_tessdata = self.root / "tesseract" / "tessdata"
        tessdata_dir = (
            bundled_tessdata
            if bundled_tessdata.exists()
            else self.root / ".runtime" / "tessdata"
        )
        return OCRService(
            configured_path,
            self.settings.ocr_language,
            tessdata_dir,
        )

    def _create_tray(self) -> None:
        icon = self.style().standardIcon(QStyle.SP_ComputerIcon)
        self.setWindowIcon(icon)
        self.tray = QSystemTrayIcon(icon, self)
        menu = QMenu()
        show_action = QAction("Show ERP Translator", self)
        translate_action = QAction("Translate Area", self)
        exit_action = QAction("Exit", self)
        self.bot_tray_action = QAction(self)
        self.bot_tray_action.setCheckable(True)
        self.bot_tray_action.setChecked(self.settings.automatic_hover)
        self._update_tray_bot_action(self.settings.automatic_hover)
        show_action.triggered.connect(self.show_normal)
        translate_action.triggered.connect(self.start_capture)
        exit_action.triggered.connect(self.quit_application)
        self.bot_tray_action.triggered.connect(self.automatic_hover.setChecked)
        menu.addAction(show_action)
        menu.addAction(translate_action)
        menu.addAction(self.bot_tray_action)
        menu.addSeparator()
        menu.addAction(exit_action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_activated)
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()

    def _tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_normal()

    def show_normal(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def start_capture(self) -> None:
        if self._capture_pending or self.overlay.isVisible():
            return
        self.overlay.begin()

    def translate_hovered_text(self, pointer: QPoint) -> None:
        if self._hover_busy or self.overlay.isVisible() or self._capture_pending or self._pointer_over_own_window(pointer):
            return
        screen = QGuiApplication.screenAt(pointer)
        if screen is None:
            return
        bounds = screen.geometry()
        # ERP tree rows are normally 18–26 px tall. A narrow strip prevents OCR
        # from selecting the row above or below the pointer.
        region = QRect(pointer.x() - 300, pointer.y() - 10, 600, 20).intersected(bounds)
        if region.width() < 50 or region.height() < 12:
            return
        try:
            image = self.screenshot_service.capture(region)
            self._hover_busy = True
            self.hover_popup.show_status("Reading and translating…", pointer)
            worker = HoverTranslationWorker(
                image,
                pointer,
                self.ocr_service,
                self.translation_service,
                self.explain.isChecked(),
                self.settings.target_language,
            )
            worker.signals.completed.connect(self._hover_translation_completed)
            worker.signals.failed.connect(self._hover_translation_failed)
            self.thread_pool.start(worker)
        except Exception:
            LOGGER.exception("Automatic hover translation failed")

    def _hover_translation_completed(self, result, pointer: QPoint, text: str) -> None:  # type: ignore[no-untyped-def]
        self._hover_busy = False
        current = QCursor.pos()
        if abs(current.x() - pointer.x()) + abs(current.y() - pointer.y()) > 10:
            self.hover_popup.hide()
            return
        if not result or not text or text == self._last_hover_text:
            self.hover_popup.hide()
            return
        self._last_hover_text = text
        self.hover_popup.show_result(result, pointer)

    def _hover_translation_failed(self, message: str) -> None:
        self._hover_busy = False
        self.hover_popup.hide()
        LOGGER.warning("Hover translation failed: %s", message)

    def _pointer_over_own_window(self, pointer: QPoint) -> bool:
        for widget in QApplication.topLevelWidgets():
            if widget.isVisible() and widget.frameGeometry().contains(pointer):
                return True
        return False

    def capture_area(self, rectangle) -> None:  # type: ignore[no-untyped-def]
        self._capture_pending = True
        QTimer.singleShot(180, lambda: self._capture_and_translate(rectangle))

    def _capture_and_translate(self, rectangle) -> None:  # type: ignore[no-untyped-def]
        try:
            image = self.screenshot_service.capture(rectangle)
            self.process_image(image)
        except Exception as exc:
            self.show_processing_error(exc)
        finally:
            self._capture_pending = False

    def translate_clipboard_image(self) -> None:
        image = QGuiApplication.clipboard().image()
        if image.isNull():
            QMessageBox.information(self, "ERP Translator", "The clipboard does not contain an image.")
            return
        try:
            self.process_image(self.screenshot_service.qimage_to_pil(image))
        except Exception as exc:
            self.show_processing_error(exc)

    def process_image(self, image: Image.Image) -> None:
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            text = self.ocr_service.extract_text(image)
            result = self.translation_service.translate(
                text,
                self.explain.isChecked(),
                self.settings.target_language,
            )
            self.result_window.show_result(result)
        finally:
            QApplication.restoreOverrideCursor()

    def show_processing_error(self, exc: Exception) -> None:
        LOGGER.exception("Image processing failed", exc_info=exc)
        message = str(exc)
        if "tesseract" in message.lower():
            message += (
                "\n\nInstall Tesseract with Spanish language data, then select "
                "tesseract.exe in Settings."
            )
        QMessageBox.critical(self, "ERP Translator", message)

    def show_hotkey_error(self, message: str) -> None:
        QMessageBox.warning(
            self,
            "Global hotkey unavailable",
            f"Ctrl+Shift+T could not be registered:\n{message}\n\nThe Translate Area button still works.",
        )

    def open_settings(self) -> None:
        dialog = SettingsWindow(self.settings, self)
        dialog.settings_saved.connect(self.reload_settings)
        dialog.exec()

    def reload_settings(self) -> None:
        self.ocr_service = self._make_ocr_service()
        self.explain.setChecked(self.settings.explain_erp)
        self.automatic_hover.setChecked(self.settings.automatic_hover)

    def explanation_toggled(self, checked: bool) -> None:
        self.settings.explain_erp = checked
        self.settings.save()

    def automatic_hover_toggled(self, checked: bool) -> None:
        self.settings.automatic_hover = checked
        self.settings.save()
        self._update_bot_button(checked)
        if hasattr(self, "bot_tray_action"):
            self.bot_tray_action.setChecked(checked)
            self._update_tray_bot_action(checked)
        self._last_hover_text = ""
        if checked:
            self.hover_service.start()
        else:
            self.hover_service.stop()
            self.hover_popup.hide()

    def _update_bot_button(self, enabled: bool) -> None:
        if enabled:
            self.automatic_hover.setText("Translation Bot: ON")
            self.automatic_hover.setStyleSheet(
                "QPushButton { background: #238636; color: white; font-weight: 600; "
                "padding: 9px; border-radius: 5px; }"
                "QPushButton:hover { background: #2ea043; }"
            )
        else:
            self.automatic_hover.setText("Translation Bot: OFF")
            self.automatic_hover.setStyleSheet(
                "QPushButton { background: #b42318; color: white; font-weight: 600; "
                "padding: 9px; border-radius: 5px; }"
                "QPushButton:hover { background: #d92d20; }"
            )

    def _update_tray_bot_action(self, enabled: bool) -> None:
        self.bot_tray_action.setText("Turn Bot OFF" if enabled else "Turn Bot ON")

    def remember_result_position(self, x: int, y: int) -> None:
        if not self.result_window.isVisible():
            return
        self.settings.result_x = x
        self.settings.result_y = y
        self.settings.save()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._quitting or not QSystemTrayIcon.isSystemTrayAvailable():
            event.accept()
            return
        event.ignore()
        self.hide()
        self.tray.showMessage(
            "ERP Translator",
            "Still running. Press Ctrl+Shift+T to translate an area.",
            QSystemTrayIcon.Information,
            2500,
        )

    def quit_application(self) -> None:
        self._quitting = True
        self.hotkey.stop()
        self.hover_service.stop()
        self.settings.save()
        self.tray.hide()
        QApplication.quit()
