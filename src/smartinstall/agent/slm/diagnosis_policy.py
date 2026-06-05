"""When to run SLM diagnosis and which errors are actionable for end users."""

from __future__ import annotations

from smartinstall.core.models.unified_report import ReportErrorEntry, UnifiedInstallationReport

_INTERNAL_CODES = frozenset(
    {
        "COLLECTOR_ERROR",
        "REPORT_WRITE_FAILURE",
        "AGENT_INSTALLATION_FAILED",
        "AGENT_PASSIVE_MONITORING_FAILED",
        "SESSION_INSUFFICIENT_PRIVILEGES",
    }
)

_INTERNAL_CODE_PREFIXES = ("AGENT_", "SESSION_", "BRIDGE_")


def is_internal_monitoring_error(error: ReportErrorEntry) -> bool:
    """Errors from Smart Installer collectors, not the product being installed."""
    if error.category == "collection":
        return True
    if error.code in _INTERNAL_CODES:
        return True
    if any(error.code.startswith(prefix) for prefix in _INTERNAL_CODE_PREFIXES):
        return True
    lowered = error.message.lower()
    if "processcollector" in lowered or "smartinstall" in lowered and "collector" in lowered:
        return True
    if "object has no attribute" in lowered and error.category == "collection":
        return True
    return False


def actionable_install_errors(errors: list[ReportErrorEntry]) -> list[ReportErrorEntry]:
    """Errors that relate to the monitored installer, not the monitoring agent."""
    actionable: list[ReportErrorEntry] = []
    for error in errors:
        if is_internal_monitoring_error(error):
            continue
        if error.severity == "info":
            continue
        actionable.append(error)
    return actionable


def should_run_slm_diagnosis(report: UnifiedInstallationReport) -> bool:
    """
    Run local SLM only when the monitored installation needs user-facing troubleshooting.

    Successful installs with only internal collector warnings must not trigger SLM.
    """
    outcome = report.status.installation_outcome.lower()
    if outcome in {"failed", "failure", "error", "crashed", "timedout", "timed_out"}:
        return True

    actionable = actionable_install_errors(report.errors)
    if not actionable:
        return False

    if outcome in {"success", "completed"}:
        severe = [e for e in actionable if e.severity == "error"]
        return len(severe) > 0

    return len(actionable) > 0


def input_targets_smartinstall_ai_stack(text: str) -> bool:
    """True when evidence is about Smart Installer's own AI stack (Ollama/RAG), not a product install."""
    lowered = text.lower()
    markers = (
        "ollama",
        "phi3",
        "nomic-embed",
        "could not connect to a running ollama",
        "ollama.exe",
        "slm diagnosis failed",
        "rag_engine",
        "chromadb",
    )
    return any(marker in lowered for marker in markers)
