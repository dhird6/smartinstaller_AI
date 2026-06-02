"""Report and session output directory management (architecture deployment, SEC-04)."""

from __future__ import annotations

import json
import os
import shutil
import uuid
from pathlib import Path

from smartinstall.agent.infrastructure.config_provider import SmartInstallConfig
from smartinstall.core.exceptions.session import (
    InsufficientDiskSpaceError,
    OutputDirectoryNotWritableError,
)
from smartinstall.core.models.installation_session import InstallationSession


class OutputDirectoryManager:
    """Creates and manages session working directories and global index (REL-03)."""

    SESSION_MANIFEST = "session.json"
    SESSIONS_INDEX = "sessions_index.json"
    CONSOLIDATED_REPORT = "consolidated_report.json"

    def __init__(self, config: SmartInstallConfig) -> None:
        self._config = config
        self._output_root = config.output_root

    @property
    def output_root(self) -> Path:
        return self._output_root

    @property
    def sessions_index_path(self) -> Path:
        return self._output_root.parent / self.SESSIONS_INDEX

    def ensure_output_root(self, override_root: Path | None = None) -> Path:
        root = (override_root or self._output_root).resolve()
        self._validate_writable(root, create=True)
        self._validate_disk_space(root)
        root.mkdir(parents=True, exist_ok=True)
        return root

    def create_session_directory(self, session_id: uuid.UUID, output_root: Path) -> Path:
        session_dir = output_root / str(session_id)
        session_dir.mkdir(parents=True, exist_ok=False)
        self._apply_directory_permissions(session_dir)
        return session_dir

    def write_session_manifest(self, session: InstallationSession) -> Path:
        manifest_path = Path(session.output_directory) / self.SESSION_MANIFEST
        self._write_json_atomic(manifest_path, session.to_session_json())
        return manifest_path

    def append_sessions_index(
        self,
        session: InstallationSession,
        *,
        outcome: str,
        diagnostic_score: int,
    ) -> Path:
        index_path = self.sessions_index_path
        index_path.parent.mkdir(parents=True, exist_ok=True)

        entry = {
            "sessionId": session.session_id,
            "startTimestamp": session.start_timestamp,
            "endTimestamp": session.end_timestamp,
            "outcome": outcome,
            "diagnosticScore": diagnostic_score,
            "reportPath": session.report_path,
        }

        entries: list[dict[str, object]] = []
        if index_path.is_file():
            try:
                loaded = json.loads(index_path.read_text(encoding="utf-8"))
                if isinstance(loaded, list):
                    entries = loaded
            except json.JSONDecodeError:
                entries = []

        entries.append(entry)
        self._write_json_atomic(index_path, entries)
        return index_path

    def discover_incomplete_session_dirs(self, output_root: Path | None = None) -> list[Path]:
        root = (output_root or self._output_root).resolve()
        if not root.is_dir():
            return []

        incomplete: list[Path] = []
        terminal_statuses = {"Completed", "Failed", "Incomplete", "TimedOut"}

        for child in root.iterdir():
            if not child.is_dir():
                continue
            manifest = child / self.SESSION_MANIFEST
            if not manifest.is_file():
                continue
            try:
                data = json.loads(manifest.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                incomplete.append(child)
                continue
            status = data.get("sessionStatus")
            if status not in terminal_statuses:
                incomplete.append(child)
        return incomplete

    def _validate_writable(self, path: Path, *, create: bool) -> None:
        try:
            if create:
                path.mkdir(parents=True, exist_ok=True)
            test_file = path / ".write_test"
            test_file.write_text("", encoding="utf-8")
            test_file.unlink(missing_ok=True)
        except OSError as exc:
            raise OutputDirectoryNotWritableError(str(path), reason=str(exc)) from exc

    def _validate_disk_space(self, path: Path) -> None:
        required_gb = self._config.min_free_disk_space_gb
        usage = shutil.disk_usage(path)
        available_gb = usage.free / (1024**3)
        if available_gb < required_gb:
            raise InsufficientDiskSpaceError(required_gb, available_gb)

    @staticmethod
    def _write_json_atomic(path: Path, payload: object) -> None:
        temp_path = path.with_suffix(path.suffix + ".tmp")
        temp_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        os.replace(temp_path, path)

    @staticmethod
    def _apply_directory_permissions(session_dir: Path) -> None:
        """Best-effort restrictive permissions on Windows (SEC-04)."""
        if os.name != "nt":
            return
        try:
            import ctypes

            everyone_sid = "S-1-1-0"
            administrators_sid = "S-1-5-32-544"
            icacls_cmd = (
                f'icacls "{session_dir}" /inheritance:r '
                f'/grant:r "{administrators_sid}:(OI)(CI)F" '
                f'/grant:r "{os.environ.get("USERNAME", "")}:(OI)(CI)F" '
                f'/deny "{everyone_sid}:(OI)(CI)(W,R)"'
            )
            # Avoid shell=True; not invoked in foundation milestone on non-admin dev machines.
            _ = icacls_cmd  # Placeholder for deployment script integration.
            _ = ctypes  # Reserved for future explicit ACL API.
        except Exception:
            pass
