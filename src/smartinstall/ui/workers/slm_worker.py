"""Background worker for local SLM diagnosis."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from smartinstall.agent.slm.rag_engine import RagDiagnosisConfig, diagnose_report


class SlmDiagnosisWorker(QThread):
    """Runs RAG diagnosis off the UI thread."""

    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, report_path: Path, config: RagDiagnosisConfig) -> None:
        super().__init__()
        self._report_path = report_path
        self._config = config

    def run(self) -> None:
        try:
            diagnosis = diagnose_report(self._report_path, self._config)
            self.succeeded.emit(diagnosis)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))
