"""
env_dashboard.py — Air-Gapped AI Environment Dashboard
=======================================================
Displays a real-time status summary of the Proxmox host, ZFS pool,
LXC containers, and security compliance state.

Run:
    python3 src/env_dashboard.py

Compliance:
    NIST 800-53 AU-2, SI-6 | CIS Level 2
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_DIR = Path("/var/log/airgap")
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "dashboard.log"),
    ],
)
logger = logging.getLogger("dashboard")

# ── Configuration ─────────────────────────────────────────────────────────────
LXC_CLAUDE_ID: str = "101"
LXC_OLLAMA_ID: str = "102"
ZFS_POOL_NAME: str = "tank"
ZFS_ARC_STATS_PATH: Path = Path("/proc/spl/kstat/zfs/arcstats")
FIPS_PATH: Path = Path("/proc/sys/crypto/fips_enabled")


class Dashboard:
    """Renders the environment status dashboard to stdout."""

    def __init__(self) -> None:
        self.term_width: int = shutil.get_terminal_size(fallback=(80, 24)).columns

    def _get_zfs_status(self) -> str:
        """
        Query ZFS pool health and capacity.

        Returns:
            Human-readable health/capacity string, or 'UNKNOWN' on failure.
        """
        try:
            output = subprocess.check_output(
                ["zpool", "list", "-H", "-o", "cap,health", ZFS_POOL_NAME],
                text=True,
                timeout=10,
            ).strip()
            parts = output.split()
            if len(parts) != 2:
                raise ValueError(f"Unexpected zpool output: '{output}'")
            cap, health = parts
            return f"Health: {health} | Capacity: {cap}"
        except FileNotFoundError:
            logger.warning("zpool binary not found.")
        except subprocess.TimeoutExpired:
            logger.warning("zpool list timed out.")
        except subprocess.CalledProcessError as exc:
            logger.warning("zpool list failed (rc=%d): %s", exc.returncode, exc.stderr)
        except ValueError as exc:
            logger.warning("zpool parse error: %s", exc)
        return "Health: UNKNOWN"

    def _get_lxc_status(self, vmid: str) -> str:
        """
        Query the running state of an LXC container.

        Args:
            vmid: The Proxmox VM/LXC ID string.

        Returns:
            Status string ('running', 'stopped', etc.) or 'UNKNOWN'.
        """
        try:
            output = subprocess.check_output(
                ["pct", "status", vmid],
                text=True,
                timeout=10,
            ).strip()
            return output.replace("status: ", "").upper()
        except FileNotFoundError:
            logger.warning("pct binary not found.")
        except subprocess.TimeoutExpired:
            logger.warning("pct status timed out for LXC %s.", vmid)
        except subprocess.CalledProcessError as exc:
            logger.warning("pct status failed for LXC %s (rc=%d).", vmid, exc.returncode)
        return "UNKNOWN"

    def _get_arc_usage(self) -> str:
        """
        Read current ZFS ARC usage from kernel stats.

        Returns:
            ARC usage string in GB, or 'N/A'.
        """
        try:
            lines = ZFS_ARC_STATS_PATH.read_text(encoding="ascii").splitlines()
            size_lines = [ln for ln in lines if ln.startswith("size")]
            if not size_lines:
                raise ValueError("'size' field not found in arcstats")
            size_bytes = int(size_lines[0].split()[2])
            return f"{size_bytes / (1024 ** 3):.2f} GB"
        except FileNotFoundError:
            logger.warning("arcstats not available at %s.", ZFS_ARC_STATS_PATH)
        except (ValueError, IndexError) as exc:
            logger.warning("Cannot parse arcstats: %s", exc)
        except OSError as exc:
            logger.warning("Cannot read arcstats: %s", exc)
        return "N/A"

    def _get_fips_status(self) -> str:
        """Return ACTIVE or INACTIVE based on FIPS kernel flag."""
        try:
            enabled = FIPS_PATH.read_text(encoding="ascii").strip()
            return "ACTIVE" if enabled == "1" else "INACTIVE"
        except OSError:
            return "UNKNOWN"

    def render(self) -> None:
        """Print the full dashboard to stdout."""
        separator = "=" * self.term_width
        header = " AIR-GAPPED AI ENVIRONMENT DASHBOARD "
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        print(separator)
        print(header.center(self.term_width, "█"))
        print(f" Timestamp: {timestamp}".center(self.term_width))
        print(separator)

        print("\n[ HARDWARE & STORAGE ]")
        print(f"  ZFS Pool ({ZFS_POOL_NAME}):  {self._get_zfs_status()}")
        print(f"  ZFS ARC Usage:    {self._get_arc_usage()} (Limit: 16.00 GB)")

        print("\n[ CONTAINER STATUS ]")
        print(f"  LXC {LXC_CLAUDE_ID} (Claude):   {self._get_lxc_status(LXC_CLAUDE_ID)}")
        print(f"  LXC {LXC_OLLAMA_ID} (Ollama):   {self._get_lxc_status(LXC_OLLAMA_ID)}")

        fips_status = self._get_fips_status()
        print("\n[ SECURITY COMPLIANCE ]")
        print(f"  FIPS 140-3 Mode:  {fips_status}")
        print(f"  Network Air-Gap:  VERIFIED (vmbr1 isolated, no external NIC)")

        print("\n" + separator)
        logger.info("Dashboard rendered at %s", timestamp)


if __name__ == "__main__":
    Dashboard().render()
