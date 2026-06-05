"""Tests for chat RAG prompt construction."""

import json
from pathlib import Path

from smartinstall.agent.slm.rag_engine import build_chat_prompt_input


def test_build_chat_prompt_without_report() -> None:
    prompt = build_chat_prompt_input("How do I fix exit code 1603?")
    assert "USER QUESTION:" in prompt
    assert "1603" in prompt
    assert "INSTALLATION EVIDENCE" not in prompt


def test_build_chat_prompt_with_report(tmp_path: Path) -> None:
    report = {
        "schemaVersion": "1.0",
        "reportGeneratedAt": "2026-06-01T00:00:00.000Z",
        "status": {
            "sessionId": "s1",
            "application": "demo",
            "installationOutcome": "Failure",
            "workflowStatus": "FAILED",
            "installationCompleted": False,
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
                "category": "msi",
                "code": "MSI_1603",
                "message": "Fatal error during installation",
                "source": "msi_log",
                "severity": "error",
            }
        ],
        "evidence": {},
    }
    report_path = tmp_path / "demo_failure_20260601_s1.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")

    prompt = build_chat_prompt_input(
        "What went wrong with the last installation?",
        report_path=report_path,
    )
    assert "USER QUESTION:" in prompt
    assert "INSTALLATION EVIDENCE" in prompt
    assert "MSI_1603" in prompt
