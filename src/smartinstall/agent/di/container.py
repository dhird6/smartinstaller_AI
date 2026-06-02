"""Dependency injection container (MAINT-05)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import structlog

from smartinstall.agent.infrastructure.config_provider import ConfigProvider, SmartInstallConfig
from smartinstall.agent.infrastructure.event_bus import EventBus
from smartinstall.agent.infrastructure.logging_setup import configure_logging
from smartinstall.agent.infrastructure.output_directory_manager import OutputDirectoryManager
from smartinstall.agent.orchestration.automated_run_orchestrator import AutomatedRunOrchestrator
from smartinstall.agent.orchestration.installation_agent import InstallationAgent
from smartinstall.agent.session.report_writer import ReportWriter
from smartinstall.agent.session.session_manager import SessionManager


@dataclass(slots=True)
class ServiceContainer:
    """Wired application services for the installation agent."""

    config: SmartInstallConfig
    config_provider: ConfigProvider
    logger: structlog.stdlib.BoundLogger
    event_bus: EventBus
    output_directory_manager: OutputDirectoryManager
    session_manager: SessionManager
    report_writer: ReportWriter
    installation_agent: InstallationAgent
    automated_run_orchestrator: AutomatedRunOrchestrator


def build_container(config_path: Path | None = None) -> ServiceContainer:
    config_provider = ConfigProvider(config_path)
    config = config_provider.load()
    logger = configure_logging(config)

    event_bus = EventBus()
    output_directory_manager = OutputDirectoryManager(config)
    report_writer = ReportWriter()
    session_manager = SessionManager(
        output_manager=output_directory_manager,
        event_bus=event_bus,
        report_writer=report_writer,
    )
    installation_agent = InstallationAgent(
        config=config,
        session_manager=session_manager,
        event_bus=event_bus,
    )
    automated_run_orchestrator = AutomatedRunOrchestrator(
        config=config,
        installation_agent=installation_agent,
    )

    recovered = session_manager.recover_incomplete_sessions()
    if recovered:
        logger.info("incomplete_sessions_recovered", count=recovered)

    return ServiceContainer(
        config=config,
        config_provider=config_provider,
        logger=logger,
        event_bus=event_bus,
        output_directory_manager=output_directory_manager,
        session_manager=session_manager,
        report_writer=report_writer,
        installation_agent=installation_agent,
        automated_run_orchestrator=automated_run_orchestrator,
    )
