"""Dashboard statistics from sessions, reports, and background monitoring state."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from smartinstall.agent.monitoring.monitoring_state_store import MonitoringPlatformState


@dataclass(slots=True)
class SessionSummary:
    session_id: str
    installer_name: str
    outcome: str
    timestamp: str
    report_path: str | None = None
    error_count: int = 0


@dataclass(slots=True)
class ActiveInstallationSummary:
    installer_name: str
    stage: str
    mode: str


@dataclass(slots=True)
class DashboardStats:
    total_sessions: int = 0
    successful: int = 0
    failed: int = 0
    partial: int = 0
    active_count: int = 0
    recent_sessions: list[SessionSummary] = field(default_factory=list)
    active_installations: list[ActiveInstallationSummary] = field(default_factory=list)
    background_service_running: bool = False
    automatic_monitoring_enabled: bool = True
    ai_troubleshooting_enabled: bool = True
    last_heartbeat: str = ""
    ai_recommendations: list[str] = field(default_factory=list)


def load_dashboard_stats(
    *,
    sessions_dir: Path,
    reports_dir: Path,
    platform_state: MonitoringPlatformState | None = None,
    max_recent: int = 8,
) -> DashboardStats:
    stats = DashboardStats()
    summaries: list[SessionSummary] = []

    if reports_dir.is_dir():
        for report_file in sorted(
            reports_dir.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )[:max_recent]:
            summary = _summary_from_report(report_file)
            if summary is not None:
                summaries.append(summary)

    if not summaries and sessions_dir.is_dir():
        for session_dir in sorted(
            sessions_dir.iterdir(),
            key=lambda p: p.stat().st_mtime if p.is_dir() else 0,
            reverse=True,
        )[:max_recent]:
            if not session_dir.is_dir():
                continue
            report = session_dir / "smartinstall_report.json"
            if report.is_file():
                summary = _summary_from_report(report)
                if summary is not None:
                    summaries.append(summary)

    stats.recent_sessions = summaries[:max_recent]
    stats.total_sessions = len(summaries)
    for item in summaries:
        outcome = item.outcome.lower()
        if outcome == "success":
            stats.successful += 1
        elif outcome in {"failure", "failed", "crashed", "timedout"}:
            stats.failed += 1
        elif outcome == "partial":
            stats.partial += 1

    if platform_state is not None:
        stats.active_count = len(platform_state.active_installations)
        stats.active_installations = [
            ActiveInstallationSummary(
                installer_name=item.installer_name,
                stage=item.stage,
                mode=item.mode,
            )
            for item in platform_state.active_installations
        ]
        stats.background_service_running = platform_state.service_running
        stats.automatic_monitoring_enabled = platform_state.automatic_monitoring_enabled
        stats.last_heartbeat = platform_state.last_updated

        for completed in platform_state.recent_installations[:max_recent]:
            if any(s.session_id == completed.session_id for s in stats.recent_sessions):
                continue
            stats.recent_sessions.insert(
                0,
                SessionSummary(
                    session_id=completed.session_id,
                    installer_name=completed.installer_name,
                    outcome=completed.outcome,
                    timestamp=completed.completed_at,
                    report_path=completed.report_path,
                    error_count=1 if completed.error_summary else 0,
                ),
            )
        stats.recent_sessions = stats.recent_sessions[:max_recent]
        stats.total_sessions = max(stats.total_sessions, len(platform_state.recent_installations))

    stats.ai_recommendations = _build_recommendations(stats)
    return stats


def _summary_from_report(path: Path) -> SessionSummary | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    status = data.get("status", {})
    errors = data.get("errors", [])
    installer = status.get("installer", {})
    return SessionSummary(
        session_id=str(status.get("sessionId", path.stem)),
        installer_name=str(installer.get("installerName", path.stem)),
        outcome=str(status.get("installationOutcome", "Unknown")),
        timestamp=str(status.get("endTimestamp") or status.get("startTimestamp", "")),
        report_path=str(path),
        error_count=len(errors),
    )


def _build_recommendations(stats: DashboardStats) -> list[str]:
    items: list[str] = []
    if stats.active_count > 0:
        items.append(
            f"{stats.active_count} installation(s) in progress — open Live Monitoring for real-time logs."
        )
    if stats.failed > 0:
        items.append(
            f"{stats.failed} installation(s) need review — open Troubleshooting for AI-guided fixes."
        )
    if stats.partial > 0:
        items.append("Partial installs detected — verify prerequisites and retry.")
    if stats.total_sessions == 0 and stats.active_count == 0:
        items.append(
            "Launch installers from Explorer for automatic monitoring, or use Installation Center."
        )
    else:
        items.append("Windows toast notifications surface critical errors even when the app is minimized.")
    return items[:4]
