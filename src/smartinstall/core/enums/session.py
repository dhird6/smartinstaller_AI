"""Session lifecycle enums (data-model §1)."""

from enum import StrEnum


class SessionStatus(StrEnum):
    INITIALIZING = "Initializing"
    PRE_SNAPSHOTTING = "PreSnapshotting"
    INSTALLING = "Installing"
    POST_SNAPSHOTTING = "PostSnapshotting"
    AGGREGATING = "Aggregating"
    COMPLETED = "Completed"
    FAILED = "Failed"
    INCOMPLETE = "Incomplete"
    TIMED_OUT = "TimedOut"
