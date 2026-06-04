"""Tests for QA test issue injection loader."""

from __future__ import annotations

import json
from pathlib import Path

from smartinstall.agent.testing.test_issue_injector import TestIssueInjector


def test_load_and_match_pattern(tmp_path: Path) -> None:
    issues_file = tmp_path / "issues.json"
    issues_file.write_text(
        json.dumps(
            {
                "enabled": True,
                "issues": [
                    {
                        "id": "sample",
                        "enabled": True,
                        "trigger": "during_install",
                        "installerNamePattern": "*setup*.exe",
                        "code": "TEST_001",
                        "message": "Sample test error",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    injector = TestIssueInjector._load_file(issues_file)
    assert injector.is_active
    matched = injector._match(Path("My-setup.exe"), trigger_filter={"during_install", "both"})
    assert len(matched) == 1
    assert matched[0].code == "TEST_001"


def test_fire_before_post_snapshot_emits_entries(tmp_path: Path) -> None:
    from smartinstall.agent.infrastructure.event_bus import EventBus

    issues_file = tmp_path / "issues.json"
    issues_file.write_text(
        json.dumps(
            {
                "enabled": True,
                "issues": [
                    {
                        "id": "pre_post",
                        "enabled": True,
                        "trigger": "before_post_snapshot",
                        "code": "TEST_PRE",
                        "message": "Before post-snapshot error",
                        "suggestedFix": "Apply VC++ redistributable",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    injector = TestIssueInjector._load_file(issues_file)
    bus = EventBus()
    errors = injector.fire_before_post_snapshot(
        bus,
        session_id="sess-1",
        installer_path=Path("setup.exe"),
    )
    assert len(errors) == 1
    assert errors[0].code == "TEST_PRE"
    assert "[TEST]" in (errors[0].raw_excerpt or "")


def test_inactive_when_file_disabled(tmp_path: Path) -> None:
    issues_file = tmp_path / "issues.json"
    issues_file.write_text(json.dumps({"enabled": False, "issues": []}), encoding="utf-8")
    injector = TestIssueInjector._load_file(issues_file)
    assert not injector.is_active
