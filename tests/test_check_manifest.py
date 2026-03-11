"""
test_check_manifest.py — Tests for check_manifest_integrity.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Ensure src/ is importable
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from check_manifest_integrity import ManifestEntry, verify_entry, AuditResult


class TestVerifyEntry:
    """Unit tests for the verify_entry function."""

    def test_pass_on_existing_file_correct_perm(self, tmp_path: Path) -> None:
        target = tmp_path / "testfile.txt"
        target.write_text("data")
        target.chmod(0o644)
        entry = ManifestEntry(path=str(target), perm="644")
        result = verify_entry(entry)
        assert result.passed is True
        assert "OK" in result.message

    def test_fail_on_missing_file(self, tmp_path: Path) -> None:
        entry = ManifestEntry(path=str(tmp_path / "nonexistent.key"), perm="600")
        result = verify_entry(entry)
        assert result.passed is False
        assert "MISSING" in result.message

    def test_warn_on_wrong_permissions(self, tmp_path: Path) -> None:
        target = tmp_path / "secret.key"
        target.write_text("key-material")
        target.chmod(0o644)  # should be 600
        entry = ManifestEntry(path=str(target), perm="600")
        result = verify_entry(entry)
        assert result.passed is False
        assert "PERM_MISMATCH" in result.message

    def test_pass_on_directory_correct_perm(self, tmp_path: Path) -> None:
        keys_dir = tmp_path / "keys"
        keys_dir.mkdir()
        keys_dir.chmod(0o700)
        entry = ManifestEntry(path=str(keys_dir), perm="700", is_dir=True)
        result = verify_entry(entry)
        assert result.passed is True

    def test_returns_audit_result_type(self, tmp_path: Path) -> None:
        entry = ManifestEntry(path=str(tmp_path / "missing"), perm="644")
        result = verify_entry(entry)
        assert isinstance(result, AuditResult)


class TestManifestEntry:
    """Tests for ManifestEntry dataclass defaults."""

    def test_default_is_dir_false(self) -> None:
        entry = ManifestEntry(path="/some/path", perm="644")
        assert entry.is_dir is False

    def test_description_defaults_empty(self) -> None:
        entry = ManifestEntry(path="/some/path", perm="644")
        assert entry.description == ""
