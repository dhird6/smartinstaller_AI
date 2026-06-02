"""
SmartInstaller AI — autonomous launcher.
Right-click .exe/.msi -> this runs silently (no console).

Thread layout:
  Main thread  — Tkinter status window (never blocks)
  Thread A     — starts Ollama if needed (background, fire-and-forget)
  Thread B     — runs `smartinstall install <path>` (the actual install + monitoring)
                 posts result back to Tk via root.after()
"""
import json
import os
import subprocess
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import scrolledtext, ttk

PROJECT_DIR = Path(__file__).resolve().parent.parent
PYTHON = sys.executable
LOCK_FILE = PROJECT_DIR / "sessions" / ".launcher.lock"


# ── Single-instance guard ──────────────────────────────────────────────────────

def _is_pid_alive(pid: int) -> bool:
    try:
        import psutil
        return psutil.pid_exists(pid)
    except Exception:
        return False


def _acquire_lock() -> bool:
    """Return True if we are the only launcher instance."""
    try:
        LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        if LOCK_FILE.exists():
            try:
                pid = int(LOCK_FILE.read_text().strip())
                if _is_pid_alive(pid):
                    return False   # another launcher is running
            except Exception:
                pass               # stale / corrupt lock, overwrite it
        LOCK_FILE.write_text(str(os.getpid()))
        return True
    except Exception:
        return True                # can't check — proceed anyway


def _release_lock() -> None:
    try:
        LOCK_FILE.unlink(missing_ok=True)
    except Exception:
        pass


# ── Ollama ─────────────────────────────────────────────────────────────────────

def _ollama_running() -> bool:
    try:
        import urllib.request
        urllib.request.urlopen("http://localhost:11434", timeout=2)
        return True
    except Exception:
        return False


def _ensure_ollama_bg() -> None:
    """Fire-and-forget: start Ollama if not running. Runs in its own thread."""
    if _ollama_running():
        return
    subprocess.Popen(
        ["ollama", "serve"],
        creationflags=subprocess.CREATE_NO_WINDOW,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


# ── Agent runner ───────────────────────────────────────────────────────────────

def _run_agent(installer_path: str) -> tuple[int, str]:
    """
    Run `smartinstall install <path>` in a subprocess.
    Installation happens inside the agent — this thread just waits for it to finish.
    Returns (exit_code, combined output).
    """
    proc = subprocess.run(
        [PYTHON, "-m", "smartinstall", "install", installer_path],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return proc.returncode, proc.stdout + proc.stderr


def _find_latest_session_dir() -> Path | None:
    sessions = PROJECT_DIR / "sessions"
    dirs = sorted(
        (d for d in sessions.iterdir() if d.is_dir() and d.name != "."),
        key=lambda d: d.stat().st_mtime,
        reverse=True,
    )
    return dirs[0] if dirs else None


# ── Result formatting ──────────────────────────────────────────────────────────

def _format_success(installer: str) -> str:
    return (
        f"Installer:  {installer}\n\n"
        f"Installation completed successfully.\n"
        f"No failures detected — RAG diagnosis was not needed.\n\n"
        f"Evidence report saved in:  sessions/"
    )


def _format_diagnosis(diag: dict, installer: str) -> str:
    fixes = "\n".join(
        f"  {i+1}. {f}" for i, f in enumerate(diag.get("recommended_fixes") or [])
    )
    cmds = "\n".join(
        f"  - {c}" for c in (diag.get("verification_commands") or [])
    )
    docs = ", ".join(diag.get("retrieved_docs") or [])
    return (
        f"Installer:    {installer}\n"
        f"Outcome:      {diag.get('outcome', 'FAILED')}\n"
        f"Confidence:   {diag.get('confidence', '-')}\n\n"
        f"Root Cause:\n  {diag.get('root_cause', '-')}\n\n"
        f"Evidence:\n  {diag.get('evidence', '-')}\n\n"
        f"Recommended Fixes:\n{fixes or '  -'}\n\n"
        f"Verification Commands:\n{cmds or '  -'}\n\n"
        f"Escalation:\n  {diag.get('escalation', '-')}\n\n"
        f"KB docs matched:  {docs or '-'}"
    )


def _format_raw(output: str, installer: str) -> str:
    snippet = output.strip()[-2000:] if output.strip() else "(no output)"
    return (
        f"Installer:  {installer}\n\n"
        f"RAG diagnosis unavailable (Ollama may not be running).\n"
        f"Agent log:\n\n{snippet}"
    )


# ── Status window ──────────────────────────────────────────────────────────────

class StatusWindow:
    """
    Single persistent Tk window.
    Shows a spinner while the installer runs, then updates in-place with results.
    Never re-creates the window — no flash, no loop.
    """

    def __init__(self, installer_name: str) -> None:
        self.root = tk.Tk()
        self.root.title(f"SmartInstaller AI  |  {installer_name}")
        self.root.geometry("560x140")
        self.root.configure(bg="#1e1e1e")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._label = tk.Label(
            self.root,
            text="Monitoring installation...",
            bg="#1e1e1e", fg="#d4d4d4",
            font=("Segoe UI", 11),
        )
        self._label.pack(pady=(20, 8), padx=16)

        style = ttk.Style(self.root)
        style.theme_use("default")
        style.configure("Blue.Horizontal.TProgressbar",
                        troughcolor="#2d2d2d", background="#0e639c")
        self._bar = ttk.Progressbar(
            self.root, style="Blue.Horizontal.TProgressbar",
            mode="indeterminate", length=520,
        )
        self._bar.pack(padx=16, pady=(0, 8))
        self._bar.start(12)

        self._sub = tk.Label(
            self.root,
            text="Complete the installer normally. This window will update automatically.",
            bg="#1e1e1e", fg="#6a6a6a",
            font=("Segoe UI", 9),
        )
        self._sub.pack(pady=(0, 12))

        self._done = False

    def _on_close(self) -> None:
        self._done = True
        _release_lock()
        self.root.destroy()

    def post_result(self, title: str, body: str, success: bool) -> None:
        """Called from any thread via root.after — updates window in place."""
        self.root.after(0, lambda: self._render_result(title, body, success))

    def _render_result(self, title: str, body: str, success: bool) -> None:
        if self._done:
            return

        # Tear down spinner widgets
        self._bar.stop()
        self._bar.destroy()
        self._sub.destroy()

        # Expand window for result
        bg = "#1a3a1a" if success else "#2a1a1a"
        self.root.configure(bg=bg)
        self.root.geometry("680x500")
        self.root.resizable(True, True)

        self._label.configure(
            text=title, bg=bg,
            fg="#80ff80" if success else "#ff8080",
            font=("Segoe UI", 12, "bold"),
        )

        txt = scrolledtext.ScrolledText(
            self.root, wrap=tk.WORD,
            bg="#2d2d2d", fg="#d4d4d4",
            font=("Consolas", 10),
            relief="flat", padx=10, pady=8,
        )
        txt.insert(tk.END, body)
        txt.config(state=tk.DISABLED)
        txt.pack(fill="both", expand=True, padx=12, pady=(4, 6))

        tk.Button(
            self.root, text="Close",
            command=self._on_close,
            bg="#0e639c", fg="white",
            font=("Segoe UI", 10), relief="flat",
            padx=20, pady=5, cursor="hand2",
        ).pack(pady=(0, 10))

    def run(self) -> None:
        self.root.mainloop()


# ── Worker thread ──────────────────────────────────────────────────────────────

def _worker(installer_path: str, installer_name: str, window: StatusWindow) -> None:
    """Runs in Thread B. Calls agent, then posts result to window."""
    exit_code, output = _run_agent(installer_path)

    session_dir = _find_latest_session_dir()
    diag_file = (session_dir / "rag_diagnosis.json") if session_dir else None

    if exit_code == 0:
        window.post_result(
            f"Success  |  {installer_name}",
            _format_success(installer_name),
            success=True,
        )
    elif diag_file and diag_file.exists():
        try:
            diag = json.loads(diag_file.read_text(encoding="utf-8"))
            window.post_result(
                f"Failure Detected  |  {installer_name}",
                _format_diagnosis(diag, installer_name),
                success=False,
            )
        except Exception:
            window.post_result(
                f"Failure Detected  |  {installer_name}",
                _format_raw(output, installer_name),
                success=False,
            )
    else:
        window.post_result(
            f"Finished  |  {installer_name}",
            _format_raw(output, installer_name),
            success=False,
        )

    _release_lock()


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    if len(sys.argv) < 2:
        return

    installer_path = sys.argv[1]
    installer_name = Path(installer_path).name

    # Single-instance guard — silently exit if another launcher is already running
    if not _acquire_lock():
        return

    # Thread A: Ollama warm-up (non-blocking, best-effort)
    threading.Thread(target=_ensure_ollama_bg, daemon=True).start()

    # Build the status window
    window = StatusWindow(installer_name)

    # Thread B: agent + RAG — posts result back to window when done
    threading.Thread(
        target=_worker,
        args=(installer_path, installer_name, window),
        daemon=True,
    ).start()

    # Main thread: run Tk event loop (never blocks the installer)
    window.run()


if __name__ == "__main__":
    main()
