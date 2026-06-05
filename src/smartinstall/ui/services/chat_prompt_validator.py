"""Validate and classify chat prompts before routing to commands or RAG."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

_MIN_PROMPT_LENGTH = 2
_MAX_PROMPT_LENGTH = 2000

_LAST_INSTALL_MARKERS = (
    "last installation",
    "last install",
    "latest run",
    "latest installation",
    "latest install",
    "previous install",
    "previous installation",
    "recent install",
    "recent installation",
    "what went wrong",
    "summarize errors",
    "summarise errors",
    "last run",
)

_KNOWLEDGE_MARKERS = (
    "how do i fix",
    "how to fix",
    "how can i fix",
    "exit code",
    "error code",
    "troubleshoot",
    "troubleshooting",
    "what is",
    "what does",
    "explain",
    "why did",
    "root cause",
    "recommended fix",
    "fix ",
    "msi ",
    "installer error",
    "installation error",
    "failed to install",
    "permission denied",
    "access denied",
    "disk space",
    "visual c++",
    "autocad",
    "autodesk",
    "flexnet",
    "mingw",
)

_HELP_MARKERS = (
    "what can smart install",
    "what can you do",
    "how does ai troubleshooting",
    "how does troubleshooting work",
    "capabilities",
    "what do you do",
)

_LIST_ALIASES = frozenset(
    {
        "list",
        "list installers",
        "list available installers",
        "show installers",
        "available installers",
    }
)

_WORD_PATTERN = re.compile(r"[a-zA-Z0-9]")


class ChatPromptIntent(str, Enum):
    """Routing target for a validated chat prompt."""

    COMMAND_LIST = "command_list"
    COMMAND_INSTALL = "command_install"
    COMMAND_BROWSE = "command_browse"
    COMMAND_HELP = "command_help"
    DIAGNOSE_LAST = "diagnose_last"
    KNOWLEDGE_QUERY = "knowledge_query"
    INVALID = "invalid"


@dataclass(frozen=True, slots=True)
class ChatPromptValidation:
    """Outcome of chat prompt validation and intent classification."""

    valid: bool
    intent: ChatPromptIntent
    normalized: str
    error_message: str | None = None
    installer_name: str | None = None


def validate_chat_prompt(text: str) -> ChatPromptValidation:
    """Validate user input and determine how the chat assistant should respond."""
    normalized = text.strip()
    if not normalized:
        return ChatPromptValidation(
            valid=False,
            intent=ChatPromptIntent.INVALID,
            normalized="",
            error_message="Please enter a message before sending.",
        )

    if len(normalized) < _MIN_PROMPT_LENGTH:
        return ChatPromptValidation(
            valid=False,
            intent=ChatPromptIntent.INVALID,
            normalized=normalized,
            error_message="Your message is too short. Ask a question or use a command like `list` or `install`.",
        )

    if len(normalized) > _MAX_PROMPT_LENGTH:
        return ChatPromptValidation(
            valid=False,
            intent=ChatPromptIntent.INVALID,
            normalized=normalized,
            error_message=(
                f"Your message is too long ({len(normalized)} characters). "
                f"Please keep prompts under {_MAX_PROMPT_LENGTH} characters."
            ),
        )

    if not _WORD_PATTERN.search(normalized):
        return ChatPromptValidation(
            valid=False,
            intent=ChatPromptIntent.INVALID,
            normalized=normalized,
            error_message="Your message must include letters or numbers. Try a clear question or command.",
        )

    lowered = normalized.lower()
    if lowered in _LIST_ALIASES:
        return ChatPromptValidation(
            valid=True,
            intent=ChatPromptIntent.COMMAND_LIST,
            normalized=normalized,
        )

    if lowered in {"help", "?"}:
        return ChatPromptValidation(
            valid=True,
            intent=ChatPromptIntent.COMMAND_HELP,
            normalized=normalized,
        )

    if lowered in {"install", "browse"}:
        return ChatPromptValidation(
            valid=True,
            intent=ChatPromptIntent.COMMAND_BROWSE,
            normalized=normalized,
        )

    if lowered.startswith("install "):
        installer_name = normalized[8:].strip()
        if not installer_name:
            return ChatPromptValidation(
                valid=True,
                intent=ChatPromptIntent.COMMAND_BROWSE,
                normalized=normalized,
            )
        if not _is_plausible_installer_name(installer_name):
            return ChatPromptValidation(
                valid=False,
                intent=ChatPromptIntent.INVALID,
                normalized=normalized,
                error_message=(
                    "Installer name looks invalid. Use a file name like `mingw-get-setup.exe` "
                    "or choose Browse Installer."
                ),
            )
        return ChatPromptValidation(
            valid=True,
            intent=ChatPromptIntent.COMMAND_INSTALL,
            normalized=normalized,
            installer_name=installer_name,
        )

    if any(marker in lowered for marker in _HELP_MARKERS):
        return ChatPromptValidation(
            valid=True,
            intent=ChatPromptIntent.COMMAND_HELP,
            normalized=normalized,
        )

    if any(marker in lowered for marker in _LAST_INSTALL_MARKERS):
        return ChatPromptValidation(
            valid=True,
            intent=ChatPromptIntent.DIAGNOSE_LAST,
            normalized=normalized,
        )

    if _looks_like_question(lowered) or any(marker in lowered for marker in _KNOWLEDGE_MARKERS):
        return ChatPromptValidation(
            valid=True,
            intent=ChatPromptIntent.KNOWLEDGE_QUERY,
            normalized=normalized,
        )

    return ChatPromptValidation(
        valid=False,
        intent=ChatPromptIntent.INVALID,
        normalized=normalized,
        error_message=(
            "I didn't understand that prompt. Try:\n"
            "- `list` — show installers\n"
            "- `install <file-name>` — run a monitored install\n"
            "- Ask about errors, e.g. \"How do I fix exit code 1603?\"\n"
            "- Ask about the last run, e.g. \"What went wrong with the last installation?\"\n"
            "- `help` — see what I can do"
        ),
    )


def is_install_command_intent(intent: ChatPromptIntent) -> bool:
    """True when the prompt starts an installation workflow."""
    return intent in {
        ChatPromptIntent.COMMAND_INSTALL,
        ChatPromptIntent.COMMAND_BROWSE,
    }


def _looks_like_question(text: str) -> bool:
    if text.endswith("?"):
        return True
    starters = ("what ", "how ", "why ", "when ", "where ", "can ", "could ", "is ", "are ", "does ")
    return text.startswith(starters)


def _is_plausible_installer_name(name: str) -> bool:
    if ".." in name or "/" in name or "\\" in name:
        return False
    if len(name) > 260:
        return False
    lower = name.lower()
    return lower.endswith(".exe") or lower.endswith(".msi") or "." not in name
