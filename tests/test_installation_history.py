"""Tests for installation history loading and merging."""

from __future__ import annotations

import json
import time
from pathlib import Path

from smartinstall.ui.services.installation_history import load_recent_run_results, merge_run_history
from smartinstall.ui.services.run_result_loader import load_run_result_from_report


def _write_report(
    path: Path,
    *,
    session_id: str,
    installer_name: str,
    outcome: str = "Success",
) -> None:
    payload = {
        "schemaVersion": "1.0",
        "reportGeneratedAt": "2026-06-01T00:00:00.000Z",
        "status": {
            "sessionId": session_id,
            "application": "demo",
            "installationOutcome": outcome,
            "workflowStatus": "COMPLETED",
            "installationCompleted": True,
            "sessionStatus": "Completed",
            "startTimestamp": "2026-06-01T00:00:00.000Z",
            "endTimestamp": "2026-06-01T00:01:00.000Z",
            "durationSeconds": 60,
            "installer": {
                "installerName": installer_name,
                "installerPath": f"C:\\installers\\{installer_name}",
                "installerType": "EXE",
            },
            "artifactDirectory": f"C:\\sessions\\{session_id}",
            "logFiles": {},
        },
        "errors": [],
        "evidence": {},
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_load_recent_run_results_orders_by_mtime_and_dedupes(tmp_path: Path) -> None:
    session_a = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    session_b = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
    first = tmp_path / "first_setup_a_20260101_aaaa1111.json"
    second = tmp_path / "second_setup_b_20260201_bbbb2222.json"
    _write_report(first, session_id=session_a, installer_name="setup_a.exe")
    time.sleep(0.02)
    _write_report(second, session_id=session_b, installer_name="setup_b.exe")

    results = load_recent_run_results(tmp_path)
    assert len(results) == 2
    assert results[0].session.session_id == session_b
    assert results[1].session.session_id == session_a


def test_merge_run_history_inserts_latest_and_dedupes_by_session(tmp_path: Path) -> None:
    session_a = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
    session_b = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
    first_path = tmp_path / "first.json"
    second_path = tmp_path / "second.json"
    _write_report(first_path, session_id=session_a, installer_name="a.exe")
    _write_report(second_path, session_id=session_b, installer_name="b.exe")
    run_a = load_run_result_from_report(first_path)
    run_b = load_run_result_from_report(second_path)
    assert run_a is not None and run_b is not None

    merged = merge_run_history([run_a], run_b)
    assert [item.session.session_id for item in merged] == [session_b, session_a]

    updated_a = load_run_result_from_report(first_path)
    assert updated_a is not None
    merged_again = merge_run_history(merged, updated_a)
    assert [item.session.session_id for item in merged_again] == [session_a, session_b]
