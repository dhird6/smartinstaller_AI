"""Tests for MSI/UAC installer process chain resolution."""

from __future__ import annotations

from pathlib import Path

from smartinstall.agent.detection.process_chain_resolver import _extract_msi_path


def test_extract_msi_from_msiexec_cmdline() -> None:
    parts = [
        "msiexec.exe",
        "/i",
        r"C:\Downloads\product.msi",
        "/qn",
    ]
    result = _extract_msi_path(parts, " ".join(parts))
    assert result == Path(r"C:\Downloads\product.msi")


def test_extract_msi_quoted() -> None:
    cmd = r'msiexec.exe /i "C:\Temp\My App\setup.msi" /norestart'
    result = _extract_msi_path([], cmd)
    assert result == Path(r"C:\Temp\My App\setup.msi")


def test_extract_msi_none_when_missing() -> None:
    assert _extract_msi_path(["setup.exe", "/S"], "setup.exe /S") is None
