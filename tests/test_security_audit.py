"""
test_security_audit.py — Tests for security_compliance_audit.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from security_compliance_audit import AuditReport, Finding, ProxmoxAuditor


class TestFinding:
    def test_finding_fields(self) -> None:
        f = Finding(check="FIPS_MODE", status="PASS", detail="Active.")
        assert f.check == "FIPS_MODE"
        assert f.status == "PASS"

    def test_finding_fail_status(self) -> None:
        f = Finding(check="FIPS_MODE", status="FAIL", detail="Disabled.")
        assert f.status == "FAIL"


class TestAuditReport:
    def test_initial_status_is_pass(self) -> None:
        report = AuditReport(hostname="test", timestamp="now", overall_status="PASS")
        assert report.overall_status == "PASS"

    def test_fail_finding_degrades_status(self) -> None:
        report = AuditReport(hostname="test", timestamp="now", overall_status="PASS")
        report.add(Finding("X", "FAIL", "bad"))
        assert report.overall_status == "FAIL"

    def test_warn_finding_sets_warn_when_passing(self) -> None:
        report = AuditReport(hostname="test", timestamp="now", overall_status="PASS")
        report.add(Finding("X", "WARN", "marginal"))
        assert report.overall_status == "WARN"

    def test_fail_not_overridden_by_warn(self) -> None:
        report = AuditReport(hostname="test", timestamp="now", overall_status="PASS")
        report.add(Finding("A", "FAIL", "bad"))
        report.add(Finding("B", "WARN", "marginal"))
        assert report.overall_status == "FAIL"


class TestProxmoxAuditor:
    def test_check_fips_pass(self) -> None:
        auditor = ProxmoxAuditor()
        with patch("pathlib.Path.read_text", return_value="1\n"):
            auditor.check_fips()
        finding = auditor.report.findings[0]
        assert finding.status == "PASS"
        assert finding.check == "FIPS_MODE"

    def test_check_fips_fail(self) -> None:
        auditor = ProxmoxAuditor()
        with patch("pathlib.Path.read_text", return_value="0\n"):
            auditor.check_fips()
        finding = auditor.report.findings[0]
        assert finding.status == "FAIL"

    def test_check_fips_missing_file(self) -> None:
        auditor = ProxmoxAuditor()
        with patch("pathlib.Path.read_text", side_effect=FileNotFoundError):
            auditor.check_fips()
        finding = auditor.report.findings[0]
        assert finding.status == "FAIL"

    def test_check_arc_limit_pass(self) -> None:
        # 8 GB — below the 16 GB limit
        eight_gb = str(8 * 1024 * 1024 * 1024)
        auditor = ProxmoxAuditor()
        with patch("pathlib.Path.read_text", return_value=eight_gb + "\n"):
            auditor.check_arc_limit()
        finding = auditor.report.findings[0]
        assert finding.status == "PASS"

    def test_check_arc_limit_warn_over(self) -> None:
        # 32 GB — above the 16 GB limit
        thirty_two_gb = str(32 * 1024 * 1024 * 1024)
        auditor = ProxmoxAuditor()
        with patch("pathlib.Path.read_text", return_value=thirty_two_gb + "\n"):
            auditor.check_arc_limit()
        finding = auditor.report.findings[0]
        assert finding.status == "WARN"

    def test_audit_lxc_privileges_pass(self, lxc_config_dir: Path) -> None:
        auditor = ProxmoxAuditor()
        with patch("security_compliance_audit.LXC_CONFIG_DIR", lxc_config_dir):
            auditor.audit_lxc_privileges()
        statuses = [f.status for f in auditor.report.findings]
        assert all(s == "PASS" for s in statuses)

    def test_audit_lxc_privileges_fail_privileged(
        self, privileged_lxc_config_dir: Path
    ) -> None:
        auditor = ProxmoxAuditor()
        with patch("security_compliance_audit.LXC_CONFIG_DIR", privileged_lxc_config_dir):
            auditor.audit_lxc_privileges()
        statuses = {f.status for f in auditor.report.findings}
        assert "FAIL" in statuses
