"""
check_manifest_integrity.py — Air-Gap File & Permission Auditor
===============================================================
Verifies that all files defined in the system manifest exist on disk
with the correct permissions.

Run:
    python3 src/check_manifest_integrity.py

Compliance:
    NIST 800-53 AU-2, AU-9 | CIS Level 2 | FIPS 140-3 environment
"""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_DIR = Path("/var/log/airgap")
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            LOG_DIR / f"manifest_audit_{datetime.now(timezone.utc).strftime('%Y%m%d')}.log"
        ),
    ],
)
logger = logging.getLogger("manifest_integrity")

# ── Manifest Definition ───────────────────────────────────────────────────────

@dataclass
class ManifestEntry:
    """A single expected file entry in the manifest."""
    path: str
    perm: str
    is_dir: bool = False
    description: str = ""


# Expected system state — update when adding new files
MANIFEST: dict[str, list[ManifestEntry]] = {
    "Host": [
        ManifestEntry(
            path="/etc/systemd/system/zfs-load-keys.service",
            perm="644",
            description="ZFS key loader systemd unit",
        ),
        ManifestEntry(
            path="/usr/local/bin/zfs-key-manager.sh",
            perm="755",
            description="ZFS key lifecycle manager",
        ),
        ManifestEntry(
            path="/etc/zfs/keys/",
            perm="700",
            is_dir=True,
            description="AES-256-GCM key store — host-only",
        ),
    ],
    "LXC_Configs": [
        ManifestEntry(path="/etc/pve/lxc/101.conf", perm="600", description="LXC 101 config"),
        ManifestEntry(path="/etc/pve/lxc/102.conf", perm="600", description="LXC 102 config"),
    ],
    "Workspace": [
        ManifestEntry(path="/tank/workspace/CLAUDE.md", perm="644", description="Agent rules"),
        ManifestEntry(
            path="/tank/workspace/.claude.env",
            perm="600",
            description="API redirect config — must be 600",
        ),
        ManifestEntry(
            path="/tank/workspace/python-sandbox.Containerfile",
            perm="644",
            description="Podman sandbox image definition",
        ),
    ],
}


# ── Audit Logic ───────────────────────────────────────────────────────────────

@dataclass
class AuditResult:
    """Result of a single manifest entry check."""
    entry: ManifestEntry
    passed: bool
    message: str


def verify_entry(entry: ManifestEntry) -> AuditResult:
    """
    Verify a single manifest entry exists and has the correct permissions.

    Args:
        entry: The ManifestEntry to validate.

    Returns:
        AuditResult with pass/fail status and human-readable message.
    """
    target = Path(entry.path)

    # ── Existence check ───────────────────────────────────────────────────────
    if not target.exists():
        msg = f"MISSING: {entry.path}"
        logger.warning(msg)
        return AuditResult(entry=entry, passed=False, message=msg)

    # ── Permission check ──────────────────────────────────────────────────────
    try:
        current_perm = oct(target.stat().st_mode)[-3:]
    except OSError as exc:
        msg = f"STAT_ERROR: {entry.path} — {exc}"
        logger.error(msg)
        return AuditResult(entry=entry, passed=False, message=msg)

    if current_perm != entry.perm:
        msg = (
            f"PERM_MISMATCH: {entry.path} "
            f"(found {current_perm}, expected {entry.perm})"
        )
        logger.warning(msg)
        return AuditResult(entry=entry, passed=False, message=msg)

    msg = f"OK: {entry.path} [{current_perm}]"
    logger.info(msg)
    return AuditResult(entry=entry, passed=True, message=msg)


def run_audit() -> int:
    """
    Execute the full manifest audit.

    Returns:
        Exit code: 0 = compliant, 1 = non-compliant.
    """
    separator = "=" * 62
    logger.info(separator)
    logger.info(" AIR-GAP MANIFEST INTEGRITY CHECK")
    logger.info(" Timestamp: %s", datetime.now(timezone.utc).isoformat())
    logger.info(separator)

    total = 0
    failures = 0

    for category, entries in MANIFEST.items():
        logger.info("[ %s ]", category)
        for entry in entries:
            result = verify_entry(entry)
            total += 1
            if not result.passed:
                failures += 1

    logger.info(separator)
    if failures == 0:
        logger.info(" RESULT: SYSTEM COMPLIANT (%d/%d checks passed)", total, total)
        return 0

    logger.warning(
        " RESULT: NON-COMPLIANT — %d/%d checks FAILED — ATTENTION REQUIRED",
        failures,
        total,
    )
    return 1


if __name__ == "__main__":
    sys.exit(run_audit())
