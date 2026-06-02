"""Automatic installer discovery from the installers/ repository."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from smartinstall.core.exceptions.validation import InvalidInputError

_INSTALLER_SUFFIXES = {".exe", ".msi"}


@dataclass(frozen=True, slots=True)
class DiscoveredInstaller:
    """Metadata for an installer package found in the repository."""

    path: Path
    file_name: str
    installer_type: str  # EXE | MSI
    size_bytes: int
    modified_timestamp: str

    @property
    def product_name(self) -> str:
        return self.path.stem


class InstallerDiscovery:
    """Scans the installers directory for .exe and .msi packages."""

    def __init__(self, installers_dir: Path) -> None:
        self._installers_dir = installers_dir.resolve()

    @property
    def installers_dir(self) -> Path:
        return self._installers_dir

    def list_installers(self) -> list[DiscoveredInstaller]:
        if not self._installers_dir.is_dir():
            return []

        discovered: list[DiscoveredInstaller] = []
        for entry in self._installers_dir.iterdir():
            if not entry.is_file():
                continue
            if entry.suffix.lower() not in _INSTALLER_SUFFIXES:
                continue
            stat = entry.stat()
            discovered.append(
                DiscoveredInstaller(
                    path=entry.resolve(),
                    file_name=entry.name,
                    installer_type="MSI" if entry.suffix.lower() == ".msi" else "EXE",
                    size_bytes=stat.st_size,
                    modified_timestamp=datetime.fromtimestamp(
                        stat.st_mtime, tz=timezone.utc
                    ).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
                    + "Z",
                )
            )

        discovered.sort(key=lambda item: item.path.stat().st_mtime, reverse=True)
        return discovered

    def select_latest(self) -> DiscoveredInstaller:
        installers = self.list_installers()
        if not installers:
            raise InvalidInputError(
                f"No installers found in {self._installers_dir}. "
                "Copy .exe or .msi files into the installers/ folder.",
                detail=str(self._installers_dir),
            )
        return installers[0]

    def select_by_name(self, name: str) -> DiscoveredInstaller:
        normalized = name.strip().lower()
        matches = [
            item
            for item in self.list_installers()
            if item.file_name.lower() == normalized
            or item.path.stem.lower() == normalized.replace(".exe", "").replace(".msi", "")
        ]
        if not matches:
            available = ", ".join(i.file_name for i in self.list_installers()) or "(none)"
            raise InvalidInputError(
                f"Installer not found: {name}",
                detail=f"Available: {available}",
            )
        return matches[0]
