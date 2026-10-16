from PySide6.QtCore import QRect

from app.services.screenshot_service import ScreenshotService


def test_maps_qt_logical_coordinates_to_scaled_physical_pixels() -> None:
    logical_screen = QRect(0, 0, 1536, 864)
    logical_capture = QRect(200, 600, 600, 30)
    physical_monitor = {"left": 0, "top": 0, "width": 1920, "height": 1080}

    result = ScreenshotService._map_to_physical(
        logical_capture,
        logical_screen,
        physical_monitor,
    )

    assert result == {"left": 250, "top": 750, "width": 750, "height": 38}


def test_maps_coordinates_relative_to_a_secondary_monitor() -> None:
    logical_screen = QRect(-1280, 0, 1280, 720)
    logical_capture = QRect(-1000, 100, 400, 40)
    physical_monitor = {"left": -1600, "top": 0, "width": 1600, "height": 900}

    result = ScreenshotService._map_to_physical(
        logical_capture,
        logical_screen,
        physical_monitor,
    )

    assert result == {"left": -1250, "top": 125, "width": 500, "height": 50}
