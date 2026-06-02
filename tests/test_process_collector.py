"""Tests for process collector exit-code handling."""

from unittest.mock import MagicMock

import psutil

from smartinstall.agent.collectors.process_collector import ProcessCollector, _read_exit_code


def test_read_exit_code_uses_wait_not_returncode() -> None:
    proc = MagicMock(spec=psutil.Process)
    proc.is_running.return_value = False
    proc.wait.return_value = 1
    assert _read_exit_code(proc) == 1
    proc.wait.assert_called_once_with(timeout=0)


def test_finalize_records_exited_child_via_wait() -> None:
    collector = ProcessCollector()
    child = MagicMock(spec=psutil.Process)
    child.is_running.return_value = False
    child.wait.return_value = 0
    child.name.return_value = "helper.exe"
    child.ppid.return_value = 10
    child.cmdline.return_value = ["helper.exe"]
    child.exe.return_value = "C:\\helper.exe"

    root = MagicMock(spec=psutil.Process)
    root.is_running.return_value = True

    collector._root_pid = 10
    collector._handles = {10: root, 99: child}
    collector._tracking = False

    result = collector.finalize()
    assert len(result.child_processes) == 1
    assert result.child_processes[0].process_id == 99
    child.wait.assert_called_once_with(timeout=0)
