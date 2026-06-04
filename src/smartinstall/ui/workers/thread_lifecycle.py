"""Safe start/stop helpers for Qt background workers."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QThread


def stop_qthread(worker: QThread | None, *, wait_ms: int = 30_000) -> None:
    """Block until the worker finishes or wait_ms elapses."""
    if worker is None:
        return
    try:
        if worker.isRunning():
            worker.wait(wait_ms)
    except RuntimeError:
        # C++ object already deleted
        return


def wire_worker_lifetime(
    worker: QThread,
    *,
    on_finished: Callable[[], None] | None = None,
) -> None:
    """Keep worker alive until the thread exits, then schedule deletion."""

    def _finished() -> None:
        if on_finished is not None:
            on_finished()
        worker.deleteLater()

    worker.finished.connect(_finished)
