"""Tests for latest report resolution."""

import json
from pathlib import Path

from smartinstall.ui.services.report_resolver import find_latest_report


def test_find_latest_report_returns_newest_file(tmp_path: Path) -> None:
    older = tmp_path / "older_success_20260101_abcd1234.json"
    newer = tmp_path / "newer_failure_20260201_efgh5678.json"
    payload = {
        "schemaVersion": "1.0",
        "reportGeneratedAt": "2026-06-01T00:00:00.000Z",
        "status": {
            "sessionId": "abcd1234",
            "application": "demo",
            "installationOutcome": "Success",
            "workflowStatus": "COMPLETED",
            "installationCompleted": True,
            "sessionStatus": "Completed",
            "startTimestamp": "2026-06-01T00:00:00.000Z",
            "endTimestamp": "2026-06-01T00:01:00.000Z",
            "durationSeconds": 60,
            "installer": {
                "installerName": "setup.exe",
                "installerPath": "C:\\setup.exe",
                "installerType": "EXE",
            },
            "artifactDirectory": "C:\\sessions\\s1",
            "logFiles": {},
        },
        "errors": [],
        "evidence": {},
    }
    older.write_text(json.dumps(payload), encoding="utf-8")
    newer.write_text(json.dumps(payload), encoding="utf-8")

    resolved = find_latest_report(tmp_path)
    assert resolved == newer
