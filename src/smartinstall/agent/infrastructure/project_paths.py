"""Project root and standard directory layout resolution."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def get_project_root() -> Path:
    """Resolve repository root (directory containing pyproject.toml or config/)."""
    env_root = os.environ.get("SMARTINSTALL_PROJECT_ROOT")
    if env_root:
        return Path(env_root).resolve()

    anchor = Path(__file__).resolve()
    for parent in anchor.parents:
        if (parent / "pyproject.toml").is_file() or (parent / "config" / "smartinstall.config.json").is_file():
            return parent
    return Path.cwd().resolve()


def ensure_project_layout(
    *,
    installers_dir: Path,
    reports_dir: Path,
    logs_dir: Path,
    sessions_dir: Path,
) -> None:
    """Create standard project folders if missing."""
    for directory in (installers_dir, reports_dir, logs_dir, sessions_dir):
        directory.mkdir(parents=True, exist_ok=True)
