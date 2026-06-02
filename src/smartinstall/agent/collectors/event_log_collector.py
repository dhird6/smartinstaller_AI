"""Windows Event Log collector with live polling during installation."""

from __future__ import annotations

import subprocess
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import structlog

from smartinstall.core.models.evidence import EventLogEvidence

logger = structlog.get_logger(__name__)

_LEVEL_NAMES = {
    1: "Critical",
    2: "Error",
    3: "Warning",
    4: "Information",
    5: "Verbose",
}


@dataclass(slots=True)
class EventLogCollectionResult:
    entries: list[EventLogEvidence] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    logs_scanned: list[str] = field(default_factory=list)
    logs_skipped: list[str] = field(default_factory=list)


class EventLogCollector:
    """Captures Application, System, and Setup events during the install window."""

    TARGET_LOGS = ("Application", "System", "Setup")

    def __init__(self, max_entries: int = 5000) -> None:
        self._max_entries = max_entries
        self._session_start: datetime | None = None
        self._session_end: datetime | None = None
        self._live_entries: list[EventLogEvidence] = []
        self._live_lock = threading.Lock()
        self._seen_keys: set[tuple[str, int, int]] = set()

    def mark_session_start(self) -> None:
        self._session_start = datetime.now(timezone.utc)

    def mark_session_end(self) -> None:
        self._session_end = datetime.now(timezone.utc)

    def poll_live(self) -> None:
        """Called periodically while installer runs to capture GUI-time errors."""
        if self._session_start is None:
            return
        end = datetime.now(timezone.utc)
        start = self._session_start - timedelta(seconds=30)
        batch = self._collect_all_logs(start, end)
        with self._live_lock:
            for entry in batch:
                key = (entry.log_name, entry.record_id or 0, entry.event_id)
                if key in self._seen_keys:
                    continue
                self._seen_keys.add(key)
                self._live_entries.append(entry)

    def collect(self) -> EventLogCollectionResult:
        if self._session_start is None:
            self._session_start = datetime.now(timezone.utc)
        end = (self._session_end or datetime.now(timezone.utc)) + timedelta(seconds=60)
        start = self._session_start - timedelta(seconds=30)

        result = EventLogCollectionResult()
        final_batch = self._collect_all_logs(start, end)

        with self._live_lock:
            merged = list(self._live_entries)
        merged.extend(final_batch)

        deduped: list[EventLogEvidence] = []
        local_seen: set[tuple[str, int, int]] = set()
        for entry in merged:
            key = (entry.log_name, entry.record_id or 0, entry.event_id)
            if key in local_seen:
                continue
            local_seen.add(key)
            deduped.append(entry)

        deduped.sort(key=lambda item: item.timestamp)
        if len(deduped) > self._max_entries:
            deduped = deduped[-self._max_entries :]
            result.errors.append(f"Event log truncated to {self._max_entries} entries")

        result.entries = deduped
        return result

    def _collect_all_logs(self, start: datetime, end: datetime) -> list[EventLogEvidence]:
        entries: list[EventLogEvidence] = []
        wevtutil_entries = _collect_via_wevtutil(start, end, self.TARGET_LOGS)
        if wevtutil_entries:
            return wevtutil_entries

        try:
            import win32evtlog  # type: ignore[import-untyped]
        except ImportError:
            return entries

        for log_name in self.TARGET_LOGS:
            try:
                chunk = self._read_log_win32(win32evtlog, log_name, start, end)
                entries.extend(chunk)
            except Exception as exc:  # noqa: BLE001
                logger.warning("event_log_skipped", log=log_name, error=str(exc))
        return entries

    def _read_log_win32(self, win32evtlog, log_name: str, start, end) -> list[EventLogEvidence]:  # noqa: ANN001
        try:
            import win32evtlogutil  # type: ignore[import-untyped]
        except ImportError:
            win32evtlogutil = None  # type: ignore[assignment]

        hand = win32evtlog.OpenEventLog(None, log_name)
        flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
        entries: list[EventLogEvidence] = []
        try:
            while True:
                events = win32evtlog.ReadEventLog(hand, flags, 0)
                if not events:
                    break
                for event in events:
                    generated = _parse_event_time(event.TimeGenerated)
                    if generated < start:
                        return entries
                    if generated > end:
                        continue
                    level = _LEVEL_NAMES.get(event.EventType, "Unknown")
                    message = _format_message(event, log_name, win32evtlogutil)
                    entries.append(
                        EventLogEvidence(
                            eventId=event.EventID & 0xFFFF,
                            source=event.SourceName or "",
                            level=level,
                            message=message[:32000],
                            timestamp=generated.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
                            logName=log_name,
                            recordId=event.RecordNumber,
                        )
                    )
        finally:
            win32evtlog.CloseEventLog(hand)
        return entries


def _format_message(event, log_name: str, win32evtlogutil) -> str:  # noqa: ANN001
    if win32evtlogutil is not None:
        try:
            return win32evtlogutil.SafeFormatMessage(event, log_name) or ""
        except Exception:
            pass
    if event.StringInserts:
        parts = [str(part) for part in event.StringInserts if part]
        return " | ".join(parts)
    return ""


def _collect_via_wevtutil(
    start: datetime,
    end: datetime,
    log_names: tuple[str, ...],
) -> list[EventLogEvidence]:
    """Fallback using wevtutil for richer messages on modern Windows."""
    import json

    entries: list[EventLogEvidence] = []
    start_utc = start.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    end_utc = end.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    query = (
        f"*[System[(TimeCreated[@SystemTime>='{start_utc}'] and "
        f"TimeCreated[@SystemTime<='{end_utc}'])]]"
    )

    for log_name in log_names:
        try:
            completed = subprocess.run(
                [
                    "wevtutil",
                    "qe",
                    log_name,
                    f"/q:{query}",
                    "/f:json",
                    "/rd:true",
                    "/c:2000",
                ],
                capture_output=True,
                text=True,
                timeout=90,
                shell=False,
            )
            if completed.returncode != 0 or not completed.stdout.strip():
                continue
            payload = json.loads(completed.stdout)
            events = payload if isinstance(payload, list) else [payload]
            for item in events:
                parsed = _parse_wevtutil_event(item, log_name)
                if parsed is not None:
                    entries.append(parsed)
        except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
            logger.debug("wevtutil_skipped", log=log_name, error=str(exc))
    return entries


def _parse_wevtutil_event(item: dict, log_name: str) -> EventLogEvidence | None:
    try:
        system = item.get("Event", {}).get("System", {})
        event_id = int(system.get("EventID"))
        level_code = int(system.get("Level", 4))
        level = _LEVEL_NAMES.get(level_code, "Information")
        provider = system.get("Provider", {}).get("@Name", "")
        created = system.get("TimeCreated", {}).get("@SystemTime", "")
        record_id = system.get("EventRecordID")
        message = ""
        event_data = item.get("Event", {}).get("EventData", {})
        if isinstance(event_data, dict):
            raw = event_data.get("Data")
            if isinstance(raw, list):
                message = " | ".join(str(x) for x in raw if x)
            elif raw:
                message = str(raw)
        return EventLogEvidence(
            eventId=event_id,
            source=str(provider),
            level=level,
            message=message[:32000],
            timestamp=created,
            logName=log_name,
            recordId=int(record_id) if record_id is not None else None,
        )
    except (KeyError, TypeError, ValueError):
        return None


def _parse_event_time(time_generated: object) -> datetime:
    if isinstance(time_generated, datetime):
        if time_generated.tzinfo is None:
            return time_generated.replace(tzinfo=timezone.utc)
        return time_generated.astimezone(timezone.utc)
    return datetime.fromtimestamp(int(time_generated), tz=timezone.utc)
