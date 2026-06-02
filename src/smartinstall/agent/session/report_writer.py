"""Foundation-phase consolidated report writer (data-model §11 placeholder)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from smartinstall.agent.infrastructure.output_directory_manager import OutputDirectoryManager
from smartinstall.core.enums.installation import InstallationOutcome
from smartinstall.core.models.consolidated_report import (
    ConsolidatedInstallationReport,
    InstallerResultStub,
)
from smartinstall.core.models.installation_session import InstallationSession


class ReportWriter:
    """Writes minimal consolidated reports for foundation milestone demos."""

    def write_foundation_report(
        self,
        session: InstallationSession,
        *,
        exit_code: int | None,
        outcome: InstallationOutcome,
        diagnostic_score: int = 0,
    ) -> Path:
        session_dir = Path(session.output_directory)
        report_path = session_dir / OutputDirectoryManager.CONSOLIDATED_REPORT
        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

        installer_result = InstallerResultStub(
            sessionId=session.session_id,
            exitCode=exit_code if exit_code is not None else 0,
            startTimestamp=session.start_timestamp,
            endTimestamp=session.end_timestamp,
            timedOut=outcome == InstallationOutcome.TIMED_OUT,
        )

        report = ConsolidatedInstallationReport(
            reportGeneratedAt=generated_at,
            session=session,
            installerResult=installer_result,
            installationOutcome=outcome,
            diagnosticScore=diagnostic_score,
        )

        report_path.write_text(
            json.dumps(
                report.model_dump(by_alias=True, mode="json"),
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        return report_path
