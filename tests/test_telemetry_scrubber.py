"""
test_telemetry_scrubber.py — Tests for telemetry_scrubber.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from telemetry_scrubber import scrub_workspace


class TestScrubWorkspace:
    def test_dry_run_detects_telemetry_file(self, tmp_path: Path) -> None:
        bad_file = tmp_path / ".telemetry"
        bad_file.write_text("data")
        count = scrub_workspace(tmp_path, dry_run=True)
        assert count == 1
        assert bad_file.exists()  # dry run must NOT delete

    def test_dry_run_detects_multiple_patterns(self, tmp_path: Path) -> None:
        (tmp_path / ".analytics").write_text("x")
        (tmp_path / ".crash-report").write_text("x")
        count = scrub_workspace(tmp_path, dry_run=True)
        assert count == 2

    def test_execute_deletes_telemetry_file(self, tmp_path: Path) -> None:
        bad_file = tmp_path / "sentry_dsn.json"
        bad_file.write_text("dsn-value")
        count = scrub_workspace(tmp_path, dry_run=False)
        assert count == 1
        assert not bad_file.exists()

    def test_clean_workspace_returns_zero(self, tmp_path: Path) -> None:
        (tmp_path / "main.py").write_text("print('hello')")
        count = scrub_workspace(tmp_path, dry_run=True)
        assert count == 0

    def test_nonexistent_root_returns_zero(self, tmp_path: Path) -> None:
        count = scrub_workspace(tmp_path / "nonexistent", dry_run=True)
        assert count == 0

    def test_nested_telemetry_detected(self, tmp_path: Path) -> None:
        nested = tmp_path / "subdir"
        nested.mkdir()
        (nested / ".telemetry").write_text("x")
        count = scrub_workspace(tmp_path, dry_run=True)
        assert count == 1

    def test_git_dir_not_scanned(self, tmp_path: Path) -> None:
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / ".analytics").write_text("x")
        count = scrub_workspace(tmp_path, dry_run=True)
        assert count == 0  # .git excluded from walk
