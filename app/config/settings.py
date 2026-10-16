from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from PySide6.QtCore import QStandardPaths

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class AppSettings:
    tesseract_path: str = ""
    ocr_language: str = "spa"
    target_language: str = "en"
    explain_erp: bool = True
    automatic_hover: bool = True
    result_x: int | None = None
    result_y: int | None = None

    @staticmethod
    def path() -> Path:
        directory = Path(QStandardPaths.writableLocation(QStandardPaths.AppConfigLocation))
        return directory / "settings.json"

    @classmethod
    def load(cls) -> "AppSettings":
        path = cls.path()
        if not path.exists():
            return cls()
        try:
            values = json.loads(path.read_text(encoding="utf-8"))
            allowed = {field.name for field in fields(cls)}
            return cls(**{key: value for key, value in values.items() if key in allowed})
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            LOGGER.warning("Could not load settings from %s: %s", path, exc)
            return cls()

    def save(self) -> None:
        path = self.path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
        except OSError:
            LOGGER.exception("Could not save settings to %s", path)
