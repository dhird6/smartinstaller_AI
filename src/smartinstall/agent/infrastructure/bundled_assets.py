"""Extract bundled installers and harness assets when running as a frozen executable."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from smartinstall.agent.infrastructure.project_paths import get_project_root


def _bundle_root() -> Path | None:
    if not getattr(sys, "frozen", False):
        return None
    meipass = getattr(sys, "_MEIPASS", None)
    return Path(meipass) if meipass else None


def ensure_bundled_assets() -> Path:
    """
    Copy bundled TestApp installer and harness scenarios beside the frozen exe.

    Returns the installers directory path (created if needed).
    """
    root = get_project_root()
    installers_dir = root / "installers"
    installers_dir.mkdir(parents=True, exist_ok=True)

    bundle = _bundle_root()
    if bundle is None:
        return installers_dir

    _copy_if_missing(bundle / "installers" / "TestAppSetup.exe", installers_dir / "TestAppSetup.exe")

    scenarios_src = bundle / "failure_harness" / "config" / "scenarios"
    scenarios_dest = root / "failure_harness" / "config" / "scenarios"
    if scenarios_src.is_dir():
        scenarios_dest.mkdir(parents=True, exist_ok=True)
        for item in scenarios_src.glob("*.json"):
            _copy_if_missing(item, scenarios_dest / item.name)

    harness_config_src = bundle / "failure_harness" / "config" / "harness.config.json"
    harness_config_dest = root / "failure_harness" / "config" / "harness.config.json"
    if harness_config_src.is_file():
        harness_config_dest.parent.mkdir(parents=True, exist_ok=True)
        _copy_if_missing(harness_config_src, harness_config_dest)

    return installers_dir


def bundled_test_app_path() -> Path | None:
    """Resolve TestAppSetup.exe from the PyInstaller bundle or extracted installers dir."""
    bundle = _bundle_root()
    if bundle is not None:
        candidate = bundle / "installers" / "TestAppSetup.exe"
        if candidate.is_file():
            return candidate

    root = get_project_root()
    extracted = root / "installers" / "TestAppSetup.exe"
    if extracted.is_file():
        return extracted
    return None


def _copy_if_missing(src: Path, dest: Path) -> None:
    if not src.is_file():
        return
    if dest.is_file() and dest.stat().st_size == src.stat().st_size:
        return
    shutil.copy2(src, dest)
