"""
SmartInstaller AI — silent launcher.
Invoked by Windows context menu with the installer path as argv[1].
No console window (.pyw extension).
"""
import json
import subprocess
import sys
import time
import tkinter as tk
from pathlib import Path
from tkinter import scrolledtext

PROJECT_DIR = Path(__file__).resolve().parent.parent
PYTHON = sys.executable


# ── Ollama health ──────────────────────────────────────────────────────────────

def _ollama_running() -> bool:
    try:
        import urllib.request
        urllib.request.urlopen("http://localhost:11434", timeout=2)
        return True
    except Exception:
        return False


def _ensure_ollama() -> bool:
    if _ollama_running():
        return True
    subprocess.Popen(
        ["ollama", "serve"],
        creationflags=subprocess.CREATE_NO_WINDOW,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(20):
        time.sleep(1)
        if _ollama_running():
            return True
    return False


# ── Run agent ──────────────────────────────────────────────────────────────────

def _run_agent(installer_path: str) -> tuple[int, str]:
    """Run smartinstall install <path> and return (exit_code, stdout)."""
    result = subprocess.run(
        [PYTHON, "-m", "smartinstall", "install", installer_path],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout + result.stderr


def _find_latest_session_dir() -> Path | None:
    sessions = PROJECT_DIR / "sessions"
    dirs = sorted(sessions.glob("*/"), key=lambda d: d.stat().st_mtime, reverse=True)
    return dirs[0] if dirs else None


# ── Result popup ───────────────────────────────────────────────────────────────

def _show_popup(title: str, body: str, color: str = "#1e1e1e") -> None:
    root = tk.Tk()
    root.title(title)
    root.configure(bg=color)
    root.geometry("680x520")
    root.resizable(True, True)

    header = tk.Label(
        root, text=title, bg=color, fg="white",
        font=("Segoe UI", 13, "bold"), pady=10,
    )
    header.pack(fill="x")

    text_area = scrolledtext.ScrolledText(
        root, wrap=tk.WORD, bg="#2d2d2d", fg="#d4d4d4",
        font=("Consolas", 10), bd=0, relief="flat", padx=12, pady=8,
    )
    text_area.insert(tk.END, body)
    text_area.config(state=tk.DISABLED)
    text_area.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    tk.Button(
        root, text="Close", command=root.destroy,
        bg="#0e639c", fg="white", font=("Segoe UI", 10),
        relief="flat", padx=20, pady=6, cursor="hand2",
    ).pack(pady=(0, 12))

    root.lift()
    root.focus_force()
    root.mainloop()


def _format_success(installer: str) -> str:
    return (
        f"✓  Installation completed successfully.\n\n"
        f"Installer:  {installer}\n\n"
        f"No failures detected — no RAG diagnosis needed.\n"
        f"Full evidence report saved in:  sessions/"
    )


def _format_diagnosis(diagnosis: dict, installer: str) -> str:
    fixes = "\n".join(
        f"  {i+1}. {f}" for i, f in enumerate(diagnosis.get("recommended_fixes") or [])
    )
    cmds = "\n".join(
        f"  • {c}" for c in (diagnosis.get("verification_commands") or [])
    )
    docs = ", ".join(diagnosis.get("retrieved_docs") or [])
    return (
        f"Installer:     {installer}\n"
        f"Outcome:       {diagnosis.get('outcome', 'FAILED')}\n"
        f"Confidence:    {diagnosis.get('confidence', '—')}\n\n"
        f"Root Cause:\n  {diagnosis.get('root_cause', '—')}\n\n"
        f"Evidence:\n  {diagnosis.get('evidence', '—')}\n\n"
        f"Recommended Fixes:\n{fixes or '  —'}\n\n"
        f"Verification Commands:\n{cmds or '  —'}\n\n"
        f"Escalation:\n  {diagnosis.get('escalation', '—')}\n\n"
        f"Retrieved KB docs:  {docs or '—'}"
    )


def _format_agent_output(stdout: str, installer: str) -> str:
    return (
        f"Installer:  {installer}\n\n"
        f"Agent output (RAG diagnosis not available — is Ollama running?):\n\n"
        f"{stdout[-3000:]}"
    )


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    if len(sys.argv) < 2:
        _show_popup("SmartInstaller AI", "No installer path provided.", "#8b0000")
        return

    installer_path = sys.argv[1]
    installer_name = Path(installer_path).name

    # 1. Start Ollama in background (non-blocking for the agent — RAG is best-effort)
    ollama_ok = _ensure_ollama()

    # 2. Run the monitoring agent
    exit_code, agent_output = _run_agent(installer_path)

    # 3. Find rag_diagnosis.json from the newest session
    session_dir = _find_latest_session_dir()
    diag_file = (session_dir / "rag_diagnosis.json") if session_dir else None

    if exit_code == 0:
        _show_popup(
            f"✓ SmartInstaller AI — {installer_name}",
            _format_success(installer_name),
            "#1a3a1a",
        )
    elif diag_file and diag_file.exists():
        diagnosis = json.loads(diag_file.read_text(encoding="utf-8"))
        _show_popup(
            f"⚠ SmartInstaller AI — Failure Detected: {installer_name}",
            _format_diagnosis(diagnosis, installer_name),
            "#3a1a1a",
        )
    else:
        _show_popup(
            f"⚠ SmartInstaller AI — {installer_name}",
            _format_agent_output(agent_output, installer_name),
            "#3a2a1a",
        )


if __name__ == "__main__":
    main()
