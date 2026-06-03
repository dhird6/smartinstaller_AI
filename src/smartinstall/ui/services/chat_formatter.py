"""Format installation reports and SLM output for chat display."""

from __future__ import annotations

from smartinstall.core.models.unified_report import ReportErrorEntry, UnifiedInstallationReport
from smartinstall.ui.models.chat_message import ChatMessage, ChatRole, ChatSection
from smartinstall.ui.services.slm_response_parser import parse_slm_sections


class ChatFormatter:
    """Builds user-facing chat messages from domain models."""

    @staticmethod
    def welcome() -> ChatMessage:
        return ChatMessage(
            role=ChatRole.ASSISTANT,
            title="Welcome",
            content=(
                "Welcome to SmartInstall AI.\n\n"
                "You can:\n"
                "- Type `install <installer-name>` (example: `install mingw-get-setup.exe`)\n"
                "- Type `list` to see installers in the installers folder\n"
                "- Use **Browse Installer** to pick any .exe or .msi file\n\n"
                "I will monitor installation, collect diagnostics, and run local AI troubleshooting."
            ),
        )

    @staticmethod
    def installer_list(file_names: list[str]) -> ChatMessage:
        if not file_names:
            body = "No installers found. Copy a .exe or .msi file into the installers folder."
        else:
            body = "Available installers:\n" + "\n".join(f"- {name}" for name in file_names)
        return ChatMessage(role=ChatRole.ASSISTANT, title="Installers", content=body)

    @staticmethod
    def status_update(message: str) -> ChatMessage:
        return ChatMessage(role=ChatRole.SYSTEM, content=message)

    @staticmethod
    def installation_summary(report: UnifiedInstallationReport, report_path: str) -> ChatMessage:
        status = report.status
        top_error = ChatFormatter._top_error(report.errors)
        sections: list[ChatSection] = [
            ChatSection(
                heading="Installation Status",
                body=(
                    f"Installer: {status.installer.installer_name}\n"
                    f"Outcome: {status.installation_outcome}\n"
                    f"Completed: {status.installation_completed}\n"
                    f"Report: {report_path}"
                ),
            )
        ]

        if top_error is not None:
            sections.append(
                ChatSection(
                    heading="Detected Error",
                    body=f"Error Code: {top_error.code}\nMessage: {top_error.message}",
                )
            )
        if status.failure_reason:
            sections.append(
                ChatSection(heading="Failure Reason", body=status.failure_reason)
            )

        registry_count = len(report.evidence.registry_changes)
        filesystem_count = len(report.evidence.filesystem_changes)
        if registry_count or filesystem_count:
            sections.append(
                ChatSection(
                    heading="System Changes",
                    body=(
                        f"Registry changes: {registry_count}\n"
                        f"Filesystem changes: {filesystem_count}"
                    ),
                )
            )

        title = (
            "Installation Complete"
            if status.installation_completed
            else "Installation Issue Detected"
        )
        summary = f"Captured {len(report.errors)} error item(s)."
        return ChatMessage(role=ChatRole.ASSISTANT, title=title, content=summary, sections=sections)

    @staticmethod
    def slm_diagnosis(answer: str, sources: list[str]) -> ChatMessage:
        sections = parse_slm_sections(answer)
        source_line = ", ".join(sources) if sources else "none"
        if not sections:
            return ChatMessage(
                role=ChatRole.ASSISTANT,
                title="AI Troubleshooting",
                content=f"{answer.strip()}\n\nKnowledge sources: {source_line}",
            )
        sections.append(
            ChatSection(heading="Knowledge Sources", body=source_line)
        )
        return ChatMessage(
            role=ChatRole.ASSISTANT,
            title="AI Troubleshooting",
            content="Analysis complete. See details below.",
            sections=sections,
        )

    @staticmethod
    def error_message(message: str) -> ChatMessage:
        return ChatMessage(role=ChatRole.ASSISTANT, title="Error", content=message)

    @staticmethod
    def _top_error(errors: list[ReportErrorEntry]) -> ReportErrorEntry | None:
        if not errors:
            return None
        for entry in errors:
            if entry.severity == "error":
                return entry
        return errors[0]
