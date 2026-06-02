"""Unit tests for SessionManager (functional-spec §1)."""

from __future__ import annotations

import json
from pathlib import Path

from smartinstall.agent.infrastructure.output_directory_manager import OutputDirectoryManager
from smartinstall.core.enums.installation import InstallationOutcome
from smartinstall.core.enums.session import SessionStatus
from smartinstall.core.models.requests import StartSessionRequest


def test_create_session_writes_manifest(container, sample_installer: Path) -> None:
    request = StartSessionRequest(installerPath=str(sample_installer))
    result = container.session_manager.create_session(request)
    assert result.success
    session = result.unwrap()
    manifest = Path(session.output_directory) / OutputDirectoryManager.SESSION_MANIFEST
    assert manifest.is_file()
    data = json.loads(manifest.read_text(encoding="utf-8"))
    assert data["sessionId"] == session.session_id
    assert data["sessionStatus"] == SessionStatus.INITIALIZING.value


def test_transition_state_persists(container, sample_installer: Path) -> None:
    request = StartSessionRequest(installerPath=str(sample_installer))
    session = container.session_manager.create_session(request).unwrap()
    tr = container.session_manager.transition_state(
        session.session_id, SessionStatus.PRE_SNAPSHOTTING
    )
    assert tr.success
    updated = container.session_manager.get_session(session.session_id).unwrap()
    assert updated.session_status == SessionStatus.PRE_SNAPSHOTTING


def test_foundation_lifecycle_produces_report(container, sample_installer: Path) -> None:
    request = StartSessionRequest(
        installerPath=str(sample_installer),
        productName="Test Product",
        callerTag="UNIT-TEST",
    )
    final = container.session_manager.run_foundation_lifecycle(request).unwrap()
    assert final.session_status == SessionStatus.COMPLETED
    assert final.report_path is not None
    assert Path(final.report_path).is_file()
    assert final.installation_outcome == InstallationOutcome.SUCCESS


def test_installer_not_found(container, tmp_path: Path) -> None:
    missing = tmp_path / "missing.msi"
    result = container.session_manager.create_session(
        StartSessionRequest(installerPath=str(missing))
    )
    assert not result.success
    assert result.error is not None
    assert result.error.error_code == "SESSION_INSTALLER_NOT_FOUND"
