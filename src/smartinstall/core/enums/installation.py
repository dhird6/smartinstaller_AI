"""Installer and outcome enums (data-model §1)."""

from enum import StrEnum


class InstallerType(StrEnum):
    EXE = "EXE"
    MSI = "MSI"
    UNKNOWN = "Unknown"


class InstallationOutcome(StrEnum):
    SUCCESS = "Success"
    FAILURE = "Failure"
    PARTIAL = "Partial"
    CRASHED = "Crashed"
    TIMED_OUT = "TimedOut"
    UNKNOWN = "Unknown"
