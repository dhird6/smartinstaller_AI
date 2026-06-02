"""Unit tests for input validation (SEC-08)."""

import pytest

from smartinstall.core.exceptions.validation import InvalidInputError
from smartinstall.agent.infrastructure.input_validator import validate_installer_path


def test_rejects_path_traversal() -> None:
    with pytest.raises(InvalidInputError):
        validate_installer_path(r"C:\Temp\..\Windows\System32\calc.exe")


def test_requires_absolute_path() -> None:
    with pytest.raises(InvalidInputError):
        validate_installer_path("relative\\setup.exe")
