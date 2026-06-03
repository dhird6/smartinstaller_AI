"""UI static resources (icons, etc.)."""

from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def resources_dir() -> Path:
    base = Path(__file__).resolve().parent
    if getattr(sys, "frozen", False):
        bundled = Path(getattr(sys, "_MEIPASS", base))
        candidate = bundled / "smartinstall" / "ui" / "resources"
        if candidate.is_dir():
            return candidate
    return base


def icons_dir() -> Path:
    return resources_dir() / "icons"
