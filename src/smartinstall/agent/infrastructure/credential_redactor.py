"""Redact sensitive tokens from command lines before logging (SEC-05)."""

from __future__ import annotations

import re

_SENSITIVE_PATTERNS = [
    re.compile(r"(/password:)(\S+)", re.IGNORECASE),
    re.compile(r"(/pwd:)(\S+)", re.IGNORECASE),
    re.compile(r"(-pw\s+)(\S+)", re.IGNORECASE),
    re.compile(r"(--token\s+)(\S+)", re.IGNORECASE),
    re.compile(r"(/p\s+)(\S+)", re.IGNORECASE),
]


def redact_command_line(command_line: str) -> str:
    redacted = command_line
    for pattern in _SENSITIVE_PATTERNS:
        redacted = pattern.sub(r"\1***REDACTED***", redacted)
    return redacted
