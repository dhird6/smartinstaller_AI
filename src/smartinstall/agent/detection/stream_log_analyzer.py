"""Extract installation errors from captured stdout/stderr logs."""

from __future__ import annotations

import re
from pathlib import Path

from smartinstall.core.models.unified_report import ReportErrorEntry

_NETWORK_PATTERNS = (
    re.compile(r"network", re.IGNORECASE),
    re.compile(r"connection\s+(refused|failed|reset|timed\s*out)", re.IGNORECASE),
    re.compile(r"unable\s+to\s+(connect|download|reach)", re.IGNORECASE),
    re.compile(r"failed\s+to\s+download", re.IGNORECASE),
    re.compile(r"no\s+internet", re.IGNORECASE),
    re.compile(r"offline", re.IGNORECASE),
    re.compile(r"could\s+not\s+resolve", re.IGNORECASE),
    re.compile(r"name\s+resolution", re.IGNORECASE),
    re.compile(r"wget|curl", re.IGNORECASE),
)

_FAILURE_PATTERNS = (
    re.compile(r"\berror\b", re.IGNORECASE),
    re.compile(r"\bfailed\b", re.IGNORECASE),
    re.compile(r"\bfatal\b", re.IGNORECASE),
    re.compile(r"access\s+denied", re.IGNORECASE),
    re.compile(r"rollback", re.IGNORECASE),
    re.compile(r"installation\s+(failed|incomplete|aborted)", re.IGNORECASE),
)


def analyze_stream_logs(
    stdout_path: Path | None,
    stderr_path: Path | None,
    *,
    failure_timestamp: str,
) -> list[ReportErrorEntry]:
    errors: list[ReportErrorEntry] = []
    errors.extend(_scan_file(stdout_path, "stdout", failure_timestamp))
    errors.extend(_scan_file(stderr_path, "stderr", failure_timestamp))
    return errors


def _scan_file(path: Path | None, source: str, failure_timestamp: str) -> list[ReportErrorEntry]:
    if path is None or not path.is_file():
        return []

    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        return []

    found: list[ReportErrorEntry] = []
    seen: set[str] = set()

    for line_no, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if len(stripped) < 4:
            continue

        category, code = _classify_line(stripped)
        if category is None:
            continue

        key = f"{category}:{stripped[:120]}"
        if key in seen:
            continue
        seen.add(key)

        found.append(
            ReportErrorEntry(
                category=category,
                code=code,
                message=stripped[:2000],
                source=f"{source}:line{line_no}",
                timestamp=failure_timestamp,
                severity="error",
                rawExcerpt=stripped[:4096],
            )
        )
    return found


def _classify_line(line: str) -> tuple[str, str] | None:
    for pattern in _NETWORK_PATTERNS:
        if pattern.search(line):
            return "network", "NETWORK_ERROR"

    for pattern in _FAILURE_PATTERNS:
        if pattern.search(line):
            return "installation", "INSTALL_LOG_ERROR"

    return None
