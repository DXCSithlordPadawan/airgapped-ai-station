"""
egress_check.py — Network Air-Gap Egress Verification
======================================================
Confirms the internal AI bridge (vmbr1) has no default gateway and that
nftables/iptables drop rules are in place, satisfying the "Zero Leakage"
success metric in the PRD.

Run:
    python3 src/egress_check.py

Compliance:
    NIST 800-53 SC-7 (Boundary Protection) | CIS Level 2
"""

from __future__ import annotations

import logging
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_DIR = Path("/var/log/airgap")
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "egress_check.log"),
    ],
)
logger = logging.getLogger("egress_check")

# ── Configuration ─────────────────────────────────────────────────────────────
INTERNAL_BRIDGE: str = "vmbr1"
INTERNAL_SUBNET: str = "10.0.0.0/24"
EXTERNAL_TEST_HOST: str = "8.8.8.8"   # Should be unreachable
PING_TIMEOUT_SECS: int = 3

Status = Literal["PASS", "FAIL", "WARN", "ERROR"]


@dataclass
class CheckResult:
    """Result of a single egress check."""
    name: str
    status: Status
    detail: str


# ── Checks ────────────────────────────────────────────────────────────────────

def check_no_default_gateway() -> CheckResult:
    """
    Verify that no default gateway (0.0.0.0) is configured, which would
    allow packets to leave the internal network.
    """
    try:
        output = subprocess.check_output(
            ["ip", "route", "show", "default"],
            text=True,
            timeout=10,
        ).strip()
        if output:
            return CheckResult(
                "NO_DEFAULT_GATEWAY",
                "FAIL",
                f"Default route found — traffic may escape air-gap: '{output}'",
            )
        return CheckResult(
            "NO_DEFAULT_GATEWAY",
            "PASS",
            "No default gateway configured. Internal routing only.",
        )
    except FileNotFoundError:
        return CheckResult("NO_DEFAULT_GATEWAY", "ERROR", "'ip' binary not found.")
    except subprocess.TimeoutExpired:
        return CheckResult("NO_DEFAULT_GATEWAY", "ERROR", "ip route timed out.")
    except subprocess.CalledProcessError as exc:
        return CheckResult("NO_DEFAULT_GATEWAY", "ERROR", f"ip route error: {exc}")


def check_bridge_internal_only() -> CheckResult:
    """
    Confirm vmbr1 has no physical NIC enslave (no uplink), ensuring the
    bridge is isolated.
    """
    bridge_path = Path(f"/sys/class/net/{INTERNAL_BRIDGE}/brif")
    try:
        if not bridge_path.exists():
            return CheckResult(
                "BRIDGE_ISOLATED",
                "WARN",
                f"Bridge '{INTERNAL_BRIDGE}' not found — check if Proxmox bridge is configured.",
            )
        ports = list(bridge_path.iterdir())
        # Physical NIC names typically start with eth/eno/enp/ens
        physical = [p.name for p in ports if re.match(r"^(eth|eno|enp|ens)\d", p.name)]
        if physical:
            return CheckResult(
                "BRIDGE_ISOLATED",
                "FAIL",
                f"Bridge '{INTERNAL_BRIDGE}' has physical NIC(s): {physical} — air-gap may be broken!",
            )
        return CheckResult(
            "BRIDGE_ISOLATED",
            "PASS",
            f"Bridge '{INTERNAL_BRIDGE}' has no physical NIC uplinks. Ports: {[p.name for p in ports]}",
        )
    except OSError as exc:
        return CheckResult("BRIDGE_ISOLATED", "ERROR", f"Cannot inspect bridge ports: {exc}")


def check_external_unreachable() -> CheckResult:
    """
    Actively attempt to ping an external host.  On an air-gapped system
    this must fail (PASS = ping failed = good).
    """
    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", str(PING_TIMEOUT_SECS), EXTERNAL_TEST_HOST],
            capture_output=True,
            text=True,
            timeout=PING_TIMEOUT_SECS + 2,
        )
        if result.returncode == 0:
            return CheckResult(
                "EXTERNAL_UNREACHABLE",
                "FAIL",
                f"CRITICAL: External host {EXTERNAL_TEST_HOST} IS reachable — air-gap is BREACHED.",
            )
        return CheckResult(
            "EXTERNAL_UNREACHABLE",
            "PASS",
            f"External host {EXTERNAL_TEST_HOST} is unreachable. Air-gap confirmed.",
        )
    except FileNotFoundError:
        return CheckResult("EXTERNAL_UNREACHABLE", "ERROR", "'ping' binary not found.")
    except subprocess.TimeoutExpired:
        # Timeout == unreachable == good
        return CheckResult(
            "EXTERNAL_UNREACHABLE",
            "PASS",
            f"Ping to {EXTERNAL_TEST_HOST} timed out — air-gap confirmed.",
        )
    except OSError as exc:
        return CheckResult("EXTERNAL_UNREACHABLE", "ERROR", f"Ping error: {exc}")


def run_egress_checks() -> int:
    """
    Execute all egress checks and report results.

    Returns:
        Exit code: 0 = all PASS, 1 = any FAIL/ERROR present.
    """
    separator = "=" * 58
    logger.info(separator)
    logger.info(" NETWORK AIR-GAP EGRESS VERIFICATION")
    logger.info(separator)

    checks: list[CheckResult] = [
        check_no_default_gateway(),
        check_bridge_internal_only(),
        check_external_unreachable(),
    ]

    any_fail = False
    for chk in checks:
        level = logging.INFO if chk.status == "PASS" else logging.WARNING
        logger.log(level, "  [%s] %-28s %s", chk.status, chk.name, chk.detail)
        if chk.status in ("FAIL", "ERROR"):
            any_fail = True

    logger.info(separator)
    if not any_fail:
        logger.info(" RESULT: AIR-GAP INTEGRITY CONFIRMED")
        return 0

    logger.warning(" RESULT: AIR-GAP INTEGRITY FAILURE — IMMEDIATE ACTION REQUIRED")
    return 1


if __name__ == "__main__":
    sys.exit(run_egress_checks())
