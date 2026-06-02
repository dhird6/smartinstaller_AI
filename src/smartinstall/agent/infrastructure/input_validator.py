"""Caller input validation (SEC-08)."""

from __future__ import annotations

import re
from pathlib import Path

from smartinstall.core.enums.installation import InstallerType
from smartinstall.core.exceptions.validation import InvalidInputError

_TRAVERSAL_PATTERN = re.compile(r"\.\.[/\\]")
_ALLOWED_INSTALLER_EXTENSIONS = {".exe", ".msi", ".msix"}


def validate_installer_path(installer_path: str) -> Path:
    if _TRAVERSAL_PATTERN.search(installer_path):
        raise InvalidInputError("Path traversal sequences are not allowed in installerPath")

    path = Path(installer_path)
    if not path.is_absolute():
        raise InvalidInputError("installerPath must be an absolute path", detail=str(path))

    return path


def validate_optional_output_root(output_directory: str | None) -> Path | None:
    if output_directory is None:
        return None
    if _TRAVERSAL_PATTERN.search(output_directory):
        raise InvalidInputError("Path traversal sequences are not allowed in outputDirectory")
    path = Path(output_directory)
    if not path.is_absolute():
        raise InvalidInputError("outputDirectory must be an absolute path", detail=str(path))
    return path


def validate_caller_tag(caller_tag: str | None) -> None:
    if caller_tag is None:
        return
    if len(caller_tag) > 500:
        raise InvalidInputError("callerTag exceeds maximum length of 500 characters")
    if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", caller_tag):
        raise InvalidInputError("callerTag contains invalid control characters")


def detect_installer_type(installer_path: Path, explicit: InstallerType | None) -> InstallerType:
    if explicit is not None and explicit is not InstallerType.UNKNOWN:
        return explicit
    suffix = installer_path.suffix.lower()
    if suffix == ".msi":
        return InstallerType.MSI
    if suffix == ".exe":
        return InstallerType.EXE
    if suffix in _ALLOWED_INSTALLER_EXTENSIONS:
        return InstallerType.UNKNOWN
    raise InvalidInputError(
        f"Unsupported installer extension: {suffix}",
        detail="Allowed: .exe, .msi",
    )
