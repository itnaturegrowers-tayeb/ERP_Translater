from __future__ import annotations

from io import BytesIO

import mss
from PIL import Image
from PySide6.QtCore import QBuffer, QIODevice, QRect
from PySide6.QtGui import QGuiApplication, QImage, QScreen


class ScreenshotService:
    def capture(self, rectangle: QRect) -> Image.Image:
        with mss.mss() as capture:
            screen = QGuiApplication.screenAt(rectangle.center()) or QGuiApplication.primaryScreen()
            monitor = self._monitor_for_screen(screen, capture.monitors[1:])
            physical_rectangle = self._map_to_physical(rectangle, screen.geometry(), monitor)
            shot = capture.grab(physical_rectangle)
            return Image.frombytes("RGB", shot.size, shot.rgb)

    @staticmethod
    def _monitor_for_screen(screen: QScreen, monitors: list[dict]) -> dict:
        """Match a Qt logical screen to the equivalent physical MSS monitor."""
        primary = QGuiApplication.primaryScreen()
        if screen is primary:
            for monitor in monitors:
                if monitor.get("is_primary"):
                    return monitor

        expected_width = round(screen.geometry().width() * screen.devicePixelRatio())
        expected_height = round(screen.geometry().height() * screen.devicePixelRatio())
        size_matches = [
            monitor
            for monitor in monitors
            if abs(int(monitor["width"]) - expected_width) <= 2
            and abs(int(monitor["height"]) - expected_height) <= 2
        ]
        if len(size_matches) == 1:
            return size_matches[0]

        screens = QGuiApplication.screens()
        try:
            return monitors[screens.index(screen)]
        except (ValueError, IndexError):
            return monitors[0]

    @staticmethod
    def _map_to_physical(rectangle: QRect, screen_geometry: QRect, monitor: dict) -> dict[str, int]:
        """Convert Qt device-independent coordinates to physical capture pixels."""
        scale_x = int(monitor["width"]) / screen_geometry.width()
        scale_y = int(monitor["height"]) / screen_geometry.height()
        return {
            "left": int(monitor["left"]) + round((rectangle.x() - screen_geometry.x()) * scale_x),
            "top": int(monitor["top"]) + round((rectangle.y() - screen_geometry.y()) * scale_y),
            "width": max(1, round(rectangle.width() * scale_x)),
            "height": max(1, round(rectangle.height() * scale_y)),
        }

    @staticmethod
    def qimage_to_pil(image: QImage) -> Image.Image:
        buffer = QBuffer()
        buffer.open(QIODevice.WriteOnly)
        image.save(buffer, "PNG")
        return Image.open(BytesIO(bytes(buffer.data()))).convert("RGB")
