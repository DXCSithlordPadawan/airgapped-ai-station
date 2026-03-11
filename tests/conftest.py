"""
conftest.py — Shared pytest fixtures for Air-Gapped AI Station tests
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture()
def tmp_workspace(tmp_path: Path) -> Path:
    """Return a temporary workspace directory with standard sub-paths."""
    (tmp_path / "tank" / "workspace").mkdir(parents=True)
    (tmp_path / "etc" / "pve" / "lxc").mkdir(parents=True)
    (tmp_path / "etc" / "zfs" / "keys").mkdir(parents=True)
    return tmp_path


@pytest.fixture()
def lxc_config_dir(tmp_path: Path) -> Path:
    """Create a temporary LXC config directory with sample configs."""
    lxc_dir = tmp_path / "lxc"
    lxc_dir.mkdir()
    (lxc_dir / "101.conf").write_text("unprivileged: 1\ncores: 12\n")
    (lxc_dir / "102.conf").write_text("unprivileged: 1\ncores: 24\n")
    return lxc_dir


@pytest.fixture()
def privileged_lxc_config_dir(tmp_path: Path) -> Path:
    """LXC config dir where one container is privileged (compliance failure)."""
    lxc_dir = tmp_path / "lxc_priv"
    lxc_dir.mkdir()
    (lxc_dir / "101.conf").write_text("unprivileged: 1\n")
    (lxc_dir / "999.conf").write_text("cores: 4\n")  # missing unprivileged: 1
    return lxc_dir
