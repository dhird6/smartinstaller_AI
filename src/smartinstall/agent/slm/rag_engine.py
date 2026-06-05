"""Local RAG + SLM diagnosis engine (shared by CLI and desktop UI)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from langchain_chroma import Chroma
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import OllamaEmbeddings, OllamaLLM

from smartinstall.agent.infrastructure.project_paths import get_project_root
from smartinstall.agent.slm.diagnosis_policy import input_targets_smartinstall_ai_stack
from smartinstall.core.models.unified_report import UnifiedInstallationReport

_INSTALLER_RAG_DOCS = frozenset(
    {
        "mingw_installation.md",
        "windows_installer_common.md",
        "testapp_disk_storage.md",
        "testapp_download_failures.md",
        "testapp_permissions.md",
        "testapp_msi_engine.md",
    }
)


@dataclass(frozen=True, slots=True)
class RagDiagnosisConfig:
    """Runtime configuration for local SLM inference."""

    docs_path: Path
    llm_model: str = "phi3:mini"
    embedding_model: str = "nomic-embed-text"
    top_k: int = 2
    temperature: float = 0.0


@dataclass(frozen=True, slots=True)
class RagDiagnosisResult:
    """Outcome of a single RAG diagnosis run."""

    answer: str
    sources: list[str]
    prompt_input: str


_ERROR_LINE_PATTERN = re.compile(
    r"(error|critical|failed|warning|exception|timeout|refused|denied|network)",
    re.IGNORECASE,
)

# Keywords that indicate an Autodesk-specific query — route to rag/ only
_AUTODESK_KEYWORDS: frozenset[str] = frozenset({
    "autodesk", "autocad", "revit", "inventor", "civil 3d", "navisworks",
    "flexnet", "adsk", "adsklic", "adsklic ensingservice", "odis",
    "autodesk access", "adlm", "lmtools", "lmgrd", "flexlm",
})


def extract_relevant_log_lines(log_text: str, *, tail: int = 40) -> str:
    """Filter to high-signal lines; fall back to the last `tail` lines."""
    lines = [line for line in log_text.strip().splitlines() if line.strip()]
    filtered = [line for line in lines if _ERROR_LINE_PATTERN.search(line)]
    relevant = filtered if filtered else lines
    return "\n".join(relevant[-tail:])


def load_report(report_path: Path) -> UnifiedInstallationReport:
    """Load and validate a SmartInstall unified report JSON file."""
    resolved = report_path.resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"Report not found: {resolved}")
    raw = json.loads(resolved.read_text(encoding="utf-8"))
    return UnifiedInstallationReport.model_validate(raw)


def build_input_from_report(report: UnifiedInstallationReport) -> str:
    """Convert a unified report into compact SLM prompt input."""
    status = report.status
    installer_name = status.installer.installer_name
    lines: list[str] = [
        "TASK: Diagnose the Windows software installation session below.",
        f"Monitored product (focus all advice on this installer): {installer_name}",
        f"Application: {status.application}",
        f"Installer path: {status.installer.installer_path}",
        f"Outcome: {status.installation_outcome}",
        f"Completed: {status.installation_completed}",
        f"Workflow: {status.workflow_status}",
        "Do NOT recommend Ollama, phi3, or Smart Installer AI setup unless explicitly mentioned in the evidence.",
    ]
    if status.failure_reason:
        lines.append(f"Failure reason: {status.failure_reason}")

    for error in report.errors[:30]:
        lines.append(
            "ERROR "
            f"[{error.category}/{error.code}]: "
            f"{error.message} | source={error.source}"
        )

    for event in report.evidence.event_logs[:20]:
        lines.append(
            "EVENT "
            f"[{event.level}/{event.event_id}]: "
            f"{event.message}"
        )

    for installer_log in report.evidence.installer_log_files[:10]:
        for preview in installer_log.preview_lines[:6]:
            lines.append(f"INSTALLER_LOG: {preview}")

    for change in report.evidence.registry_changes[:10]:
        lines.append(
            "REGISTRY "
            f"{change.change_type}: {change.hive}\\{change.key_path}\\{change.value_name}"
        )

    for change in report.evidence.filesystem_changes[:10]:
        lines.append(f"FILESYSTEM {change.change_type}: {change.path}")

    return extract_relevant_log_lines("\n".join(lines))


def build_input_from_report_path(report_path: Path) -> str:
    """Load report JSON from disk and build SLM prompt input."""
    return build_input_from_report(load_report(report_path))


def default_rag_docs_path() -> Path:
    import sys

    root = get_project_root()
    candidates = [
        root / "rag_docs",
        Path(getattr(sys, "_MEIPASS", root)) / "rag_docs",
    ]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate.resolve()
    return (root / "rag_docs").resolve()


def _is_autodesk_query(text: str) -> bool:
    """Return True if the query contains Autodesk-specific product or service names."""
    lower = text.lower()
    return any(kw in lower for kw in _AUTODESK_KEYWORDS)


def _load_documents(docs_path: Path, input_text: str = "") -> list[Document]:
    """Load markdown docs, routing to the correct KB folder based on query content.

    - Autodesk queries  → only rag/  (33 Autodesk/generic docs)
    - Everything else   → rag_docs/ first, then rag/ as fallback
    """
    root = get_project_root()
    rag_dir = (root / "rag").resolve()
    search_dirs: list[Path] = []

    if _is_autodesk_query(input_text):
        # Route Autodesk-specific queries exclusively to the Autodesk KB so that
        # Ollama-specific docs (connection_refused, port_conflict) cannot outrank them.
        if rag_dir.is_dir():
            search_dirs.append(rag_dir)
    else:
        if docs_path.is_dir():
            search_dirs.append(docs_path.resolve())
        if rag_dir.is_dir() and rag_dir not in search_dirs:
            search_dirs.append(rag_dir)

    if not search_dirs:
        raise FileNotFoundError(f"RAG docs directory not found: {docs_path}")

    documents: list[Document] = []
    seen: set[str] = set()
    for folder in search_dirs:
        for md_file in sorted(folder.glob("*.md")):
            if md_file.name in seen:
                continue
            seen.add(md_file.name)
            text = md_file.read_text(encoding="utf-8")
            doc_category = "installer" if md_file.name in _INSTALLER_RAG_DOCS else "platform"
            documents.append(Document(
                page_content=text,
                metadata={"source": md_file.name, "doc_category": doc_category},
            ))

    if not documents:
        raise RuntimeError(f"No markdown documents found in {search_dirs}")
    return documents


def _documents_for_retrieval(
    documents: list[Document],
    input_text: str,
) -> list[Document]:
    """Exclude Smart Installer / Ollama platform docs unless evidence is about that stack."""
    if input_targets_smartinstall_ai_stack(input_text):
        return documents
    installer_docs = [d for d in documents if d.metadata.get("doc_category") == "installer"]
    if installer_docs:
        return installer_docs
    return documents


def run_rag_diagnosis(
    input_text: str,
    config: RagDiagnosisConfig,
) -> RagDiagnosisResult:
    """Run retrieval-augmented diagnosis against the local knowledge base."""
    all_documents = _load_documents(config.docs_path.resolve(), input_text=input_text)
    documents = _documents_for_retrieval(all_documents, input_text)
    embeddings = OllamaEmbeddings(model=config.embedding_model)
    vector_store = Chroma.from_documents(documents=documents, embedding=embeddings)
    retriever = vector_store.as_retriever(search_kwargs={"k": max(config.top_k, 3)})

    llm = OllamaLLM(model=config.llm_model, temperature=config.temperature)
    system_prompt = (
        "You are an automated Windows SOFTWARE INSTALLER troubleshooting assistant.\n"
        "The user evidence describes a third-party installer (e.g. MinGW, VS Code, MSI package).\n"
        "Use the documentation context only when it applies to THAT product and the log evidence.\n"
        "Never suggest installing Ollama, pulling phi3, or fixing Smart Installer AI unless the "
        "evidence explicitly mentions those tools.\n"
        "If context documents are unrelated, answer from the installation evidence only.\n"
        "Respond with these sections:\n"
        "1) Error Summary\n"
        "2) Root Cause\n"
        "3) Recommended Fix (numbered steps)\n"
        "If evidence is insufficient, say what additional data is needed.\n\n"
        "Documentation Context:\n{context}"
    )
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "Installation failure evidence:\n\n{input}"),
        ]
    )
    qa_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(retriever, qa_chain)
    result = rag_chain.invoke({"input": input_text})
    sources = [str(doc.metadata.get("source", "unknown")) for doc in result.get("context", [])]
    return RagDiagnosisResult(
        answer=str(result.get("answer", "")),
        sources=sources,
        prompt_input=input_text,
    )


def diagnose_report(
    report_path: Path,
    config: RagDiagnosisConfig,
) -> RagDiagnosisResult:
    """End-to-end diagnosis from a SmartInstall JSON report path."""
    prompt_input = build_input_from_report_path(report_path)
    diagnosis = run_rag_diagnosis(prompt_input, config)
    return diagnosis
