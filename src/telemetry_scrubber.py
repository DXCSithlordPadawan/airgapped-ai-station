"""
telemetry_scrubber.py — Workspace Telemetry Artefact Scanner
=============================================================
Scans the workspace for known telemetry, analytics, and crash-report
artefacts.  Uses a --dry-run / --execute flag pattern so the operator
consciously chooses between audit-only and remediation modes.

Usage:
    python3 src/telemetry_scrubber.py --dry-run    # Scan and report only
    python3 src/telemetry_scrubber.py --execute    # Scan and DELETE matches

Compliance:
    NIST 800-53 SI-12 | CIS Level 2
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_DIR = Path("/var/log/airgap")
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "telemetry_scrubber.log"),
    ],
)
logger = logging.getLogger("telemetry_scrubber")

# ── Known telemetry patterns ──────────────────────────────────────────────────
BANNED_PATTERNS: tuple[str, ...] = (
    ".telemetry",
    ".analytics",
    ".crash-report",
    "sentry_dsn",
    ".sentry",
    "crashpad",
    ".heartbeat",
)


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Scan workspace for telemetry artefacts.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python3 telemetry_scrubber.py --dry-run\n"
            "  python3 telemetry_scrubber.py --execute\n"
        ),
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Scan and report matches without deleting anything.",
    )
    mode.add_argument(
        "--execute",
        action="store_true",
        help="Scan and permanently DELETE matched artefacts.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("/src"),
        help="Workspace root to scan (default: /src).",
    )
    return parser


def scrub_workspace(root_path: Path, *, dry_run: bool) -> int:
    """
    Walk root_path and flag (or remove) telemetry artefacts.

    Args:
        root_path: The directory to scan.
        dry_run:   If True, log findings only.  If False, delete matches.

    Returns:
        Count of matched artefacts found.
    """
    mode_label = "DRY-RUN" if dry_run else "EXECUTE"
    logger.info("[%s] Scanning workspace: %s", mode_label, root_path)

    if not root_path.is_dir():
        logger.error("Root path does not exist or is not a directory: %s", root_path)
        return 0

    found: int = 0

    for dirpath, dirnames, filenames in os.walk(root_path, topdown=True):
        # Avoid descending into .git or __pycache__
        dirnames[:] = [d for d in dirnames if d not in {".git", "__pycache__"}]

        for name in filenames + dirnames:
            lower_name = name.lower()
            if any(pattern in lower_name for pattern in BANNED_PATTERNS):
                full_path = Path(dirpath) / name
                found += 1
                if dry_run:
                    logger.warning("[FOUND] Telemetry artefact: %s", full_path)
                else:
                    try:
                        full_path.unlink(missing_ok=True)
                        logger.warning("[DELETED] Removed telemetry artefact: %s", full_path)
                    except OSError as exc:
                        logger.error("[ERROR] Failed to delete %s: %s", full_path, exc)

    logger.info("[%s] Scan complete. %d artefact(s) found.", mode_label, found)
    return found


def main() -> int:
    """Entry point."""
    parser = build_arg_parser()
    args = parser.parse_args()

    count = scrub_workspace(args.root, dry_run=args.dry_run)

    if args.dry_run and count > 0:
        logger.warning(
            "Re-run with --execute to permanently remove %d artefact(s).", count
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
