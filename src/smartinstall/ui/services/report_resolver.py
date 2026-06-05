"""Resolve installation report paths for chat-based diagnosis."""

from __future__ import annotations

from pathlib import Path


def find_latest_report(reports_dir: Path) -> Path | None:
    """Return the most recently modified unified report JSON, if any."""
    resolved = reports_dir.resolve()
    if not resolved.is_dir():
        return None

    candidates = [
        path
        for path in resolved.glob("*.json")
        if path.is_file() and _looks_like_report(path)
    ]
    if not candidates:
        return None

    return max(candidates, key=lambda path: path.stat().st_mtime)


def _looks_like_report(path: Path) -> bool:
    """Skip non-report JSON artifacts when possible."""
    name = path.name.lower()
    if name in {"config.json", "settings.json"}:
        return False
    return True
