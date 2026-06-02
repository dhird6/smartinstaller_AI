"""Collector-related enums (data-model §3, §7, §8)."""

from enum import StrEnum


class EventLevel(StrEnum):
    UNKNOWN = "Unknown"
    CRITICAL = "Critical"
    ERROR = "Error"
    WARNING = "Warning"
    INFORMATION = "Information"
    VERBOSE = "Verbose"


class FSEventType(StrEnum):
    CREATED = "Created"
    MODIFIED = "Modified"
    DELETED = "Deleted"
    RENAMED = "Renamed"


class RegistryChangeType(StrEnum):
    KEY_ADDED = "KeyAdded"
    KEY_DELETED = "KeyDeleted"
    VALUE_ADDED = "ValueAdded"
    VALUE_MODIFIED = "ValueModified"
    VALUE_DELETED = "ValueDeleted"
