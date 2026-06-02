"""Tests for installer log discovery helpers."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from smartinstall.agent.collectors.installer_log_collector import (
    InstallerLogCollector,
    _find_candidate_logs,
)


def test_finds_log_modified_during_session(tmp_path: Path) -> None:
    log_file = tmp_path / "mingw-setup.log"
    log_file.write_text("ERROR: network unreachable\n", encoding="utf-8")

    now = datetime.now(timezone.utc)
    start = now - timedelta(minutes=1)
    end = now + timedelta(minutes=1)

    found = _find_candidate_logs(tmp_path, start, end, max_depth=2, installer_stem="mingw-get-setup")
    assert log_file in found


def test_collect_parses_errors(tmp_path: Path) -> None:
    session_dir = tmp_path / "session"
    session_dir.mkdir()
    installer = tmp_path / "mingw-get-setup.exe"
    installer.write_bytes(b"")

    collector = InstallerLogCollector(max_files=5, max_depth=3)
    collector.mark_session_start()
    log_file = tmp_path / "setup_error.log"
    log_file.write_text("FATAL: download failed due to network error\n", encoding="utf-8")
    collector.mark_session_end()

    result = collector.collect(
        installer_path=installer,
        session_directory=session_dir,
        installer_stem=installer.stem,
        failure_timestamp="2026-06-01T12:00:00.000Z",
    )

    assert result.discovered_logs or result.extracted_errors
    if result.extracted_errors:
        assert any(e.category == "network" or "network" in e.message.lower() for e in result.extracted_errors)
