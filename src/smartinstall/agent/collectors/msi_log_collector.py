"""MSI verbose log parser (functional-spec §4)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from smartinstall.core.models.evidence import MsiDiagnosticEvidence

_FATAL_PATTERN = re.compile(r"return value 3", re.IGNORECASE)
_WARNING_PATTERN = re.compile(r"return value 2", re.IGNORECASE)
_ERROR_LINE = re.compile(r"\bERROR\b", re.IGNORECASE)
_MSI_ERROR = re.compile(r"MSI \(s\).*error", re.IGNORECASE)
_ROLLBACK = re.compile(r"rollback", re.IGNORECASE)
_ERROR_CODE = re.compile(r"error\s+(\d+)", re.IGNORECASE)


@dataclass(slots=True)
class MsiLogCollectionResult:
    diagnostics: list[MsiDiagnosticEvidence] = field(default_factory=list)
    fatal_detected: bool = False
    errors: list[str] = field(default_factory=list)


class MsiLogCollector:
    def __init__(self, max_size_mb: int = 200) -> None:
        self._max_bytes = max_size_mb * 1024 * 1024

    def parse(self, log_path: Path | None) -> MsiLogCollectionResult:
        result = MsiLogCollectionResult()
        if log_path is None or not log_path.is_file():
            result.errors.append("MSI verbose log not found")
            return result

        try:
            size = log_path.stat().st_size
            if size > self._max_bytes:
                result.errors.append("MSI log exceeded size cap; parsing tail only")
                content = self._read_tail(log_path, self._max_bytes)
            else:
                content = log_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            result.errors.append(str(exc))
            return result

        for line_no, line in enumerate(content.splitlines(), start=1):
            diagnostic = self._classify_line(line_no, line)
            if diagnostic is not None:
                result.diagnostics.append(diagnostic)
                if diagnostic.is_fatal:
                    result.fatal_detected = True
        return result

    def _classify_line(self, line_no: int, line: str) -> MsiDiagnosticEvidence | None:
        is_fatal = bool(_FATAL_PATTERN.search(line))
        is_warning = bool(_WARNING_PATTERN.search(line))
        is_rollback = bool(_ROLLBACK.search(line))
        is_error = bool(_ERROR_LINE.search(line) or _MSI_ERROR.search(line))

        if not (is_fatal or is_warning or is_rollback or is_error):
            return None

        code_match = _ERROR_CODE.search(line)
        return MsiDiagnosticEvidence(
            lineNumber=line_no,
            rawText=line[:4096],
            errorCode=code_match.group(1) if code_match else None,
            isFatal=is_fatal,
            isWarning=is_warning and not is_fatal,
            isRollback=is_rollback,
        )

    @staticmethod
    def _read_tail(path: Path, max_bytes: int) -> str:
        with path.open("rb") as handle:
            handle.seek(max(0, path.stat().st_size - max_bytes))
            return handle.read().decode("utf-8", errors="replace")
