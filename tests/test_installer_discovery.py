"""Tests for installer discovery."""

import os
from pathlib import Path

import pytest

from smartinstall.agent.intake.installer_discovery import InstallerDiscovery
from smartinstall.core.exceptions.validation import InvalidInputError


def test_list_and_select_latest(tmp_path: Path) -> None:
    old = tmp_path / "old_setup.exe"
    new = tmp_path / "new_setup.msi"
    old.write_bytes(b"old")
    new.write_bytes(b"new")

    os.utime(old, (1_600_000_000, 1_600_000_000))
    os.utime(new, (1_700_000_000, 1_700_000_000))

    discovery = InstallerDiscovery(tmp_path)
    installers = discovery.list_installers()
    assert len(installers) == 2
    assert discovery.select_latest().file_name == "new_setup.msi"


def test_select_by_name(tmp_path: Path) -> None:
    target = tmp_path / "python-3.13.exe"
    target.write_bytes(b"x")
    discovery = InstallerDiscovery(tmp_path)
    selected = discovery.select_by_name("python-3.13.exe")
    assert selected.path == target.resolve()


def test_empty_repository_raises(tmp_path: Path) -> None:
    discovery = InstallerDiscovery(tmp_path)
    with pytest.raises(InvalidInputError):
        discovery.select_latest()
