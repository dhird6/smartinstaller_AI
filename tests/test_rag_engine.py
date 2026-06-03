"""Tests for SLM report context builder."""

import json
from pathlib import Path

from smartinstall.agent.slm.rag_engine import build_input_from_report_path, load_report


def test_build_input_from_report_path(tmp_path: Path) -> None:
    report = {
        "schemaVersion": "1.0",
        "reportGeneratedAt": "2026-06-01T00:00:00.000Z",
        "status": {
            "sessionId": "s1",
            "application": "demo",
            "installationOutcome": "Failure",
            "workflowStatus": "FAILED",
            "installationCompleted": False,
            "failureReason": "network",
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
        "errors": [
            {
                "category": "network",
                "code": "NETWORK_ERROR",
                "message": "network unreachable",
                "source": "installer_log",
                "severity": "error",
            }
        ],
        "evidence": {},
    }
    report_path = tmp_path / "smartinstall_report.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")

    prompt = build_input_from_report_path(report_path)
    assert "NETWORK_ERROR" in prompt
    assert "network unreachable" in prompt

    model = load_report(report_path)
    assert model.status.application == "demo"
