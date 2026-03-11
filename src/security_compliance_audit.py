"""
security_compliance_audit.py — Proxmox Security & Compliance Auditor
=====================================================================
Checks FIPS 140-3 mode, ZFS ARC limits, and LXC unprivileged status.
Writes a timestamped JSON audit record in addition to console output.

Run:
    python3 src/security_compliance_audit.py

Compliance:
    NIST 800-53 AC-3, AU-2, AU-9 | FIPS 140-3 | CIS Level 2
"""

from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_DIR = Path("/var/log/airgap")
LOG_DIR.mkdir(parents=True, exist_ok=True)

_ts = datetime.now(timezone.utc).strftime("%Y%m%d")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / f"compliance_audit_{_ts}.log"),
    ],
)
logger = logging.getLogger("compliance_audit")

# ── Constants ─────────────────────────────────────────────────────────────────
ZFS_ARC_MAX_BYTES: int = 16 * 1024 * 1024 * 1024  # 16 GB target for T5500
LXC_CONFIG_DIR: Path = Path("/etc/pve/lxc")
AUDIT_OUTPUT_DIR: Path = Path("/var/log/airgap/audit_reports")

Status = Literal["PASS", "FAIL", "WARN", "ERROR"]


# ── Data Model ────────────────────────────────────────────────────────────────

@dataclass
class Finding:
    """A single audit finding."""
    check: str
    status: Status
    detail: str


@dataclass
class AuditReport:
    """Full audit report — serialised to JSON on completion."""
    hostname: str
    timestamp: str
    overall_status: Status
    findings: list[Finding] = field(default_factory=list)

    def add(self, finding: Finding) -> None:
        """Add a finding and update overall status if it degrades."""
        self.findings.append(finding)
        if finding.status == "FAIL":
            self.overall_status = "FAIL"
        elif finding.status == "WARN" and self.overall_status not in ("FAIL",):
            self.overall_status = "WARN"

    def save(self) -> Path:
        """Persist the report as a JSON file and return the path."""
        AUDIT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        ts_safe = self.timestamp.replace(":", "-").replace("+", "Z")
        output_path = AUDIT_OUTPUT_DIR / f"audit_{ts_safe}.json"
        try:
            with output_path.open("w", encoding="utf-8") as fp:
                json.dump(asdict(self), fp, indent=2)
            logger.info("Audit report written to: %s", output_path)
        except OSError as exc:
            logger.error("Failed to write audit report: %s", exc)
        return output_path


# ── Audit Checks ──────────────────────────────────────────────────────────────

class ProxmoxAuditor:
    """Runs compliance checks against the Proxmox host environment."""

    def __init__(self) -> None:
        self.report = AuditReport(
            hostname=os.uname().nodename,
            timestamp=datetime.now(timezone.utc).isoformat(),
            overall_status="PASS",
        )

    def check_fips(self) -> None:
        """Verify FIPS 140-3 kernel mode is active (NIST SC-13)."""
        fips_path = Path("/proc/sys/crypto/fips_enabled")
        try:
            enabled = fips_path.read_text(encoding="ascii").strip()
            if enabled == "1":
                self.report.add(Finding("FIPS_MODE", "PASS", "FIPS 140-3 kernel mode is active."))
            else:
                self.report.add(
                    Finding("FIPS_MODE", "FAIL", "FIPS mode is DISABLED — kernel flag fips=1 required.")
                )
        except FileNotFoundError:
            self.report.add(
                Finding("FIPS_MODE", "FAIL", f"FIPS node not found at {fips_path}.")
            )
        except OSError as exc:
            self.report.add(Finding("FIPS_MODE", "ERROR", f"Cannot read FIPS state: {exc}"))

    def check_arc_limit(self) -> None:
        """Verify ZFS ARC is capped to protect LLM RAM headroom."""
        arc_path = Path("/sys/module/zfs/parameters/zfs_arc_max")
        try:
            raw = arc_path.read_text(encoding="ascii").strip()
            current = int(raw)
            gb = current / (1024 ** 3)
            if current <= ZFS_ARC_MAX_BYTES:
                self.report.add(
                    Finding("ZFS_ARC_MAX", "PASS", f"ZFS ARC limited to {gb:.2f} GB.")
                )
            else:
                self.report.add(
                    Finding(
                        "ZFS_ARC_MAX",
                        "WARN",
                        f"ZFS ARC is {gb:.2f} GB — exceeds 16 GB target. LLM RAM may be constrained.",
                    )
                )
        except FileNotFoundError:
            self.report.add(
                Finding("ZFS_ARC_MAX", "ERROR", f"ZFS ARC parameter not found at {arc_path}.")
            )
        except ValueError as exc:
            self.report.add(Finding("ZFS_ARC_MAX", "ERROR", f"Non-numeric ARC value: {exc}"))
        except OSError as exc:
            self.report.add(Finding("ZFS_ARC_MAX", "ERROR", f"Cannot read ARC settings: {exc}"))

    def audit_lxc_privileges(self) -> None:
        """Ensure all LXC containers are unprivileged (CIS Level 2, DISA STIG)."""
        if not LXC_CONFIG_DIR.is_dir():
            self.report.add(
                Finding(
                    "LXC_PRIVILEGE",
                    "ERROR",
                    f"LXC config directory not found: {LXC_CONFIG_DIR}",
                )
            )
            return

        try:
            config_files = [
                f for f in LXC_CONFIG_DIR.iterdir()
                if f.suffix == ".conf" and f.name.replace(".conf", "").isdigit()
            ]
        except OSError as exc:
            self.report.add(
                Finding("LXC_PRIVILEGE", "ERROR", f"Cannot list LXC configs: {exc}")
            )
            return

        if not config_files:
            self.report.add(
                Finding("LXC_PRIVILEGE", "WARN", "No LXC config files found.")
            )
            return

        for config_path in sorted(config_files):
            vmid = config_path.stem
            try:
                content = config_path.read_text(encoding="utf-8")
            except OSError as exc:
                self.report.add(
                    Finding(f"LXC_{vmid}_PRIVILEGE", "ERROR", f"Cannot read {config_path}: {exc}")
                )
                continue

            if "unprivileged: 1" in content:
                self.report.add(
                    Finding(f"LXC_{vmid}_PRIVILEGE", "PASS", f"LXC {vmid} is unprivileged.")
                )
            else:
                self.report.add(
                    Finding(
                        f"LXC_{vmid}_PRIVILEGE",
                        "FAIL",
                        f"LXC {vmid} IS PRIVILEGED — compliance violation.",
                    )
                )

    def run(self) -> int:
        """
        Execute all checks, log results, save report.

        Returns:
            Exit code: 0 = PASS/WARN, 1 = FAIL/ERROR.
        """
        logger.info("─" * 54)
        logger.info(" Proxmox Security Audit Initialised")
        logger.info(" Host: %s | Time: %s", self.report.hostname, self.report.timestamp)
        logger.info("─" * 54)

        self.check_fips()
        self.check_arc_limit()
        self.audit_lxc_privileges()

        for finding in self.report.findings:
            level = logging.WARNING if finding.status in ("FAIL", "WARN", "ERROR") else logging.INFO
            logger.log(level, "[%s] %s — %s", finding.status, finding.check, finding.detail)

        logger.info("─" * 54)
        logger.info(" Overall Status: %s", self.report.overall_status)

        self.report.save()

        return 0 if self.report.overall_status in ("PASS", "WARN") else 1


if __name__ == "__main__":
    sys.exit(ProxmoxAuditor().run())
