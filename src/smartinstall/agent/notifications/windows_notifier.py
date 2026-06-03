"""Windows toast notifications for installation errors (no Qt dependency)."""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import xml.sax.saxutils as xml_escape
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)

_MAX_TOAST_FIELD = 240


class WindowsNotifier:
    """Shows native Windows toast notifications via PowerShell."""

    def show_toast(self, *, title: str, message: str) -> None:
        if sys.platform != "win32":
            return
        safe_title = _sanitize_toast_text(title)
        safe_message = _sanitize_toast_text(message)
        toast_xml = (
            '<toast activatable="false">'
            "<visual>"
            '<binding template="ToastText02">'
            f"<text id=\"1\">{xml_escape.escape(safe_title)}</text>"
            f"<text id=\"2\">{xml_escape.escape(safe_message)}</text>"
            "</binding>"
            "</visual>"
            "</toast>"
        )
        self._display_xml(toast_xml)

    def show_installation_failed(
        self,
        *,
        error_message: str,
        suggested_fix: str,
    ) -> None:
        body = f"Error: {error_message}\nSuggested fix: {suggested_fix}"
        self.show_toast(title="Installation Failed", message=body)

    @staticmethod
    def _display_xml(toast_xml: str) -> None:
        xml_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                suffix=".xml",
                delete=False,
            ) as handle:
                handle.write(toast_xml)
                xml_path = Path(handle.name)
            xml_literal = str(xml_path).replace("'", "''")
            script = (
                "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, "
                "ContentType = WindowsRuntime] | Out-Null; "
                "[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, "
                "ContentType = WindowsRuntime] | Out-Null; "
                f"$xml = New-Object Windows.Data.Xml.Dom.XmlDocument; "
                f"$xml.LoadXml((Get-Content -LiteralPath '{xml_literal}' -Raw -Encoding UTF8)); "
                "$toast = [Windows.UI.Notifications.ToastNotification]::new($xml); "
                "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("
                "'SmartInstall AI').Show($toast);"
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
                check=False,
                capture_output=True,
                timeout=15,
                shell=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            logger.warning("windows_toast_failed", error=str(exc))
        finally:
            if xml_path is not None:
                try:
                    xml_path.unlink(missing_ok=True)
                except OSError:
                    pass


def _sanitize_toast_text(value: str) -> str:
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", value)
    return cleaned[:_MAX_TOAST_FIELD]
