"""Writes installation_failure_report.json artifact."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from smartinstall.core.models.failure_report import FAILURE_REPORT_FILENAME, InstallationFailureReport


class EvidenceWriter:
    @staticmethod
    def write(report: InstallationFailureReport, session_directory: Path) -> Path:
        path = session_directory / FAILURE_REPORT_FILENAME
        path.write_text(
            json.dumps(report.model_dump(by_alias=True, mode="json"), indent=2)
            + "\n",
            encoding="utf-8",
        )
        return path

    @staticmethod
    def utc_now() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
