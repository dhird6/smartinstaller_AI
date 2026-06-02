"""Windows Error Reporting (WER) crash report collector."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from smartinstall.core.models.evidence import CrashReportEvidence


@dataclass(slots=True)
class WerCollectionResult:
    reports: list[CrashReportEvidence] = field(default_factory=list)
    crash_detected: bool = False
    errors: list[str] = field(default_factory=list)


class WerCollector:
    """Detects new WER report directories created during an installation session."""

    def __init__(self) -> None:
        self._baseline_dirs: set[str] = set()
        self._session_start: datetime | None = None

    def take_pre_snapshot(self) -> None:
        self._session_start = datetime.now(timezone.utc)
        self._baseline_dirs = self._list_report_dirs()

    def collect(self, installer_pids: set[int] | None = None) -> WerCollectionResult:
        result = WerCollectionResult()
        current = self._list_report_dirs()
        new_dirs = current - self._baseline_dirs

        for report_dir in new_dirs:
            report_file = Path(report_dir) / "Report.wer"
            if not report_file.is_file():
                continue
            parsed = self._parse_report_wer(report_file, report_dir)
            result.reports.append(parsed)
            result.crash_detected = True

        _ = installer_pids
        return result

    def _list_report_dirs(self) -> set[str]:
        paths: list[Path] = []
        local_app = os.environ.get("LOCALAPPDATA")
        program_data = os.environ.get("PROGRAMDATA", r"C:\ProgramData")
        if local_app:
            paths.append(
                Path(local_app) / "Microsoft" / "Windows" / "WER" / "ReportQueue"
            )
        paths.append(
            Path(program_data) / "Microsoft" / "Windows" / "WER" / "ReportQueue"
        )

        dirs: set[str] = set()
        for base in paths:
            if not base.is_dir():
                continue
            for child in base.iterdir():
                if child.is_dir():
                    dirs.add(str(child.resolve()))
        return dirs

    @staticmethod
    def _parse_report_wer(report_file: Path, report_dir: str) -> CrashReportEvidence:
        raw = report_file.read_bytes()
        text = raw.decode("utf-16", errors="replace")
        if not text.strip():
            text = raw.decode("utf-8", errors="replace")

        fields: dict[str, str] = {}
        for line in text.splitlines():
            if "=" in line:
                key, _, value = line.partition("=")
                fields[key.strip()] = value.strip()

        event_time = fields.get("EventTime") or fields.get("CreationTime")
        timestamp = None
        if event_time:
            try:
                dt = datetime.fromisoformat(event_time.replace("Z", "+00:00"))
                timestamp = dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
            except ValueError:
                timestamp = event_time

        return CrashReportEvidence(
            faultingApplication=fields.get("AppName"),
            faultingModule=fields.get("ModName"),
            exceptionCode=fields.get("ExceptionCode"),
            crashTimestamp=timestamp,
            reportDirectory=report_dir,
            friendlyEventName=fields.get("FriendlyEventName"),
        )
