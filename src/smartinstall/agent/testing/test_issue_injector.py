"""Inject configurable test installation errors (QA only — gated by config)."""

from __future__ import annotations

import fnmatch
import json
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import structlog

from smartinstall.agent.detection.failure_detector import FailureDetectionOutcome
from smartinstall.agent.infrastructure.config_provider import SmartInstallConfig
from smartinstall.agent.infrastructure.event_bus import AgentEvent, EventBus
from smartinstall.core.models.unified_report import ReportErrorEntry

logger = structlog.get_logger(__name__)

_VALID_TRIGGERS = frozenset({"during_install", "on_complete", "before_post_snapshot", "both"})


@dataclass(slots=True)
class TestInstallationIssue:
    id: str
    enabled: bool
    trigger: str
    delay_seconds: float
    installer_name_pattern: str
    category: str
    code: str
    message: str
    severity: str
    suggested_fix: str
    emit_live_log: bool
    show_notification: bool
    force_failed_outcome: bool
    source: str = "TestIssueInjector"


class TestIssueInjector:
    """Loads test_installation_issues.json and injects errors during monitored installs."""

    __test__ = False  # prevent pytest from collecting this helper class

    def __init__(self, issues: list[TestInstallationIssue], *, file_enabled: bool) -> None:
        self._file_enabled = file_enabled
        self._issues = [item for item in issues if item.enabled]

    @classmethod
    def from_config(cls, config: SmartInstallConfig) -> TestIssueInjector | None:
        if not config.enable_test_issue_injection:
            return None
        path = config.test_installation_issues_file
        if not path.is_file():
            logger.warning("test_issues_file_missing", path=str(path))
            return cls([], file_enabled=False)
        return cls._load_file(path)

    @classmethod
    def _load_file(cls, path: Path) -> TestIssueInjector:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("test_issues_load_failed", path=str(path), error=str(exc))
            return cls([], file_enabled=False)

        file_enabled = bool(raw.get("enabled", False))
        issues: list[TestInstallationIssue] = []
        for entry in raw.get("issues", []):
            if not isinstance(entry, dict):
                continue
            issue = _parse_issue(entry)
            if issue is not None:
                issues.append(issue)

        logger.info(
            "test_issue_injector_loaded",
            path=str(path),
            file_enabled=file_enabled,
            active=len([i for i in issues if i.enabled]),
        )
        return cls(issues, file_enabled=file_enabled)

    @property
    def is_active(self) -> bool:
        return self._file_enabled and bool(self._issues)

    def fire_before_post_snapshot(
        self,
        event_bus: EventBus,
        *,
        session_id: str,
        installer_path: Path,
        session_directory: Path | None = None,
    ) -> list[ReportErrorEntry]:
        """Inject test errors synchronously before the post-snapshot phase (QA only)."""
        if not self.is_active:
            return []
        matched = self._match(installer_path, trigger_filter={"before_post_snapshot", "both"})
        if not matched:
            return []
        if session_directory is not None:
            _append_session_test_log(session_directory, matched, phase="before_post_snapshot")

        timestamp = _utc_now()
        entries: list[ReportErrorEntry] = []
        for issue in matched:
            self._emit_issue(
                event_bus,
                session_id=session_id,
                issue=issue,
                installer_path=installer_path,
            )
            entries.append(
                ReportErrorEntry(
                    category=issue.category,
                    code=issue.code,
                    message=issue.message,
                    source=issue.source,
                    timestamp=timestamp,
                    severity=issue.severity,
                    raw_excerpt=f"[TEST] {issue.suggested_fix}" if issue.suggested_fix else "[TEST]",
                )
            )
            event_bus.publish(
                AgentEvent.INSTALL_STAGE_CHANGED,
                {
                    "sessionId": session_id,
                    "stage": f"Test error (before post-snapshot) — {issue.id}",
                },
            )
        return entries

    def schedule_during_install(
        self,
        event_bus: EventBus,
        *,
        session_id: str,
        installer_path: Path,
        session_directory: Path | None = None,
    ) -> None:
        if not self.is_active:
            return
        matched = self._match(installer_path, trigger_filter={"during_install", "both"})
        if not matched:
            return
        if session_directory is not None:
            _append_session_test_log(session_directory, matched, phase="scheduled")

        for issue in matched:
            delay = max(0.0, issue.delay_seconds)

            def _fire(issue_ref: TestInstallationIssue = issue) -> None:
                self._emit_issue(
                    event_bus,
                    session_id=session_id,
                    issue=issue_ref,
                    installer_path=installer_path,
                )

            timer = threading.Timer(delay, _fire)
            timer.daemon = True
            timer.start()
            logger.info(
                "test_issue_scheduled",
                issue_id=issue.id,
                delay_seconds=delay,
                session_id=session_id,
            )

    def merge_into_errors(
        self,
        errors: list[ReportErrorEntry],
        installer_path: Path,
    ) -> list[ReportErrorEntry]:
        if not self.is_active:
            return errors
        matched = self._match(installer_path, trigger_filter={"on_complete", "both"})
        if not matched:
            return errors

        timestamp = _utc_now()
        merged = list(errors)
        existing_codes = {entry.code for entry in merged}
        for issue in matched:
            if issue.code in existing_codes:
                continue
            merged.append(
                ReportErrorEntry(
                    category=issue.category,
                    code=issue.code,
                    message=issue.message,
                    source=issue.source,
                    timestamp=timestamp,
                    severity=issue.severity,
                    raw_excerpt=f"[TEST] {issue.suggested_fix}" if issue.suggested_fix else "[TEST]",
                )
            )
        return merged

    def apply_failed_outcome_if_needed(
        self,
        detection: FailureDetectionOutcome,
        errors: list[ReportErrorEntry],
        installer_path: Path,
    ) -> FailureDetectionOutcome:
        if not self.is_active:
            return detection
        if not any(
            issue.force_failed_outcome
            for issue in self._match(installer_path, trigger_filter=None)
        ):
            return detection
        if any(entry.severity == "error" for entry in errors):
            detection.status = "FAILED"
            if not detection.failure_reason:
                test_err = next(
                    (e for e in errors if e.source == "TestIssueInjector"),
                    errors[0] if errors else None,
                )
                if test_err is not None:
                    detection.failure_reason = test_err.message
        return detection

    def _emit_issue(
        self,
        event_bus: EventBus,
        *,
        session_id: str,
        issue: TestInstallationIssue,
        installer_path: Path,
    ) -> None:
        logger.info(
            "test_issue_fired",
            issue_id=issue.id,
            code=issue.code,
            session_id=session_id,
            installer=installer_path.name,
        )
        if issue.emit_live_log:
            event_bus.publish(
                AgentEvent.LIVE_LOG_LINE,
                {
                    "sessionId": session_id,
                    "line": f"[TEST:{issue.id}] {issue.code}: {issue.message}",
                },
            )
            event_bus.publish(
                AgentEvent.INSTALL_STAGE_CHANGED,
                {
                    "sessionId": session_id,
                    "stage": f"Test issue injected — {issue.id}",
                },
            )
        if issue.show_notification or issue.severity == "error":
            event_bus.publish(
                AgentEvent.INSTALLATION_ERROR_DETECTED,
                {
                    "sessionId": session_id,
                    "code": issue.code,
                    "message": issue.message,
                    "category": issue.category,
                    "suggestedFix": issue.suggested_fix,
                    "testIssue": True,
                    "testIssueId": issue.id,
                },
            )

    def _match(
        self,
        installer_path: Path,
        *,
        trigger_filter: set[str] | None,
    ) -> list[TestInstallationIssue]:
        name = installer_path.name
        matched: list[TestInstallationIssue] = []
        for issue in self._issues:
            if trigger_filter is not None and issue.trigger not in trigger_filter:
                continue
            if not fnmatch.fnmatch(name.lower(), issue.installer_name_pattern.lower()):
                continue
            matched.append(issue)
        return matched


def _parse_issue(entry: dict) -> TestInstallationIssue | None:
    issue_id = str(entry.get("id", "")).strip()
    if not issue_id:
        return None
    trigger = str(entry.get("trigger", "during_install")).strip().lower()
    if trigger not in _VALID_TRIGGERS:
        trigger = "during_install"
    return TestInstallationIssue(
        id=issue_id,
        enabled=bool(entry.get("enabled", True)),
        trigger=trigger,
        delay_seconds=float(entry.get("delaySeconds", 5)),
        installer_name_pattern=str(entry.get("installerNamePattern", "*")),
        category=str(entry.get("category", "installation")),
        code=str(entry.get("code", "TEST_ERROR")),
        message=str(entry.get("message", "Simulated test installation error")),
        severity=str(entry.get("severity", "error")),
        suggested_fix=str(entry.get("suggestedFix", "")),
        emit_live_log=bool(entry.get("emitLiveLog", True)),
        show_notification=bool(entry.get("showNotification", True)),
        force_failed_outcome=bool(entry.get("forceFailedOutcome", True)),
    )


def _append_session_test_log(
    session_directory: Path,
    issues: list[TestInstallationIssue],
    *,
    phase: str,
) -> None:
    try:
        log_path = session_directory / "test_injected_issues.log"
        lines = [f"[{_utc_now()}] phase={phase}"]
        for issue in issues:
            lines.append(f"  - {issue.id}: {issue.code} {issue.message}")
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
    except OSError:
        pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
