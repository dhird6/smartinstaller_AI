"""Structured logging framework (MAINT-03, NFR structured JSON to agent.log)."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import structlog

from smartinstall.agent.infrastructure.config_provider import LogLevel, SmartInstallConfig


def configure_logging(config: SmartInstallConfig) -> structlog.stdlib.BoundLogger:
    """Configure structlog with JSON file sink and human-readable console sink."""
    log_path = config.agent_log_path
    log_path.parent.mkdir(parents=True, exist_ok=True)

    level = _map_log_level(config.log_level)

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    json_formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
        foreign_pre_chain=shared_processors,
    )
    console_formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.dev.ConsoleRenderer(colors=False),
        foreign_pre_chain=shared_processors,
    )

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(json_formatter)

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(level)
    console_handler.setFormatter(console_formatter)

    root = logging.getLogger("smartinstall")
    root.handlers.clear()
    root.setLevel(level)
    root.addHandler(file_handler)
    root.addHandler(console_handler)
    root.propagate = False

    return structlog.get_logger("smartinstall.agent")


def _map_log_level(level: LogLevel) -> int:
    mapping = {
        LogLevel.VERBOSE: logging.DEBUG,
        LogLevel.DEBUG: logging.DEBUG,
        LogLevel.INFO: logging.INFO,
        LogLevel.WARNING: logging.WARNING,
        LogLevel.ERROR: logging.ERROR,
    }
    return mapping[level]
