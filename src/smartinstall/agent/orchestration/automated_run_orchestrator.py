"""One-command automated installer workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import structlog

from smartinstall.agent.intake.installer_discovery import DiscoveredInstaller, InstallerDiscovery
from smartinstall.agent.intake.report_publisher import ReportPublisher
from smartinstall.agent.infrastructure.config_provider import SmartInstallConfig
from smartinstall.agent.infrastructure.project_paths import ensure_project_layout
from smartinstall.agent.orchestration.installation_agent import InstallationAgent
from smartinstall.core.enums.installation import InstallerType
from smartinstall.core.exceptions.base import SmartInstallError
from smartinstall.core.models.installation_session import InstallationSession
from smartinstall.core.models.requests import StartSessionRequest
from smartinstall.core.models.unified_report import UnifiedInstallationReport
from smartinstall.core.results.api_error import ApiError
from smartinstall.core.results.result import Result

logger = structlog.get_logger(__name__)


@dataclass(slots=True)
class AutomatedRunResult:
    session: InstallationSession
    discovered: DiscoveredInstaller
    report: UnifiedInstallationReport
    report_path: Path
    workflow_status: str


@dataclass(slots=True)
class BatchRunResult:
    runs: list[AutomatedRunResult] = field(default_factory=list)
    failures: int = 0


class AutomatedRunOrchestrator:
    """
    End-to-end workflow: discover → install → monitor → publish one JSON report.

    User workflow: copy installer to installers/, run `smartinstall run`.
    """

    def __init__(
        self,
        config: SmartInstallConfig,
        installation_agent: InstallationAgent,
    ) -> None:
        self._config = config
        self._installation_agent = installation_agent
        ensure_project_layout(
            installers_dir=config.installers_dir,
            reports_dir=config.reports_dir,
            logs_dir=config.logs_dir,
            sessions_dir=config.output_root,
        )
        self._discovery = InstallerDiscovery(config.installers_dir)
        self._publisher = ReportPublisher(config.reports_dir)

    def run(
        self,
        *,
        installer_name: str | None = None,
        product_name: str | None = None,
        caller_tag: str | None = None,
        additional_args: str | None = None,
        timeout_seconds: int | None = None,
    ) -> Result[AutomatedRunResult]:
        try:
            discovered = (
                self._discovery.select_by_name(installer_name)
                if installer_name
                else self._discovery.select_latest()
            )
            logger.info(
                "installer_discovered",
                file=discovered.file_name,
                path=str(discovered.path),
                mode="specific" if installer_name else "latest",
            )

            request = StartSessionRequest(
                installerPath=str(discovered.path),
                installerType=InstallerType(discovered.installer_type),
                productName=product_name or discovered.product_name,
                callerTag=caller_tag or "automated-run",
                outputDirectory=str(self._config.output_root),
                additionalArgs=additional_args,
                timeoutSeconds=timeout_seconds or self._config.default_installer_timeout_seconds,
            )

            install_result = self._installation_agent.run_monitored_installation(request)
            if not install_result.success or install_result.value is None:
                return Result.fail(
                    install_result.error
                    or ApiError.create(
                        error_code="AUTOMATED_RUN_FAILED",
                        message="Installation workflow failed",
                        component="AutomatedRunOrchestrator",
                    )
                )

            session, unified = install_result.value
            application = request.product_name or discovered.product_name
            report_path = self._publisher.publish(unified, application_name=application)
            workflow_status = unified.status.installation_outcome

            logger.info(
                "automated_run_complete",
                session_id=session.session_id,
                report=str(report_path),
                status=workflow_status,
                errors=len(unified.errors),
            )

            return Result.ok(
                AutomatedRunResult(
                    session=session,
                    discovered=discovered,
                    report=unified,
                    report_path=report_path,
                    workflow_status=workflow_status,
                )
            )
        except SmartInstallError as exc:
            return Result.fail(ApiError.from_exception(exc))

    def run_all(
        self,
        *,
        caller_tag: str | None = None,
        additional_args: str | None = None,
        timeout_seconds: int | None = None,
        stop_on_failure: bool = False,
    ) -> Result[BatchRunResult]:
        installers = self._discovery.list_installers()
        if not installers:
            return Result.fail(
                ApiError.create(
                    error_code="NO_INSTALLERS_FOUND",
                    message="No installers in repository",
                    component="AutomatedRunOrchestrator",
                    detail=str(self._discovery.installers_dir),
                )
            )

        batch = BatchRunResult()
        for item in reversed(installers):
            result = self.run(
                installer_name=item.file_name,
                caller_tag=caller_tag,
                additional_args=additional_args,
                timeout_seconds=timeout_seconds,
            )
            if not result.success or result.value is None:
                batch.failures += 1
                if stop_on_failure:
                    return Result.fail(
                        result.error
                        or ApiError.create(
                            error_code="BATCH_RUN_ABORTED",
                            message="Batch run stopped on failure",
                            component="AutomatedRunOrchestrator",
                        )
                    )
                continue

            batch.runs.append(result.value)
            if result.value.workflow_status not in {"Success"}:
                batch.failures += 1
                if stop_on_failure:
                    break

        return Result.ok(batch)
