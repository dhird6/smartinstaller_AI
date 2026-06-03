#!/usr/bin/env python3
"""Desktop entry point: python desktop.py (use the project .venv — see README)."""

from __future__ import annotations

import sys


def _ensure_pyside6() -> None:
    try:
        import PySide6  # noqa: F401
    except ModuleNotFoundError:
        print(
            "PySide6 is not installed for this Python interpreter:\n"
            f"  {sys.executable}\n\n"
            "Use the project virtual environment:\n"
            "  .\\.venv\\Scripts\\Activate.ps1\n"
            "  pip install -e \".[desktop]\"\n"
            "  python desktop.py\n\n"
            "Or install desktop deps into the current interpreter:\n"
            '  pip install "PySide6>=6.6,<7"',
            file=sys.stderr,
        )
        raise SystemExit(1) from None


_ensure_pyside6()

from smartinstall.ui.main import main

if __name__ == "__main__":
    main()
