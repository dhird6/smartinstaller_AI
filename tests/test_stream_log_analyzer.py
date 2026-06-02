"""Tests for stream log error extraction."""

from pathlib import Path

from smartinstall.agent.detection.stream_log_analyzer import analyze_stream_logs


def test_detects_network_errors(tmp_path: Path) -> None:
    stderr = tmp_path / "stderr.log"
    stderr.write_text(
        "[+1.000s] ERROR: failed to download package - no network connection\n",
        encoding="utf-8",
    )
    errors = analyze_stream_logs(None, stderr, failure_timestamp="2026-06-01T00:00:00.000Z")
    assert len(errors) >= 1
    assert errors[0].category == "network"
