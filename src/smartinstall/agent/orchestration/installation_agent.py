"""Monitored installation orchestrator — run, detect failure, collect evidence."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path

import structlog

from smartinstall.agent.collectors.event_log_collector import EventLogCollector
from smartinstall.agent.collectors.filesystem_collector import FilesystemCollector
from smartinstall.agent.collectors.installer_log_collector import InstallerLogCollector
from smartinstall.agent.collectors.registry_collector import RegistryCollector
from smartinstall.agent.collectors.msi_log_collector import MsiLogCollector
from smartinstall.agent.collectors.process_collector import ProcessCollector
from smartinstall.agent.collectors.wer_collector import WerCollector
from smartinstall.agent.detection.error_aggregator import build_error_entries
from smartinstall.agent.detection.failure_detector import FailureDetector
from smartinstall.agent.detection.outcome_refiner import refine_outcome
from smartinstall.agent.infrastructure.config_provider import SmartInstallConfig
from smartinstall.agent.infrastructure.event_bus import AgentEvent, EventBus
from smartinstall.agent.infrastructure.input_validator import validate_installer_path
from smartinstall.agent.detection.installer_process_detector import DetectedInstallerProcess
from smartinstall.agent.runners.installer_runner import InstallerRunner
from smartinstall.agent.runners.process_attach_runner import ProcessAttachRunner
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
        self._attach_runner = ProcessAttachRunner()
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
        registry_collector = RegistryCollector(self._config.registry_snapshot_keys)
        filesystem_collector = FilesystemCollector(
            self._config.monitored_filesystem_paths,
            max_events=self._config.max_filesystem_events,
        )
        collection_errors: list[str] = []

        try:
            self._transition(session.session_id, SessionStatus.PRE_SNAPSHOTTING)
            event_collector.mark_session_start()
            installer_log_collector.mark_session_start()
            registry_collector.take_pre_snapshot()
            filesystem_collector.take_pre_snapshot()
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

            result = self._complete_monitored_run(
                session=session,
                session_dir=session_dir,
                installer_path=installer_path,
                application=application,
                is_gui=is_gui,
                run_result=run_result,
                event_collector=event_collector,
                installer_log_collector=installer_log_collector,
                msi_collector=msi_collector,
                wer_collector=wer_collector,
                process_collector=process_collector,
                registry_collector=registry_collector,
                filesystem_collector=filesystem_collector,
                collection_errors=collection_errors,
            )
            if result.success and result.value is not None:
                _, unified = result.value
                logger.info(
                    "monitored_installation_complete",
                    session_id=session.session_id,
                    status=unified.status.installation_outcome,
                    error_count=len(unified.errors),
                )
            return result
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

    def run_passive_monitoring(
        self,
        request: StartSessionRequest,
        detected: DetectedInstallerProcess,
        *,
        monitor_pid: int | None = None,
    ) -> Result[tuple[InstallationSession, object]]:
        """Monitor an installer already running on the system (automatic mode)."""
        create = self._session_manager.create_session(request)
        if not create.success or create.value is None:
            return Result.fail(create.error)  # type: ignore[arg-type]

        session = create.value
        session_dir = Path(session.output_directory)
        path_candidate = detected.installer_path or Path(request.installer_path)
        installer_path = validate_installer_path(str(path_candidate))
        attach_pid = monitor_pid or detected.monitor_pid or detected.pid
        application = request.product_name or installer_path.stem
        timeout = request.timeout_seconds or self._config.default_installer_timeout_seconds
        is_gui = True
        command_line = detected.command_line or str(installer_path)

        self._event_bus.publish(
            AgentEvent.INSTALLER_DETECTED,
            {
                "sessionId": session.session_id,
                "pid": attach_pid,
                "installerName": installer_path.name,
                "elevationDetected": detected.elevation_detected,
                "viaMsiexec": detected.via_msiexec,
                "chainSummary": detected.chain_summary,
            },
        )

        event_collector = EventLogCollector(max_entries=self._config.max_event_log_entries)
        installer_log_collector = InstallerLogCollector(
            max_files=self._config.max_installer_log_files,
            max_depth=self._config.installer_log_search_depth,
        )
        msi_collector = MsiLogCollector(max_size_mb=self._config.max_msi_log_size_mb)
        wer_collector = WerCollector()
        process_collector = ProcessCollector(sample_interval_seconds=2.0)
        registry_collector = RegistryCollector(self._config.registry_snapshot_keys)
        filesystem_collector = FilesystemCollector(
            self._config.monitored_filesystem_paths,
            max_events=self._config.max_filesystem_events,
        )
        collection_errors: list[str] = []

        def _emit_stage(stage: str) -> None:
            self._event_bus.publish(
                AgentEvent.INSTALL_STAGE_CHANGED,
                {"sessionId": session.session_id, "stage": stage},
            )

        def _emit_log(line: str) -> None:
            self._event_bus.publish(
                AgentEvent.LIVE_LOG_LINE,
                {"sessionId": session.session_id, "line": line},
            )

        try:
            self._transition(session.session_id, SessionStatus.PRE_SNAPSHOTTING)
            _emit_stage("Pre-snapshot")
            event_collector.mark_session_start()
            installer_log_collector.mark_session_start()
            registry_collector.take_pre_snapshot()
            filesystem_collector.take_pre_snapshot()
            wer_collector.take_pre_snapshot()

            self._transition(session.session_id, SessionStatus.INSTALLING)
            self._event_bus.publish(
                AgentEvent.INSTALLER_LAUNCHED,
                {
                    "sessionId": session.session_id,
                    "mode": "passive",
                    "pid": attach_pid,
                    "installerName": installer_path.name,
                    "installerPath": str(installer_path),
                    "startedAt": session.start_timestamp,
                    "elevationDetected": detected.elevation_detected,
                    "viaMsiexec": detected.via_msiexec,
                    "chainSummary": detected.chain_summary,
                },
            )
            stage = "Monitoring external installer"
            if detected.via_msiexec:
                stage = "Monitoring MSI installation (msiexec)"
            if detected.elevation_detected:
                stage += " — UAC elevated"
            _emit_stage(stage)

            run_result = self._attach_runner.attach_and_wait(
                root_pid=attach_pid,
                installer_path=installer_path,
                installer_type=session.installer_type,
                session_directory=session_dir,
                command_line=command_line,
                timeout_seconds=timeout,
                process_collector=process_collector,
                event_collector=event_collector,
                on_stage=_emit_stage,
                on_log_line=_emit_log,
            )

            return self._complete_monitored_run(
                session=session,
                session_dir=session_dir,
                installer_path=installer_path,
                application=application,
                is_gui=is_gui,
                run_result=run_result,
                event_collector=event_collector,
                installer_log_collector=installer_log_collector,
                msi_collector=msi_collector,
                wer_collector=wer_collector,
                process_collector=process_collector,
                registry_collector=registry_collector,
                filesystem_collector=filesystem_collector,
                collection_errors=collection_errors,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("passive_monitoring_failed", session_id=session.session_id)
            self._session_manager.transition_state(session.session_id, SessionStatus.FAILED)
            return Result.fail(
                ApiError.create(
                    error_code="AGENT_PASSIVE_MONITORING_FAILED",
                    message=str(exc),
                    component="InstallationAgent",
                )
            )

    def _complete_monitored_run(
        self,
        *,
        session: InstallationSession,
        session_dir: Path,
        installer_path: Path,
        application: str,
        is_gui: bool,
        run_result: object,
        event_collector: EventLogCollector,
        installer_log_collector: InstallerLogCollector,
        msi_collector: MsiLogCollector,
        wer_collector: WerCollector,
        process_collector: ProcessCollector,
        registry_collector: RegistryCollector,
        filesystem_collector: FilesystemCollector,
        collection_errors: list[str],
    ) -> Result[tuple[InstallationSession, object]]:
        from smartinstall.agent.runners.installer_runner import InstallerRunResult

        assert isinstance(run_result, InstallerRunResult)

        self._event_bus.publish(
            AgentEvent.INSTALLER_EXITED,
            {"sessionId": session.session_id, "exitCode": run_result.exit_code},
        )

        self._transition(session.session_id, SessionStatus.POST_SNAPSHOTTING)
        self._event_bus.publish(
            AgentEvent.INSTALL_STAGE_CHANGED,
            {"sessionId": session.session_id, "stage": "Post-snapshot"},
        )
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
        registry = registry_collector.collect()
        filesystem = filesystem_collector.collect()

        collection_errors.extend(event_logs.errors)
        collection_errors.extend(registry.errors)
        collection_errors.extend(filesystem.errors)
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
            registry=registry,
            filesystem=filesystem,
            process=process,
            collection_errors=collection_errors,
            installer_type=session.installer_type,
            failure_timestamp=failure_timestamp,
            is_gui_installer=is_gui,
        )
        detection = refine_outcome(detection, errors, failure_timestamp=failure_timestamp)

        if errors:
            top = errors[0]
            self._event_bus.publish(
                AgentEvent.INSTALLATION_ERROR_DETECTED,
                {
                    "sessionId": session.session_id,
                    "code": top.code,
                    "message": top.message,
                    "category": top.category,
                },
            )

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
            registry=registry,
            filesystem=filesystem,
        )

        report_path = UnifiedReportWriter.write(
            unified,
            session_dir / UNIFIED_REPORT_FILENAME,
        )

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
        return Result.ok((finalize.value, unified))

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
