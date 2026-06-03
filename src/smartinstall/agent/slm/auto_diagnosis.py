"""Automatic SLM diagnosis runner for SmartInstall reports."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from smartinstall.agent.infrastructure.project_paths import get_project_root
from smartinstall.agent.slm.rag_engine import RagDiagnosisConfig, diagnose_report


@dataclass(slots=True)
class SlmDiagnosisResult:
    success: bool
    return_code: int
    report_path: Path
    output: str
    sources: list[str]
    error: str | None = None


def run_slm_for_report(
    report_path: Path,
    *,
    config: RagDiagnosisConfig | None = None,
    timeout_seconds: int = 300,
) -> SlmDiagnosisResult:
    """
    Validate SmartInstall JSON and run in-process RAG diagnosis.

    Security note:
    - Accepts only an existing report path.
    - Validates JSON before model invocation.
    """
    _ = timeout_seconds  # Reserved for future async timeout control.
    resolved_report = report_path.resolve()
    if not resolved_report.is_file():
        return SlmDiagnosisResult(
            success=False,
            return_code=1,
            report_path=resolved_report,
            output="",
            sources=[],
            error=f"Report JSON not found: {resolved_report}",
        )

    try:
        json.loads(resolved_report.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return SlmDiagnosisResult(
            success=False,
            return_code=1,
            report_path=resolved_report,
            output="",
            sources=[],
            error=f"Invalid report JSON: {exc}",
        )

    rag_config = config or RagDiagnosisConfig(docs_path=(get_project_root() / "rag_docs").resolve())
    try:
        diagnosis = diagnose_report(resolved_report, rag_config)
    except Exception as exc:  # noqa: BLE001
        return SlmDiagnosisResult(
            success=False,
            return_code=1,
            report_path=resolved_report,
            output="",
            sources=[],
            error=f"SLM diagnosis failed: {exc}",
        )

    output = diagnosis.answer.strip()
    if diagnosis.sources:
        output = f"{output}\n\nRetrieved sources: {', '.join(diagnosis.sources)}"
    return SlmDiagnosisResult(
        success=True,
        return_code=0,
        report_path=resolved_report,
        output=output,
        sources=diagnosis.sources,
        error=None,
    )
