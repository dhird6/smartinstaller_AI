"""Local SLM + RAG troubleshooting using SmartInstall report JSON as input."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from langchain_chroma import Chroma
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import OllamaEmbeddings, OllamaLLM


def extract_relevant_log_lines(log_text: str, tail: int = 40) -> str:
    """Filter to high-signal lines; fall back to last `tail` lines."""
    error_pattern = re.compile(
        r"(error|critical|failed|warning|exception|timeout|refused|denied|network)",
        re.IGNORECASE,
    )
    lines = [line for line in log_text.strip().splitlines() if line.strip()]
    filtered = [line for line in lines if error_pattern.search(line)]
    relevant = filtered if filtered else lines
    return "\n".join(relevant[-tail:])


def build_input_from_report(report_path: Path) -> str:
    """Convert smartinstall_report.json into a compact SLM prompt input."""
    report = json.loads(report_path.read_text(encoding="utf-8"))
    status = report.get("status", {})
    errors = report.get("errors", [])
    evidence = report.get("evidence", {})

    lines: list[str] = []
    lines.append(f"Application: {status.get('application', 'unknown')}")
    lines.append(f"Installer: {status.get('installerName', 'unknown')}")
    lines.append(f"Outcome: {status.get('installationOutcome', 'unknown')}")
    lines.append(f"Completed: {status.get('installationCompleted', False)}")

    for error in errors[:30]:
        lines.append(
            "ERROR "
            f"[{error.get('category', 'unknown')}/{error.get('code', 'NA')}]: "
            f"{error.get('message', '')} | source={error.get('source', 'unknown')}"
        )

    for event in evidence.get("eventLogs", [])[:20]:
        lines.append(
            "EVENT "
            f"[{event.get('level', 'info')}/{event.get('eventId', 'NA')}]: "
            f"{event.get('message', '')}"
        )

    for installer_log in evidence.get("installerLogFiles", [])[:10]:
        for preview in installer_log.get("previewLines", [])[:6]:
            lines.append(f"INSTALLER_LOG: {preview}")

    return extract_relevant_log_lines("\n".join(lines))


def _load_docs(docs_path: Path) -> list[Document]:
    documents: list[Document] = []
    for md_file in sorted(docs_path.glob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        documents.append(Document(page_content=text, metadata={"source": md_file.name}))
    return documents


def run_rag(input_text: str, docs_path: Path, top_k: int = 2) -> tuple[str, list[str]]:
    """Run local RAG and return answer + retrieved source docs."""
    documents = _load_docs(docs_path)
    if not documents:
        raise RuntimeError(f"No knowledge documents found in {docs_path}")

    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    vector_store = Chroma.from_documents(documents=documents, embedding=embeddings)
    retriever = vector_store.as_retriever(search_kwargs={"k": top_k})

    llm = OllamaLLM(model="phi3:mini", temperature=0)
    system_prompt = (
        "You are an automated Windows installer troubleshooting assistant. "
        "Use only provided context. Return concise numbered remediation steps."
        "\n\nDocumentation Context:\n{context}"
    )
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "Here is the installation failure evidence:\n\n{input}"),
        ]
    )
    qa_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(retriever, qa_chain)

    result = rag_chain.invoke({"input": input_text})
    sources = [doc.metadata.get("source", "unknown") for doc in result.get("context", [])]
    return result.get("answer", ""), sources


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local SLM diagnosis from SmartInstall JSON.")
    parser.add_argument(
        "--report",
        type=Path,
        help="Path to smartinstall_report.json (recommended input)",
    )
    parser.add_argument(
        "--text",
        type=str,
        help="Raw error text fallback when report is not provided",
    )
    parser.add_argument(
        "--docs-path",
        type=Path,
        default=Path(__file__).parent / "rag_docs",
        help="Path to markdown troubleshooting docs",
    )
    args = parser.parse_args()

    if args.report is not None:
        if not args.report.is_file():
            raise FileNotFoundError(f"Report not found: {args.report}")
        slm_input = build_input_from_report(args.report)
    elif args.text:
        slm_input = extract_relevant_log_lines(args.text)
    else:
        raise ValueError("Provide --report <path> or --text <raw log text>")

    answer, sources = run_rag(slm_input, args.docs_path)
    print("\n### LOCAL SLM DIAGNOSIS ###\n")
    print(answer)
    print(f"\nRetrieved sources: {', '.join(sources) if sources else 'none'}")


if __name__ == "__main__":
    main()
