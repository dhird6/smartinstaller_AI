"""Graphical installer window for TestAppSetup — demo-friendly setup UI."""

from __future__ import annotations

import queue
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import scrolledtext, ttk

from failure_harness.models import ScenarioConfig
from failure_harness.test_installer import run_install_simulation

WINDOW_TITLE = "TestApp Setup"
_PRODUCT_NAME = "TestApp Setup"
_VERSION = "1.0.0"

# CCTech-inspired palette (aligned with SmartInstall AI desktop theme)
_COLOR_BG = "#f4f6fb"
_COLOR_HEADER = "#0b1020"
_COLOR_HEADER_TEXT = "#ffffff"
_COLOR_MUTED = "#94a3b8"
_COLOR_TEXT = "#111827"
_COLOR_ACCENT = "#1e5bff"
_COLOR_SUCCESS = "#16a34a"
_COLOR_ERROR = "#dc2626"
_COLOR_CARD = "#ffffff"
_COLOR_CARD_BORDER = "#e2e8f0"


def run_installer_gui(scenario: ScenarioConfig) -> int:
    """Show a windowed installer experience and return the process exit code."""
    app = _InstallerWindow(scenario)
    return app.run()


class _InstallerWindow:
    def __init__(self, scenario: ScenarioConfig) -> None:
        self._scenario = scenario
        self._exit_code = 1
        self._events: queue.Queue[tuple] = queue.Queue()
        self._finished = False
        self._logo_image = None

        self._root = tk.Tk()
        self._root.title(f"{WINDOW_TITLE} — CCTech Demo")
        self._root.configure(bg=_COLOR_BG)
        self._root.minsize(560, 460)
        self._root.geometry("600x500")
        self._root.resizable(True, True)
        self._center_on_screen()

    def run(self) -> int:
        self._build_ui()
        self._root.protocol("WM_DELETE_WINDOW", self._on_close_while_running)
        self._root.after(80, self._poll_events)
        threading.Thread(target=self._run_installation, name="TestAppInstall", daemon=True).start()
        self._root.mainloop()
        return self._exit_code

    def _center_on_screen(self) -> None:
        self._root.update_idletasks()
        width = 600
        height = 500
        x = (self._root.winfo_screenwidth() // 2) - (width // 2)
        y = (self._root.winfo_screenheight() // 2) - (height // 2)
        self._root.geometry(f"{width}x{height}+{x}+{y}")

    def _build_ui(self) -> None:
        header = tk.Frame(self._root, bg=_COLOR_HEADER, height=92)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        header_inner = tk.Frame(header, bg=_COLOR_HEADER)
        header_inner.pack(fill=tk.BOTH, expand=True, padx=22, pady=16)

        title_row = tk.Frame(header_inner, bg=_COLOR_HEADER)
        title_row.pack(fill=tk.X)

        self._logo_image = _load_logo_image(self._root)
        if self._logo_image is not None:
            logo_lbl = tk.Label(title_row, image=self._logo_image, bg=_COLOR_HEADER)
            logo_lbl.pack(side=tk.LEFT, padx=(0, 12))

        text_col = tk.Frame(title_row, bg=_COLOR_HEADER)
        text_col.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(
            text_col,
            text="CCTech · Demo Installer",
            bg=_COLOR_HEADER,
            fg=_COLOR_MUTED,
            font=("Segoe UI", 9),
            anchor="w",
        ).pack(fill=tk.X)
        tk.Label(
            text_col,
            text=_PRODUCT_NAME,
            bg=_COLOR_HEADER,
            fg=_COLOR_HEADER_TEXT,
            font=("Segoe UI", 18, "bold"),
            anchor="w",
        ).pack(fill=tk.X)
        tk.Label(
            text_col,
            text=f"Version {_VERSION}  ·  Scenario: {self._scenario.name}",
            bg=_COLOR_HEADER,
            fg="#cbd5e1",
            font=("Segoe UI", 9),
            anchor="w",
        ).pack(fill=tk.X)

        body = tk.Frame(self._root, bg=_COLOR_BG)
        body.pack(fill=tk.BOTH, expand=True, padx=22, pady=18)

        card = tk.Frame(body, bg=_COLOR_CARD, highlightbackground=_COLOR_CARD_BORDER, highlightthickness=1)
        card.pack(fill=tk.BOTH, expand=True)

        card_inner = tk.Frame(card, bg=_COLOR_CARD)
        card_inner.pack(fill=tk.BOTH, expand=True, padx=18, pady=16)

        self._step_label = tk.Label(
            card_inner,
            text="Preparing installation…",
            bg=_COLOR_CARD,
            fg=_COLOR_TEXT,
            font=("Segoe UI", 11, "bold"),
            anchor="w",
        )
        self._step_label.pack(fill=tk.X)

        self._progress = ttk.Progressbar(card_inner, mode="determinate", maximum=100)
        self._progress.pack(fill=tk.X, pady=(10, 6))
        self._style_progress_bar()

        self._percent_label = tk.Label(
            card_inner,
            text="0% complete",
            bg=_COLOR_CARD,
            fg=_COLOR_MUTED,
            font=("Segoe UI", 9),
            anchor="w",
        )
        self._percent_label.pack(fill=tk.X, pady=(0, 10))

        tk.Label(
            card_inner,
            text="Installation activity",
            bg=_COLOR_CARD,
            fg=_COLOR_TEXT,
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        ).pack(fill=tk.X)

        self._log = scrolledtext.ScrolledText(
            card_inner,
            height=11,
            wrap=tk.WORD,
            font=("Consolas", 9),
            bg="#f8fafc",
            fg="#1e293b",
            relief=tk.FLAT,
            borderwidth=1,
            highlightthickness=1,
            highlightbackground=_COLOR_CARD_BORDER,
        )
        self._log.pack(fill=tk.BOTH, expand=True, pady=(6, 0))
        self._log.configure(state=tk.DISABLED)

        footer = tk.Frame(self._root, bg=_COLOR_BG)
        footer.pack(fill=tk.X, padx=22, pady=(0, 18))

        self._status_label = tk.Label(
            footer,
            text="Installing… please wait.",
            bg=_COLOR_BG,
            fg=_COLOR_TEXT,
            font=("Segoe UI", 10),
            anchor="w",
        )
        self._status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self._close_btn = tk.Button(
            footer,
            text="Close",
            state=tk.DISABLED,
            command=self._root.destroy,
            bg=_COLOR_ACCENT,
            fg="#ffffff",
            activebackground="#1848cc",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            font=("Segoe UI", 10, "bold"),
            padx=16,
            pady=6,
            cursor="hand2",
        )
        self._close_btn.pack(side=tk.RIGHT)

    def _style_progress_bar(self) -> None:
        style = ttk.Style(self._root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "TestApp.Horizontal.TProgressbar",
            troughcolor="#e2e8f0",
            background=_COLOR_ACCENT,
            bordercolor=_COLOR_CARD_BORDER,
            lightcolor=_COLOR_ACCENT,
            darkcolor=_COLOR_ACCENT,
            thickness=14,
        )
        self._progress.configure(style="TestApp.Horizontal.TProgressbar")

    def _run_installation(self) -> None:
        def on_step(step: int, total: int, message: str) -> None:
            self._events.put(("step", step, total, message))

        def on_log(message: str, *, is_error: bool = False) -> None:
            self._events.put(("log", message, is_error))

        try:
            code = run_install_simulation(
                self._scenario,
                quiet=False,
                on_step=on_step,
                on_log=on_log,
            )
            self._events.put(("done", code))
        except Exception as exc:  # noqa: BLE001
            self._events.put(("log", f"Installer error: {exc}", True))
            self._events.put(("done", 1))

    def _poll_events(self) -> None:
        try:
            while True:
                event = self._events.get_nowait()
                self._handle_event(event)
        except queue.Empty:
            pass
        if self._root.winfo_exists():
            self._root.after(80, self._poll_events)

    def _handle_event(self, event: tuple) -> None:
        kind = event[0]
        if kind == "step":
            _, step, total, message = event
            pct = int(round(100 * step / max(total, 1)))
            self._progress["value"] = pct
            self._percent_label.configure(text=f"{pct}% complete")
            self._step_label.configure(text=message)
            self._status_label.configure(text=f"Step {step} of {total}")
            self._append_log(f"[{step}/{total}] {message}")
        elif kind == "log":
            _, message, is_error = event
            self._append_log(message, is_error=is_error)
        elif kind == "done":
            _, exit_code = event
            self._finish(exit_code)

    def _append_log(self, message: str, *, is_error: bool = False) -> None:
        self._log.configure(state=tk.NORMAL)
        tag = "error" if is_error else "info"
        if tag not in self._log.tag_names():
            self._log.tag_configure("error", foreground=_COLOR_ERROR)
            self._log.tag_configure("info", foreground="#1e293b")
        self._log.insert(tk.END, message.strip() + "\n", tag)
        self._log.see(tk.END)
        self._log.configure(state=tk.DISABLED)

    def _finish(self, exit_code: int) -> None:
        if self._finished:
            return
        self._finished = True
        self._exit_code = exit_code
        self._progress["value"] = 100
        self._percent_label.configure(text="100% complete")
        if exit_code == 0:
            self._step_label.configure(text="Installation completed successfully.")
            self._status_label.configure(
                text="Setup finished — SmartInstall AI is analyzing this session.",
                fg=_COLOR_SUCCESS,
            )
            self._append_log("Installation completed successfully.")
        else:
            self._step_label.configure(text=f"Installation failed (exit code {exit_code}).")
            self._status_label.configure(
                text="Setup reported an error — SmartInstall AI will capture troubleshooting evidence.",
                fg=_COLOR_ERROR,
            )
            self._append_log(f"Installation failed with exit code {exit_code}.", is_error=True)
        self._close_btn.configure(state=tk.NORMAL)
        self._root.title(f"{WINDOW_TITLE} — {'Complete' if exit_code == 0 else 'Failed'}")

    def _on_close_while_running(self) -> None:
        if self._finished:
            self._root.destroy()
            return
        self._status_label.configure(
            text="Installation in progress — wait for setup to finish.",
            fg=_COLOR_ERROR,
        )


def _load_logo_image(root: tk.Tk):
    """Load brand logo when packaged or running from the repo."""
    try:
        from tkinter import PhotoImage
    except ImportError:
        return None

    candidates = _logo_candidates()
    for path in candidates:
        if path.is_file():
            try:
                image = PhotoImage(file=str(path))
                # Scale down large logos for the header (Tk limited scaling)
                if image.width() > 48 or image.height() > 48:
                    factor = max(image.width() // 40, image.height() // 40, 1)
                    image = image.subsample(factor, factor)
                return image
            except tk.TclError:
                continue
    return None


def _logo_candidates() -> list[Path]:
    paths: list[Path] = []
    if getattr(sys, "frozen", False):
        bundle = getattr(sys, "_MEIPASS", None)
        exe_dir = Path(sys.executable).resolve().parent
        if bundle:
            paths.extend(
                [
                    Path(bundle) / "images" / "logo.png",
                    Path(bundle) / "assets" / "images" / "logo.png",
                ]
            )
        paths.append(exe_dir / "images" / "logo.png")

    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").is_file() or (parent / "config" / "smartinstall.config.json").is_file():
            paths.append(parent / "images" / "logo.png")
            break
    return paths
