"""Tests for Troubleshooting AI suggestion bullets."""

from smartinstall.core.models.unified_report import ReportErrorEntry
from smartinstall.ui.services.troubleshooting_suggestions_service import build_ai_suggestions


class _FakeReport:
    def __init__(self, *, errors=None, failure_reason=None, outcome="failed"):
        self.errors = errors or []
        self.status = type(
            "Status",
            (),
            {"failure_reason": failure_reason, "installation_outcome": outcome},
        )()


def test_build_suggestions_from_slm_not_generic_rules() -> None:
    report = _FakeReport(
        errors=[
            ReportErrorEntry(
                category="installation",
                code="TEST_VC",
                message="VC++ missing",
                source="test",
                raw_excerpt="[TEST] Install Microsoft Visual C++ Redistributable (x64) and retry.",
            )
        ],
    )
    items = build_ai_suggestions(report)  # type: ignore[arg-type]
    assert any("SLM" in line for line in items)
    slm = "Recommended Fix: Install Microsoft Visual C++ Redistributable (x64) and retry."
    items_slm = build_ai_suggestions(report, slm_answer=slm)  # type: ignore[arg-type]
    assert any("Visual C++" in line or "Recommended" in line for line in items_slm)


def test_build_suggestions_pending_without_slm() -> None:
    report = _FakeReport(errors=[])
    items = build_ai_suggestions(report, slm_pending=True)  # type: ignore[arg-type]
    assert any("SLM" in line for line in items)


def test_build_suggestions_prefers_slm_answer() -> None:
    report = _FakeReport(
        errors=[
            ReportErrorEntry(
                category="installation",
                code="1603",
                message="Fatal error",
                source="msi",
            )
        ],
    )
    slm = "## Root cause\nDisk full on C:\n\n## Fix\nFree 2 GB and retry."
    items = build_ai_suggestions(report, slm_answer=slm)  # type: ignore[arg-type]
    assert any("Root cause" in line or "Disk" in line for line in items)
