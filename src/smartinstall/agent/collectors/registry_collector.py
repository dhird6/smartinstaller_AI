"""Windows registry pre/post snapshot collector."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field

import structlog

from smartinstall.core.models.evidence import RegistryChangeEvidence

logger = structlog.get_logger(__name__)

_HIVE_MAP = {
    "HKLM": "HKEY_LOCAL_MACHINE",
    "HKCU": "HKEY_CURRENT_USER",
    "HKCR": "HKEY_CLASSES_ROOT",
    "HKU": "HKEY_USERS",
}


@dataclass(slots=True)
class RegistryCollectionResult:
    changes: list[RegistryChangeEvidence] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class RegistryCollector:
    """Captures registry value changes between pre-install and post-install snapshots."""

    def __init__(self, snapshot_keys: list[str], *, max_changes: int = 500) -> None:
        self._snapshot_keys = snapshot_keys
        self._max_changes = max_changes
        self._pre_snapshot: dict[str, dict[str, str]] | None = None

    def take_pre_snapshot(self) -> None:
        if sys.platform != "win32":
            return
        self._pre_snapshot = self._capture_all()

    def collect(self) -> RegistryCollectionResult:
        result = RegistryCollectionResult()
        if sys.platform != "win32":
            result.errors.append("Registry collector is only supported on Windows.")
            return result
        if self._pre_snapshot is None:
            self.take_pre_snapshot()

        post_snapshot = self._capture_all()
        changes = _diff_snapshots(self._pre_snapshot, post_snapshot)
        result.changes = changes[: self._max_changes]
        if len(changes) > self._max_changes:
            result.errors.append(
                f"Registry changes truncated to {self._max_changes} of {len(changes)}."
            )
        logger.info("registry_changes_collected", count=len(result.changes))
        return result

    def _capture_all(self) -> dict[str, dict[str, str]]:
        captured: dict[str, dict[str, str]] = {}
        for key_spec in self._snapshot_keys:
            try:
                captured.update(_read_registry_key_tree(key_spec))
            except OSError as exc:
                logger.warning("registry_snapshot_failed", key=key_spec, error=str(exc))
        return captured


def _diff_snapshots(
    before: dict[str, dict[str, str]],
    after: dict[str, dict[str, str]],
) -> list[RegistryChangeEvidence]:
    changes: list[RegistryChangeEvidence] = []
    all_keys = set(before) | set(after)
    for key_path in sorted(all_keys):
        before_values = before.get(key_path, {})
        after_values = after.get(key_path, {})
        value_names = set(before_values) | set(after_values)
        for value_name in sorted(value_names):
            old = before_values.get(value_name)
            new = after_values.get(value_name)
            if old == new:
                continue
            if old is None:
                change_type = "added"
            elif new is None:
                change_type = "removed"
            else:
                change_type = "modified"
            hive, subkey = _split_hive_and_subkey(key_path)
            changes.append(
                RegistryChangeEvidence(
                    hive=hive,
                    keyPath=subkey,
                    valueName=value_name,
                    changeType=change_type,
                    beforeValue=old,
                    afterValue=new,
                )
            )
    return changes


def _read_registry_key_tree(key_spec: str) -> dict[str, dict[str, str]]:
    import winreg

    hive_name, subkey = _parse_key_spec(key_spec)
    hive = getattr(winreg, _HIVE_MAP[hive_name])
    result: dict[str, dict[str, str]] = {}
    _read_key_recursive(winreg, hive, hive_name, subkey, result, depth=0, max_depth=2)
    return result


def _read_key_recursive(
    winreg_module,
    hive,
    hive_name: str,
    subkey: str,
    output: dict[str, dict[str, str]],
    *,
    depth: int,
    max_depth: int,
) -> None:
    full_path = f"{hive_name}\\{subkey}"
    try:
        with winreg_module.OpenKey(hive, subkey, 0, winreg_module.KEY_READ) as key:
            values = _read_values(winreg_module, key)
            if values:
                output[full_path] = values
            if depth >= max_depth:
                return
            index = 0
            while True:
                try:
                    child_name = winreg_module.EnumKey(key, index)
                except OSError:
                    break
                index += 1
                child_subkey = f"{subkey}\\{child_name}" if subkey else child_name
                _read_key_recursive(
                    winreg_module,
                    hive,
                    hive_name,
                    child_subkey,
                    output,
                    depth=depth + 1,
                    max_depth=max_depth,
                )
    except OSError:
        return


def _read_values(winreg_module, key) -> dict[str, str]:
    values: dict[str, str] = {}
    index = 0
    while True:
        try:
            name, value, _value_type = winreg_module.EnumValue(key, index)
        except OSError:
            break
        index += 1
        key_name = name or "(default)"
        values[key_name] = _stringify_registry_value(value)
    return values


def _stringify_registry_value(value: object) -> str:
    if isinstance(value, bytes):
        return value[:200].hex()
    if isinstance(value, (list, tuple)):
        return ", ".join(str(item) for item in value[:20])
    return str(value)[:2000]


def _parse_key_spec(key_spec: str) -> tuple[str, str]:
    normalized = key_spec.strip().replace("/", "\\")
    parts = [part for part in normalized.split("\\") if part]
    if len(parts) < 2:
        raise ValueError(f"Invalid registry key spec: {key_spec}")
    hive = parts[0].upper()
    if hive not in _HIVE_MAP:
        raise ValueError(f"Unsupported registry hive: {hive}")
    return hive, "\\".join(parts[1:])


def _split_hive_and_subkey(full_path: str) -> tuple[str, str]:
    parts = full_path.split("\\", 1)
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[1]

