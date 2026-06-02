"""Tests for MSI verbose log parsing."""

from pathlib import Path

from smartinstall.agent.collectors.msi_log_collector import MsiLogCollector


def test_parses_fatal_and_warning_lines(tmp_path: Path) -> None:
    log = tmp_path / "msi_verbose.log"
    log.write_text(
        "Action start 10:10:10: Install.\n"
        "MSI (s) (CC:44) error 123: sample\n"
        "Return value 3.\n"
        "Return value 2.\n"
        "Rollback completed.\n",
        encoding="utf-8",
    )
    result = MsiLogCollector().parse(log)
    assert result.fatal_detected is True
    assert len(result.diagnostics) >= 3
    assert any(d.is_rollback for d in result.diagnostics)
