"""RAG pipeline — feeds consolidated installation report into local Phi-3 for diagnosis."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

_KB_PATH = Path(__file__).parents[4] / "rag"  # repo-root/rag/


@dataclass
class RagDiagnosis:
    session_id: str
    outcome: str
    root_cause: str
    confidence: str
    evidence: str
    recommended_fixes: list[str]
    verification_commands: list[str]
    escalation: str
    retrieved_docs: list[str]
    raw_answer: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "outcome": self.outcome,
            "root_cause": self.root_cause,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "recommended_fixes": self.recommended_fixes,
            "verification_commands": self.verification_commands,
            "escalation": self.escalation,
            "retrieved_docs": self.retrieved_docs,
            "raw_answer": self.raw_answer,
        }


class RagPipeline:
    """Loads the KB once and diagnoses any number of reports."""

    def __init__(self, kb_path: Path = _KB_PATH) -> None:
        self._kb_path = kb_path
        self._chain = None
        self._retriever = None

    def _build_chain(self) -> None:
        """Lazy-load so the agent doesn't pay import cost unless there's a failure."""
        from langchain_chroma import Chroma
        from langchain_classic.chains import create_retrieval_chain
        from langchain_classic.chains.combine_documents import create_stuff_documents_chain
        from langchain_core.documents import Document
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_ollama import OllamaEmbeddings, OllamaLLM

        docs = [
            Document(
                page_content=f.read_text(encoding="utf-8"),
                metadata={"source": f.name},
            )
            for f in sorted(self._kb_path.glob("*.md"))
        ]
        if not docs:
            raise FileNotFoundError(f"No KB docs found at {self._kb_path}")

        logger.info("rag_kb_loaded", doc_count=len(docs), kb_path=str(self._kb_path))

        embeddings = OllamaEmbeddings(model="nomic-embed-text")
        vector_store = Chroma.from_documents(documents=docs, embedding=embeddings)
        self._retriever = vector_store.as_retriever(search_kwargs={"k": 2})

        llm = OllamaLLM(model="phi3", temperature=0)

        system_prompt = (
            "You are an automated Windows IT assistant for Smart Installer AI.\n"
            "Analyze the installation failure log using ONLY the provided documentation context.\n"
            "Respond in this exact format:\n\n"
            "Root Cause: <one sentence>\n"
            "Confidence: High | Medium | Low\n"
            "Evidence: <what in the log matched>\n"
            "Recommended Fixes:\n1. ...\n2. ...\n3. ...\n"
            "Verification Commands:\n- <command>\n"
            "Escalation: <when to escalate and to whom>\n\n"
            "If the log does not match any known failure, say so explicitly.\n\n"
            "Documentation Context:\n{context}"
        )
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "Installation failure log:\n\n{input}"),
        ])
        qa_chain = create_stuff_documents_chain(llm, prompt)
        self._chain = create_retrieval_chain(self._retriever, qa_chain)

    def diagnose(self, report: dict[str, Any], session_id: str = "") -> RagDiagnosis:
        """Run RAG diagnosis on a unified installation report dict."""
        if self._chain is None:
            self._build_chain()

        log_text = _extract_log_text(report)
        result = self._chain.invoke({"input": log_text})

        answer: str = result.get("answer", "")
        context_docs = result.get("context", [])
        retrieved = [d.metadata.get("source", "") for d in context_docs]

        outcome = (report.get("status") or {}).get("installation_outcome", "UNKNOWN")
        diagnosis = _parse_answer(answer, session_id=session_id, outcome=outcome)
        diagnosis.retrieved_docs = retrieved
        diagnosis.raw_answer = answer

        logger.info(
            "rag_diagnosis_complete",
            session_id=session_id,
            confidence=diagnosis.confidence,
            retrieved_docs=retrieved,
        )
        return diagnosis

    def diagnose_from_file(self, report_path: Path) -> RagDiagnosis:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        session_id = (report.get("status") or {}).get("sessionId", report_path.stem)
        return self.diagnose(report, session_id=session_id)


def _extract_log_text(report: dict[str, Any]) -> str:
    """Flatten the most diagnostic fields from the report into a log string."""
    lines: list[str] = []

    status = report.get("status") or {}
    lines.append(f"installationOutcome = {status.get('installation_outcome', 'UNKNOWN')}")
    lines.append(f"exitCode = {status.get('exit_code', 'unknown')}")
    lines.append(f"executionCompleted = {status.get('execution_completed', False)}")
    if status.get("timed_out"):
        lines.append("installer.timedOut = true")

    for err in (report.get("errors") or [])[:10]:
        cat = err.get("category", "")
        msg = err.get("message", "")
        code = err.get("code", "")
        parts = [p for p in [cat, code, msg] if p]
        lines.append(" | ".join(parts))

    evidence = report.get("evidence") or {}
    for crash in (evidence.get("crash_reports") or [])[:3]:
        lines.append(f"Crash report detected: {crash.get('faulting_application', '')} "
                     f"exception={crash.get('exception_code', '')}")
    for ev in (evidence.get("event_log_entries") or [])[:5]:
        if ev.get("level") in ("Error", "Critical"):
            lines.append(f"EventLog [{ev['level']}]: {ev.get('message', '')[:200]}")

    raw = "\n".join(lines)
    return _filter_error_lines(raw)


def _filter_error_lines(text: str, tail: int = 20) -> str:
    pattern = re.compile(
        r"(error|critical|failed|failure|timeout|cancelled|denied|missing|crash|exception)",
        re.IGNORECASE,
    )
    lines = text.strip().splitlines()
    filtered = [l for l in lines if pattern.search(l)]
    relevant = filtered if filtered else lines
    return "\n".join(relevant[-tail:])


def _parse_answer(answer: str, session_id: str, outcome: str) -> RagDiagnosis:
    """Best-effort parse of the structured Phi-3 response."""

    def _extract(label: str) -> str:
        m = re.search(rf"{label}:\s*(.+?)(?=\n[A-Z]|\Z)", answer, re.IGNORECASE | re.DOTALL)
        return m.group(1).strip() if m else ""

    fixes_block = _extract("Recommended Fixes")
    fixes = [l.lstrip("0123456789.-) ").strip() for l in fixes_block.splitlines() if l.strip()]

    cmds_block = _extract("Verification Commands")
    cmds = [l.lstrip("- ").strip() for l in cmds_block.splitlines() if l.strip()]

    return RagDiagnosis(
        session_id=session_id,
        outcome=outcome,
        root_cause=_extract("Root Cause"),
        confidence=_extract("Confidence"),
        evidence=_extract("Evidence"),
        recommended_fixes=fixes,
        verification_commands=cmds,
        escalation=_extract("Escalation"),
        retrieved_docs=[],
    )
