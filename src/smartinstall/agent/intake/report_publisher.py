"""Publish the single canonical report to reports/ (no duplicate JSON files)."""

from __future__ import annotations

from pathlib import Path

from smartinstall.core.models.unified_report import UnifiedInstallationReport
from smartinstall.agent.session.unified_report_writer import publish_unified_report


class ReportPublisher:
    """Writes one unified JSON file per installation run."""

    def __init__(self, reports_dir: Path) -> None:
        self._reports_dir = reports_dir.resolve()
        self._reports_dir.mkdir(parents=True, exist_ok=True)

    def publish(
        self,
        report: UnifiedInstallationReport,
        *,
        application_name: str,
    ) -> Path:
        return publish_unified_report(
            report,
            reports_dir=self._reports_dir,
            application_name=application_name,
        )
