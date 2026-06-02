"""Monitored installation orchestrator — run, detect failure, collect evidence."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path

import structlog

from smartinstall.agent.collectors.event_log_collector import EventLogCollector
from smartinstall.agent.collectors.installer_log_collector import InstallerLogCollector
from smartinstall.agent.collectors.msi_log_collector import MsiLogCollector
from smartinstall.agent.collectors.process_collector import ProcessCollector
from smartinstall.agent.collectors.wer_collector import WerCollector
from smartinstall.agent.detection.error_aggregator import build_error_entries
from smartinstall.agent.detection.failure_detector import FailureDetector
from smartinstall.agent.detection.outcome_refiner import refine_outcome
from smartinstall.agent.infrastructure.config_provider import SmartInstallConfig
from smartinstall.agent.infrastructure.event_bus import AgentEvent, EventBus
from smartinstall.agent.infrastructure.input_validator import validate_installer_path
from smartinstall.agent.runners.installer_runner import InstallerRunner
from smartinstall.agent.session.unified_report_writer import UnifiedReportWriter
from smartinstall.agent.session.session_manager import SessionManager
from smartinstall.core.enums.installation import InstallationOutcome, InstallerType
from smartinstall.core.enums.session import SessionStatus
from smartinstall.core.models.evidence import InstallerDetails
from smartinstall.core.models.installation_session import InstallationSession
from smartinstall.core.models.requests import StartSessionRequest
from smartinstall.core.models.unified_report import UNIFIED_REPORT_FILENAME
from smartinstall.core.results.api_error import ApiError
from smartinstall.core.results.result import Result
from smartinstall.rag.rag_pipeline import RagPipeline

_rag_pipeline: RagPipeline | None = None


def _get_rag_pipeline() -> RagPipeline:
    global _rag_pipeline
    if _rag_pipeline is None:
        _rag_pipeline = RagPipeline()
    return _rag_pipeline

logger = structlog.get_logger(__name__)


class InstallationAgent:
    """End-to-end monitored installation with failure detection and evidence collection."""

    def __init__(
        self,
        config: SmartInstallConfig,
        session_manager: SessionManager,
        event_bus: EventBus,
    ) -> None:
        self._config = config
        self._session_manager = session_manager
        self._event_bus = event_bus
        self._runner = InstallerRunner(config)
        self._failure_detector = FailureDetector()

    def run_monitored_installation(
        self,
        request: StartSessionRequest,
    ) -> Result[tuple[InstallationSession, object]]:
        """Returns (session, UnifiedInstallationReport) on success."""
        create = self._session_manager.create_session(request)
        if not create.success or create.value is None:
            return Result.fail(create.error)  # type: ignore[arg-type]

        session = create.value
        session_dir = Path(session.output_directory)
        installer_path = validate_installer_path(request.installer_path)
        application = request.product_name or installer_path.stem
        timeout = request.timeout_seconds or self._config.default_installer_timeout_seconds
        is_gui = _is_gui_installer(request.additional_args)

        event_collector = EventLogCollector(max_entries=self._config.max_event_log_entries)
        installer_log_collector = InstallerLogCollector(
            max_files=self._config.max_installer_log_files,
            max_depth=self._config.installer_log_search_depth,
        )
        msi_collector = MsiLogCollector(max_size_mb=self._config.max_msi_log_size_mb)
        wer_collector = WerCollector()
        process_collector = ProcessCollector(sample_interval_seconds=2.0)
        collection_errors: list[str] = []

        try:
            self._transition(session.session_id, SessionStatus.PRE_SNAPSHOTTING)
            event_collector.mark_session_start()
            installer_log_collector.mark_session_start()
            wer_collector.take_pre_snapshot()

            self._transition(session.session_id, SessionStatus.INSTALLING)
            self._event_bus.publish(
                AgentEvent.INSTALLER_LAUNCHED,
                {"sessionId": session.session_id},
            )

            run_result = self._runner.run(
                installer_path=installer_path,
                installer_type=session.installer_type,
                session_directory=session_dir,
                additional_args=request.additional_args,
                timeout_seconds=timeout,
                process_collector=process_collector,
                event_collector=event_collector,
            )

            self._event_bus.publish(
                AgentEvent.INSTALLER_EXITED,
                {"sessionId": session.session_id, "exitCode": run_result.exit_code},
            )

            self._transition(session.session_id, SessionStatus.POST_SNAPSHOTTING)
            event_collector.mark_session_end()
            installer_log_collector.mark_session_end()
            grace = self._config.gui_post_install_grace_seconds if is_gui else 5
            logger.info("post_install_grace_wait", seconds=grace)
            time.sleep(grace)

            event_logs = event_collector.collect()
            msi_logs = (
                msi_collector.parse(run_result.msi_verbose_log_path)
                if session.installer_type == InstallerType.MSI
                else msi_collector.parse(None)
            )
            wer = wer_collector.collect({run_result.pid})
            process = process_collector.finalize()
            installer_logs = installer_log_collector.collect(
                installer_path=installer_path,
                session_directory=session_dir,
                installer_stem=installer_path.stem,
                failure_timestamp=run_result.end_timestamp or _utc_now_iso(),
            )

            collection_errors.extend(event_logs.errors)
            collection_errors.extend(installer_logs.errors)
            if session.installer_type == InstallerType.MSI:
                collection_errors.extend(msi_logs.errors)
            collection_errors.extend(wer.errors)
            collection_errors.extend(process.errors)

            self._transition(session.session_id, SessionStatus.AGGREGATING)

            failure_timestamp = run_result.end_timestamp or _utc_now_iso()
            detection = self._failure_detector.analyze(
                run_result=run_result,
                event_logs=event_logs,
                msi_logs=msi_logs,
                installer_logs=installer_logs,
                wer=wer,
                process=process,
                application_name=application,
                installer_type=session.installer_type,
            )

            errors = build_error_entries(
                detection=detection,
                run_result=run_result,
                event_logs=event_logs,
                msi_logs=msi_logs,
                wer=wer,
                installer_logs=installer_logs,
                process=process,
                collection_errors=collection_errors,
                installer_type=session.installer_type,
                failure_timestamp=failure_timestamp,
                is_gui_installer=is_gui,
            )
            detection = refine_outcome(detection, errors, failure_timestamp=failure_timestamp)

            exit_desc, _ = self._runner.describe_exit(run_result.exit_code)
            duration = _duration_seconds(session.start_timestamp, run_result.end_timestamp)
            installer_details = InstallerDetails(
                installerName=installer_path.name,
                installerPath=str(installer_path),
                installerType=session.installer_type.value,
                processId=run_result.pid,
                parentProcessId=run_result.parent_pid,
                exitCode=run_result.exit_code,
                exitCodeDescription=exit_desc,
                executionDurationSeconds=duration,
                commandLine=run_result.command_line,
                stdoutPath=str(run_result.stdout_path) if run_result.stdout_path else None,
                stderrPath=str(run_result.stderr_path) if run_result.stderr_path else None,
                timedOut=run_result.timed_out,
            )

            unified = UnifiedReportWriter.build(
                session=session,
                application=application,
                detection=detection,
                installer_details=installer_details,
                errors=errors,
                event_logs=event_logs,
                msi_logs=msi_logs,
                wer=wer,
                process=process,
                installer_logs=installer_logs,
            )

            report_path = UnifiedReportWriter.write(
                unified,
                session_dir / UNIFIED_REPORT_FILENAME,
            )

            # Automatically diagnose failures with the local RAG pipeline (Phi-3 + ChromaDB)
            if detection.status != "SUCCESS":
                try:
                    import json as _json
                    rag = _get_rag_pipeline()
                    report_dict = _json.loads(report_path.read_text(encoding="utf-8"))
                    diagnosis = rag.diagnose(report_dict, session_id=session.session_id)
                    diag_path = session_dir / "rag_diagnosis.json"
                    diag_path.write_text(
                        _json.dumps(diagnosis.to_dict(), indent=2), encoding="utf-8"
                    )
                    logger.info(
                        "rag_diagnosis_written",
                        path=str(diag_path),
                        confidence=diagnosis.confidence,
                        root_cause=diagnosis.root_cause,
                    )
                except Exception as _rag_exc:  # noqa: BLE001
                    logger.warning("rag_diagnosis_skipped", reason=str(_rag_exc))

            outcome = _map_status_to_outcome(detection.status)
            finalize = self._session_manager.finalize_session(
                session.session_id,
                exit_code=run_result.exit_code,
                outcome=outcome,
                report_path=str(report_path),
            )
            if not finalize.success or finalize.value is None:
                return Result.fail(finalize.error)  # type: ignore[arg-type]

            self._event_bus.publish(
                AgentEvent.COLLECTION_COMPLETE,
                {"sessionId": session.session_id, "status": detection.status},
            )
            logger.info(
                "monitored_installation_complete",
                session_id=session.session_id,
                status=detection.status,
                report_path=str(report_path),
                error_count=len(errors),
            )
            return Result.ok((finalize.value, unified))
        except PermissionError as exc:
            logger.warning("installation_elevation_denied", session_id=session.session_id)
            self._session_manager.transition_state(session.session_id, SessionStatus.FAILED)
            return Result.fail(
                ApiError.create(
                    error_code="SESSION_INSUFFICIENT_PRIVILEGES",
                    message=str(exc),
                    component="InstallationAgent",
                    detail="UAC elevation was cancelled or denied",
                )
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("monitored_installation_failed", session_id=session.session_id)
            self._session_manager.transition_state(session.session_id, SessionStatus.FAILED)
            return Result.fail(
                ApiError.create(
                    error_code="AGENT_INSTALLATION_FAILED",
                    message=str(exc),
                    component="InstallationAgent",
                )
            )

    def _transition(self, session_id: str, state: SessionStatus) -> None:
        result = self._session_manager.transition_state(session_id, state)
        if not result.success:
            message = result.error.message if result.error else "State transition failed"
            raise RuntimeError(message)


def _map_status_to_outcome(status: str) -> InstallationOutcome:
    mapping = {
        "SUCCESS": InstallationOutcome.SUCCESS,
        "FAILED": InstallationOutcome.FAILURE,
        "CRASHED": InstallationOutcome.CRASHED,
        "TIMED_OUT": InstallationOutcome.TIMED_OUT,
        "PARTIAL": InstallationOutcome.PARTIAL,
    }
    return mapping.get(status, InstallationOutcome.UNKNOWN)


def _duration_seconds(start: str, end: str | None) -> float | None:
    if end is None:
        return None
    start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
    end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
    return max((end_dt - start_dt).total_seconds(), 0.0)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _is_gui_installer(additional_args: str | None) -> bool:
    if not additional_args:
        return True
    lowered = additional_args.lower()
    silent_tokens = ("/s", "/silent", "/verysilent", "/qn", "-silent", "--silent")
    return not any(token in lowered for token in silent_tokens)
