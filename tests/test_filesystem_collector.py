"""Tests for filesystem snapshot diff."""

from pathlib import Path

from smartinstall.agent.collectors.filesystem_collector import FilesystemCollector


def test_detects_created_file(tmp_path: Path) -> None:
    root = tmp_path / "watch"
    root.mkdir()
    collector = FilesystemCollector([str(root)], max_events=100, max_depth=2)
    collector.take_pre_snapshot()

    new_file = root / "installed.txt"
    new_file.write_text("ok", encoding="utf-8")

    result = collector.collect()
    assert any(change.change_type == "created" for change in result.changes)
