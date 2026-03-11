"""
test_env_dashboard.py — Tests for env_dashboard.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from env_dashboard import Dashboard


class TestDashboardZfsStatus:
    def test_returns_health_and_capacity(self) -> None:
        d = Dashboard()
        with patch("env_dashboard.subprocess.check_output", return_value="42%\tONLINE\n"):
            result = d._get_zfs_status()
        assert "ONLINE" in result
        assert "42%" in result

    def test_returns_unknown_on_file_not_found(self) -> None:
        d = Dashboard()
        with patch("env_dashboard.subprocess.check_output", side_effect=FileNotFoundError):
            result = d._get_zfs_status()
        assert "UNKNOWN" in result

    def test_returns_unknown_on_bad_output_format(self) -> None:
        d = Dashboard()
        with patch("env_dashboard.subprocess.check_output", return_value="single_token\n"):
            result = d._get_zfs_status()
        assert "UNKNOWN" in result


class TestDashboardLxcStatus:
    def test_returns_running(self) -> None:
        d = Dashboard()
        with patch("env_dashboard.subprocess.check_output", return_value="status: running\n"):
            result = d._get_lxc_status("101")
        assert result == "RUNNING"

    def test_returns_unknown_on_error(self) -> None:
        d = Dashboard()
        import subprocess
        with patch(
            "env_dashboard.subprocess.check_output",
            side_effect=subprocess.CalledProcessError(1, "pct"),
        ):
            result = d._get_lxc_status("101")
        assert result == "UNKNOWN"


class TestDashboardFips:
    def test_active_when_fips_enabled(self, tmp_path: Path) -> None:
        fips_file = tmp_path / "fips_enabled"
        fips_file.write_text("1\n")
        d = Dashboard()
        with patch("env_dashboard.FIPS_PATH", fips_file):
            result = d._get_fips_status()
        assert result == "ACTIVE"

    def test_inactive_when_fips_disabled(self, tmp_path: Path) -> None:
        fips_file = tmp_path / "fips_enabled"
        fips_file.write_text("0\n")
        d = Dashboard()
        with patch("env_dashboard.FIPS_PATH", fips_file):
            result = d._get_fips_status()
        assert result == "INACTIVE"

    def test_unknown_when_file_missing(self, tmp_path: Path) -> None:
        d = Dashboard()
        with patch("env_dashboard.FIPS_PATH", tmp_path / "nonexistent"):
            result = d._get_fips_status()
        assert result == "UNKNOWN"


class TestDashboardArcUsage:
    def test_parses_arc_size(self, tmp_path: Path) -> None:
        arc_file = tmp_path / "arcstats"
        # Write a minimal arcstats with 8 GB size
        eight_gb = 8 * 1024 ** 3
        arc_file.write_text(f"size            4    {eight_gb}\n")
        d = Dashboard()
        with patch("env_dashboard.ZFS_ARC_STATS_PATH", arc_file):
            result = d._get_arc_usage()
        assert "8.00" in result

    def test_returns_na_when_missing(self, tmp_path: Path) -> None:
        d = Dashboard()
        with patch("env_dashboard.ZFS_ARC_STATS_PATH", tmp_path / "nofile"):
            result = d._get_arc_usage()
        assert result == "N/A"
