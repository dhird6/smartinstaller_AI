"""Chat message models for the desktop UI."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class ChatRole(StrEnum):
    ASSISTANT = "assistant"
    USER = "user"
    SYSTEM = "system"


@dataclass(frozen=True, slots=True)
class ChatSection:
    """Structured section inside a chat card."""

    heading: str
    body: str


@dataclass(frozen=True, slots=True)
class ChatMessage:
    """Single message shown in the chat panel."""

    role: ChatRole
    content: str
    title: str | None = None
    sections: list[ChatSection] = field(default_factory=list)
    timestamp: datetime | None = None
