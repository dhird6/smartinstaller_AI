"""CLI wrapper for local SLM + RAG diagnosis."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Force UTF-8 output so LLM responses with unicode (arrows, bullets) don't crash
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from smartinstall.agent.slm.rag_engine import (
    RagDiagnosisConfig,
    build_input_from_report_path,
    default_rag_docs_path,
    diagnose_report,
    extract_relevant_log_lines,
    run_rag_diagnosis,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local SLM diagnosis from SmartInstall JSON.")
    parser.add_argument("--report", type=Path, help="Path to smartinstall_report.json")
    parser.add_argument("--text", type=str, help="Raw error text fallback")
    parser.add_argument("--docs-path", type=Path, default=default_rag_docs_path())
    parser.add_argument("--model", default="phi3:mini")
    parser.add_argument("--embedding-model", default="nomic-embed-text")
    args = parser.parse_args()

    config = RagDiagnosisConfig(
        docs_path=args.docs_path,
        llm_model=args.model,
        embedding_model=args.embedding_model,
    )

    if args.report is not None:
        diagnosis = diagnose_report(args.report, config)
        answer, sources, slm_input = diagnosis.answer, diagnosis.sources, diagnosis.prompt_input
    elif args.text:
        slm_input = extract_relevant_log_lines(args.text)
        diagnosis = run_rag_diagnosis(slm_input, config)
        answer, sources = diagnosis.answer, diagnosis.sources
    else:
        raise ValueError("Provide --report <path> or --text <raw log text>")

    print("\n### LOCAL SLM DIAGNOSIS ###\n")
    print(answer)
    print(f"\nRetrieved sources: {', '.join(sources) if sources else 'none'}")


if __name__ == "__main__":
    main()
