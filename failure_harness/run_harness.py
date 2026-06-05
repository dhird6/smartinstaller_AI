#!/usr/bin/env python3
"""CLI wrapper — delegates to failure_harness.run_cli."""

import sys
from pathlib import Path

_src = Path(__file__).resolve().parent.parent / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from failure_harness.run_cli import main

if __name__ == "__main__":
    raise SystemExit(main())
