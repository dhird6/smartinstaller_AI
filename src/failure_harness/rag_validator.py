"""Validate RAG troubleshooting responses against expected failure guidance."""

from __future__ import annotations

import re

from failure_harness.models import InjectedFailureSpec, RagValidationResult, ScenarioConfig
from smartinstall.agent.slm.rag_engine import RagDiagnosisConfig, diagnose_report, run_rag_diagnosis
from smartinstall.core.models.unified_report import UnifiedInstallationReport


class RagValidator:
    """Validate RAG retrieval relevance and recommendation quality."""

    def validate_from_report(
        self,
        report_path: str,
        scenario: ScenarioConfig,
        *,
        docs_path: str | None = None,
        llm_model: str = "phi3:mini",
        embedding_model: str = "nomic-embed-text",
        min_score: float | None = None,
    ) -> RagValidationResult:
        from pathlib import Path

        from smartinstall.agent.slm.rag_engine import default_rag_docs_path

        config = RagDiagnosisConfig(
            docs_path=Path(docs_path) if docs_path else default_rag_docs_path(),
            llm_model=llm_model,
            embedding_model=embedding_model,
        )
        threshold = min_score if min_score is not None else scenario.min_rag_relevance_score

        try:
            diagnosis = diagnose_report(Path(report_path), config)
            answer = diagnosis.answer
            sources = diagnosis.sources
        except Exception as exc:  # noqa: BLE001 — capture RAG failures in validation report
            return RagValidationResult(
                success=False,
                relevanceScore=0.0,
                matchedKeywords=[],
                expectedKeywords=self._collect_expected_keywords(scenario),
                sources=[],
                answerPreview=f"RAG diagnosis failed: {exc}",
            )

        expected = self._collect_expected_keywords(scenario)
        matched, score = self._score_relevance(answer, sources, expected)

        return RagValidationResult(
            success=score >= threshold and len(answer.strip()) > 20,
            relevanceScore=round(score, 3),
            matchedKeywords=matched,
            expectedKeywords=expected,
            sources=sources,
            answerPreview=answer[:500],
        )

    def validate_from_text(
        self,
        error_text: str,
        expected_keywords: list[str],
        *,
        docs_path: str | None = None,
        llm_model: str = "phi3:mini",
        embedding_model: str = "nomic-embed-text",
        min_score: float = 0.3,
    ) -> RagValidationResult:
        from pathlib import Path

        from smartinstall.agent.slm.rag_engine import default_rag_docs_path, run_rag_diagnosis

        config = RagDiagnosisConfig(
            docs_path=Path(docs_path) if docs_path else default_rag_docs_path(),
            llm_model=llm_model,
            embedding_model=embedding_model,
        )

        try:
            diagnosis = run_rag_diagnosis(error_text, config)
            answer = diagnosis.answer
            sources = diagnosis.sources
        except Exception as exc:  # noqa: BLE001
            return RagValidationResult(
                success=False,
                relevanceScore=0.0,
                matchedKeywords=[],
                expectedKeywords=expected_keywords,
                sources=[],
                answerPreview=str(exc),
            )

        matched, score = self._score_relevance(answer, sources, expected_keywords)
        return RagValidationResult(
            success=score >= min_score,
            relevanceScore=round(score, 3),
            matchedKeywords=matched,
            expectedKeywords=expected_keywords,
            sources=sources,
            answerPreview=answer[:500],
        )

    def validate_detection_accuracy(
        self,
        report: UnifiedInstallationReport,
        scenario: ScenarioConfig,
    ) -> tuple[bool, str]:
        """Check Smart Installer detected failure when expected."""
        if not scenario.expect_smart_installer_detection:
            return True, "Detection not required for this scenario"

        outcome = report.status.installation_outcome.lower()
        has_errors = bool(report.errors)
        failed = outcome in {"failure", "failed", "error", "crashed", "timedout"} or has_errors

        if failed:
            return True, f"Failure detected (outcome={outcome}, errors={len(report.errors)})"
        return False, f"Expected failure detection but got outcome={outcome}"

    def _collect_expected_keywords(self, scenario: ScenarioConfig) -> list[str]:
        keywords: list[str] = []
        for failure in scenario.failures:
            keywords.extend(failure.expected_rag_keywords)
            if not failure.expected_rag_keywords:
                from failure_harness.categories import get_failure_template

                try:
                    template = get_failure_template(failure.category, failure.sub_type)
                    keywords.extend(template.default_keywords)
                except KeyError:
                    pass
        return list(dict.fromkeys(kw.lower() for kw in keywords if kw))

    def _score_relevance(
        self,
        answer: str,
        sources: list[str],
        expected_keywords: list[str],
    ) -> tuple[list[str], float]:
        if not expected_keywords:
            return [], 1.0 if len(answer.strip()) > 50 else 0.5

        combined = f"{answer} {' '.join(sources)}".lower()
        matched = [kw for kw in expected_keywords if kw.lower() in combined or self._fuzzy_match(kw, combined)]

        if not matched:
            matched = [kw for kw in expected_keywords if self._word_overlap(kw, combined)]

        score = len(matched) / len(expected_keywords) if expected_keywords else 0.0
        if len(answer.strip()) > 100:
            score = min(1.0, score + 0.15)
        if sources:
            score = min(1.0, score + 0.1)

        return matched, score

    @staticmethod
    def _fuzzy_match(keyword: str, text: str) -> bool:
        pattern = re.escape(keyword).replace(r"\ ", r"[\s_-]+")
        return bool(re.search(pattern, text, re.IGNORECASE))

    @staticmethod
    def _word_overlap(keyword: str, text: str) -> bool:
        parts = re.split(r"[\s_-]+", keyword.lower())
        return any(part in text for part in parts if len(part) > 3)
