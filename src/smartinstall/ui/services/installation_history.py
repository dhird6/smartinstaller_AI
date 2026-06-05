"""Load and manage recent installation run history for the desktop UI."""

from __future__ import annotations

from pathlib import Path

from smartinstall.agent.orchestration.automated_run_orchestrator import AutomatedRunResult
from smartinstall.ui.services.run_result_loader import load_run_result_from_report


def load_recent_run_results(
    reports_dir: Path,
    *,
    limit: int = 12,
) -> list[AutomatedRunResult]:
    """Return the most recent monitored installation runs from published reports."""
    if not reports_dir.is_dir():
        return []

    results: list[AutomatedRunResult] = []
    seen_sessions: set[str] = set()
    candidates = sorted(
        reports_dir.glob("*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for report_path in candidates:
        if len(results) >= limit:
            break
        run_result = load_run_result_from_report(report_path)
        if run_result is None:
            continue
        session_id = run_result.session.session_id
        if session_id in seen_sessions:
            continue
        seen_sessions.add(session_id)
        results.append(run_result)
    return results


def merge_run_history(
    existing: list[AutomatedRunResult],
    latest: AutomatedRunResult,
    *,
    limit: int = 12,
) -> list[AutomatedRunResult]:
    """Insert *latest* at the front and deduplicate by session id."""
    session_id = latest.session.session_id
    merged = [latest] + [item for item in existing if item.session.session_id != session_id]
    return merged[:limit]
