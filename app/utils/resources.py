from __future__ import annotations

import sys
from pathlib import Path


def resource_root() -> Path:
    """Return the source root or PyInstaller bundle resource directory."""
    bundled_root = getattr(sys, "_MEIPASS", None)
    if bundled_root:
        return Path(bundled_root)
    return Path(__file__).resolve().parents[2]
