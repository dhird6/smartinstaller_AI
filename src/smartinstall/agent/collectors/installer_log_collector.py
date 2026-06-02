"""Discover and parse log files created by EXE/GUI installers during a session."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import structlog

from smartinstall.agent.detection.stream_log_analyzer import analyze_stream_logs
from smartinstall.core.models.evidence import InstallerLogFileEvidence
from smartinstall.core.models.unified_report import ReportErrorEntry

logger = structlog.get_logger(__name__)

_LOG_SUFFIXES = {".log", ".txt", ".out", ".err"}
_SKIP_DIRS = {
    "node_modules",
    ".git",
    "windows",
    "winsxs",
    "installer",
    "microsoft.net",
}


@dataclass(slots=True)
class InstallerLogCollectionResult:
    discovered_logs: list[InstallerLogFileEvidence] = field(default_factory=list)
    extracted_errors: list[ReportErrorEntry] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class InstallerLogCollector:
    """
    Scans common directories for log files modified while the installer was running.

    Captures GUI installer errors that never appear in stdout/stderr.
    """

    def __init__(
        self,
        *,
        max_files: int = 40,
        max_file_bytes: int = 5_000_000,
        max_depth: int = 6,
        max_preview_lines: int = 20,
    ) -> None:
        self._max_files = max_files
        self._max_file_bytes = max_file_bytes
        self._max_depth = max_depth
        self._max_preview_lines = max_preview_lines
        self._session_start: datetime | None = None
        self._session_end: datetime | None = None

    def mark_session_start(self) -> None:
        self._session_start = datetime.now(timezone.utc)

    def mark_session_end(self) -> None:
        self._session_end = datetime.now(timezone.utc)

    def collect(
        self,
        *,
        installer_path: Path,
        session_directory: Path,
        installer_stem: str,
        failure_timestamp: str,
    ) -> InstallerLogCollectionResult:
        result = InstallerLogCollectionResult()
        if self._session_start is None:
            self._session_start = datetime.now(timezone.utc)
        end = self._session_end or datetime.now(timezone.utc)
        # Filesystem mtimes and late log flushes can trail session_end slightly.
        end = end + timedelta(seconds=5)
        start = self._session_start - timedelta(seconds=2)

        roots = _search_roots(installer_path)
        candidates: list[Path] = []
        for root in roots:
            if not root.is_dir():
                continue
            candidates.extend(
                _find_candidate_logs(root, start, end, self._max_depth, installer_stem)
            )

        stable_candidates: list[tuple[float, Path]] = []
        for candidate in candidates:
            try:
                stable_candidates.append((candidate.stat().st_mtime, candidate))
            except OSError:
                continue
        stable_candidates.sort(key=lambda item: item[0], reverse=True)
        candidates = [item[1] for item in stable_candidates[: self._max_files]]

        collected_dir = session_directory / "collected_logs"
        collected_dir.mkdir(parents=True, exist_ok=True)

        for path in candidates:
            try:
                stat = path.stat()
                if stat.st_size > self._max_file_bytes:
                    result.errors.append(f"Skipped large log: {path.name} ({stat.st_size} bytes)")
                    continue

                dest_name = f"{path.parent.name}_{path.name}".replace(" ", "_")
                dest = collected_dir / dest_name
                shutil.copy2(path, dest)

                preview = _read_preview(path, self._max_preview_lines)
                log_errors = analyze_stream_logs(path, path, failure_timestamp=failure_timestamp)

                evidence = InstallerLogFileEvidence(
                    filePath=str(path.resolve()),
                    copiedTo=str(dest.resolve()),
                    sizeBytes=stat.st_size,
                    modifiedTimestamp=_mtime_utc(stat.st_mtime).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
                    + "Z",
                    extractedErrorCount=len(log_errors),
                    previewLines=preview,
                )
                result.discovered_logs.append(evidence)

                for entry in log_errors:
                    entry.source = f"installer_log:{path.name}:{entry.source}"
                    result.extracted_errors.append(entry)

                logger.info(
                    "installer_log_discovered",
                    path=str(path),
                    errors=len(log_errors),
                )
            except OSError as exc:
                result.errors.append(f"{path}: {exc}")

        return result


def _search_roots(installer_path: Path) -> list[Path]:
    roots: list[Path] = [installer_path.parent.resolve()]
    for env_key in ("TEMP", "TMP", "LOCALAPPDATA", "APPDATA", "PROGRAMDATA", "USERPROFILE"):
        value = os.environ.get(env_key)
        if value:
            roots.append(Path(value).resolve())
    # MinGW / common installer output locations
    for fixed in (Path(r"C:\MinGW"), Path(r"C:\mingw-w64")):
        if fixed.is_dir():
            roots.append(fixed)
    unique: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        key = str(root).lower()
        if key not in seen:
            seen.add(key)
            unique.append(root)
    return unique


def _find_candidate_logs(
    root: Path,
    start: datetime,
    end: datetime,
    max_depth: int,
    installer_stem: str,
) -> list[Path]:
    found: list[Path] = []
    stem_lower = installer_stem.lower().replace("-", "").replace("_", "")

    def walk(directory: Path, depth: int) -> None:
        if depth > max_depth:
            return
        try:
            entries = list(directory.iterdir())
        except OSError:
            return
        for entry in entries:
            if entry.is_dir():
                if entry.name.lower() in _SKIP_DIRS:
                    continue
                walk(entry, depth + 1)
                continue
            if entry.suffix.lower() not in _LOG_SUFFIXES:
                continue
            try:
                mtime = _mtime_utc(entry.stat().st_mtime)
            except OSError:
                continue
            if mtime < start or mtime > end:
                continue
            name_lower = entry.name.lower()
            path_lower = str(entry).lower()
            is_temp_like = any(
                part in path_lower
                for part in ("\\temp\\", "\\tmp\\", "\\local\\temp", "\\appdata\\local\\temp")
            )
            if is_temp_like and entry.suffix.lower() in _LOG_SUFFIXES:
                found.append(entry)
                continue
            if (
                stem_lower in name_lower
                or stem_lower in path_lower.replace("-", "").replace("_", "")
                or "install" in name_lower
                or "setup" in name_lower
                or "error" in name_lower
                or "mingw" in path_lower
                or "download" in name_lower
            ):
                found.append(entry)

    walk(root, 0)
    return found


def _mtime_utc(epoch_seconds: float) -> datetime:
    """Convert file mtime to UTC (Windows st_mtime is local wall-clock epoch)."""
    return datetime.fromtimestamp(epoch_seconds).astimezone(timezone.utc)


def _read_preview(path: Path, max_lines: int) -> list[str]:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    if len(lines) <= max_lines:
        return [line[:500] for line in lines]
    half = max_lines // 2
    head = [line[:500] for line in lines[:half]]
    tail = [line[:500] for line in lines[-half:]]
    return head + ["... truncated ..."] + tail
