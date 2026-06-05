"""Background worker for knowledge-base chat responses."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from smartinstall.agent.slm.rag_engine import (
    RagDiagnosisConfig,
    build_chat_prompt_input,
    run_chat_diagnosis,
)


class ChatRagWorker(QThread):
    """Runs RAG against the local knowledge base for conversational chat prompts."""

    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        question: str,
        config: RagDiagnosisConfig,
        *,
        report_path: Path | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("ChatRagWorker")
        self._question = question
        self._config = config
        self._report_path = report_path

    def run(self) -> None:
        try:
            prompt_input = build_chat_prompt_input(
                self._question,
                report_path=self._report_path,
            )
            diagnosis = run_chat_diagnosis(prompt_input, self._config)
            self.succeeded.emit(diagnosis)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))
