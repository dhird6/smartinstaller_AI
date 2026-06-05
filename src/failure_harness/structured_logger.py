"""Structured logging for harness events (JSON, CSV, human-readable)."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from failure_harness.models import HarnessEvent


class StructuredHarnessLogger:
    """Write harness events to multiple log formats."""

    def __init__(self, logs_dir: Path, run_id: str) -> None:
        self._logs_dir = logs_dir.resolve()
        self._logs_dir.mkdir(parents=True, exist_ok=True)
        self._run_id = run_id
        self._events: list[HarnessEvent] = []

        self._json_path = self._logs_dir / f"harness_{run_id}.jsonl"
        self._csv_path = self._logs_dir / f"harness_{run_id}.csv"
        self._text_path = self._logs_dir / f"harness_{run_id}.log"

        if not self._csv_path.exists():
            with self._csv_path.open("w", encoding="utf-8", newline="") as fh:
                writer = csv.writer(fh)
                writer.writerow(["timestamp", "phase", "component", "eventType", "message", "details"])

    def log(
        self,
        phase: str,
        component: str,
        event_type: str,
        message: str,
        details: dict | None = None,
    ) -> HarnessEvent:
        event = HarnessEvent(
            timestamp=_utc_now(),
            phase=phase,
            component=component,
            eventType=event_type,
            message=message,
            details=details or {},
        )
        self._events.append(event)
        self._append_json(event)
        self._append_csv(event)
        self._append_text(event)
        return event

    def get_events(self) -> list[HarnessEvent]:
        return list(self._events)

    def _append_json(self, event: HarnessEvent) -> None:
        line = event.model_dump(by_alias=True)
        line["runId"] = self._run_id
        with self._json_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(line, ensure_ascii=False) + "\n")

    def _append_csv(self, event: HarnessEvent) -> None:
        with self._csv_path.open("a", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(
                [
                    event.timestamp,
                    event.phase,
                    event.component,
                    event.event_type,
                    event.message,
                    json.dumps(event.details, ensure_ascii=False),
                ]
            )

    def _append_text(self, event: HarnessEvent) -> None:
        detail_str = f" | {event.details}" if event.details else ""
        line = f"[{event.timestamp}] [{event.phase}] [{event.component}] {event.event_type}: {event.message}{detail_str}\n"
        with self._text_path.open("a", encoding="utf-8") as fh:
            fh.write(line)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
