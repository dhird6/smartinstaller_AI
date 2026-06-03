"""CCTech brand logo — loaded only from the project root images folder."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

from smartinstall.agent.infrastructure.project_paths import get_project_root

_LOGO_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".ico")
_LOGO_STEMS = ("logo", "Logo", "LOGO")


def project_images_dir() -> Path:
    """User brand assets: `<project_root>/images/` (also accepts `image/`)."""
    root = get_project_root()
    for folder_name in ("images", "image"):
        directory = root / folder_name
        if directory.is_dir():
            return directory
    return root / "images"


def clear_brand_asset_cache() -> None:
    """Clear cached logo path (call after replacing images/logo.png)."""
    brand_kit_logo_path.cache_clear()
    company_logo_path.cache_clear()
    app_logo_path.cache_clear()


def _resolve_logo_in_directory(directory: Path) -> Path | None:
    if not directory.is_dir():
        return None
    for stem in _LOGO_STEMS:
        for ext in _LOGO_EXTENSIONS:
            candidate = directory / f"{stem}{ext}"
            if candidate.is_file():
                return candidate
    return None


@lru_cache(maxsize=1)
def brand_kit_logo_path() -> Path | None:
    """
    Canonical CCTech logo: `<project_root>/images/logo.png`.

    Does not use bundled SVG assets under assets/ or src/.
    """
    root = get_project_root()
    explicit = [
        root / "images" / "logo.png",
        root / "image" / "logo.png",
    ]
    for path in explicit:
        if path.is_file():
            return path

    for folder_name in ("images", "image"):
        found = _resolve_logo_in_directory(root / folder_name)
        if found is not None:
            return found
    return None


@lru_cache(maxsize=1)
def company_logo_path() -> Path | None:
    """Brand logo path for all UI surfaces."""
    return brand_kit_logo_path()


@lru_cache(maxsize=1)
def app_logo_path() -> Path | None:
    """Same as company logo — single brand kit only."""
    return brand_kit_logo_path()


def load_company_logo_pixmap(size: int) -> QPixmap:
    return _load_pixmap(company_logo_path(), size)


def load_app_logo_pixmap(size: int) -> QPixmap:
    return _load_pixmap(app_logo_path(), size)


def load_logo_pixmap(size: int) -> QPixmap:
    return load_company_logo_pixmap(size)


def load_brand_logo_pixmap(size: int) -> QPixmap:
    """CCTech logo from project root `images/logo.png`."""
    return load_company_logo_pixmap(size)


def brand_kit_available() -> bool:
    return brand_kit_logo_path() is not None


def _load_pixmap(path: Path | None, size: int) -> QPixmap:
    if path is None or not path.is_file():
        return QPixmap(size, size)
    pixmap = QPixmap(str(path))
    if pixmap.isNull():
        return QPixmap(size, size)
    return pixmap.scaled(
        size,
        size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
