"""Filesystem pre/post snapshot collector for monitored install paths."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import structlog

from smartinstall.core.models.evidence import FilesystemChangeEvidence

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class _FileState:
    size_bytes: int
    modified_epoch: float


@dataclass(slots=True)
class FilesystemCollectionResult:
    changes: list[FilesystemChangeEvidence] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class FilesystemCollector:
    """Detects created, deleted, and modified files under configured roots."""

    def __init__(
        self,
        monitored_paths: list[str],
        *,
        max_events: int = 10000,
        max_depth: int = 4,
    ) -> None:
        self._monitored_paths = monitored_paths
        self._max_events = max_events
        self._max_depth = max_depth
        self._pre_snapshot: dict[str, _FileState] | None = None

    def take_pre_snapshot(self) -> None:
        self._pre_snapshot = self._capture_all()

    def collect(self) -> FilesystemCollectionResult:
        result = FilesystemCollectionResult()
        if not self._monitored_paths:
            return result
        if self._pre_snapshot is None:
            self.take_pre_snapshot()

        post_snapshot = self._capture_all()
        changes = _diff_snapshots(self._pre_snapshot, post_snapshot)
        result.changes = changes[: self._max_events]
        if len(changes) > self._max_events:
            result.errors.append(
                f"Filesystem changes truncated to {self._max_events} of {len(changes)}."
            )
        logger.info("filesystem_changes_collected", count=len(result.changes))
        return result

    def _capture_all(self) -> dict[str, _FileState]:
        snapshot: dict[str, _FileState] = {}
        for raw_path in self._monitored_paths:
            root = _resolve_monitored_root(raw_path)
            if root is None:
                continue
            _walk_files(root, self._max_depth, snapshot, self._max_events)
            if len(snapshot) >= self._max_events:
                break
        return snapshot


def _resolve_monitored_root(raw_path: str) -> Path | None:
    expanded = Path(os.path.expandvars(raw_path)).resolve()
    if expanded.is_dir():
        return expanded
    return None


def _walk_files(root: Path, max_depth: int, snapshot: dict[str, _FileState], cap: int) -> None:
    root_key = str(root).lower()

    def walk(directory: Path, depth: int) -> None:
        if len(snapshot) >= cap:
            return
        if depth > max_depth:
            return
        try:
            entries = list(directory.iterdir())
        except OSError:
            return
        for entry in entries:
            if len(snapshot) >= cap:
                return
            if entry.is_dir():
                walk(entry, depth + 1)
                continue
            try:
                stat = entry.stat()
            except OSError:
                continue
            key = str(entry.resolve()).lower()
            if not key.startswith(root_key):
                continue
            snapshot[key] = _FileState(size_bytes=stat.st_size, modified_epoch=stat.st_mtime)

    walk(root, 0)


def _diff_snapshots(
    before: dict[str, _FileState],
    after: dict[str, _FileState],
) -> list[FilesystemChangeEvidence]:
    changes: list[FilesystemChangeEvidence] = []
    all_paths = set(before) | set(after)
    for path in sorted(all_paths):
        old = before.get(path)
        new = after.get(path)
        if old is None and new is not None:
            changes.append(
                FilesystemChangeEvidence(
                    path=path,
                    changeType="created",
                    sizeBefore=None,
                    sizeAfter=new.size_bytes,
                )
            )
            continue
        if new is None and old is not None:
            changes.append(
                FilesystemChangeEvidence(
                    path=path,
                    changeType="deleted",
                    sizeBefore=old.size_bytes,
                    sizeAfter=None,
                )
            )
            continue
        if old is not None and new is not None and (
            old.size_bytes != new.size_bytes or old.modified_epoch != new.modified_epoch
        ):
            changes.append(
                FilesystemChangeEvidence(
                    path=path,
                    changeType="modified",
                    sizeBefore=old.size_bytes,
                    sizeAfter=new.size_bytes,
                )
            )
    return changes
