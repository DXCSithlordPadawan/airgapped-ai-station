"""
smoke_test_agent.py — Pre-Flight Environment Validator
======================================================
Verifies Ollama reachability, model availability, and Podman sandbox
functionality before starting a Claude Code session.

Run:
    python3 src/smoke_test_agent.py

Compliance:
    NIST 800-53 SI-6 | CIS Level 2
"""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path
from typing import Optional

import requests

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_DIR = Path("/var/log/airgap")
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "smoke_test.log"),
    ],
)
logger = logging.getLogger("smoke_test")

# ── Configuration ─────────────────────────────────────────────────────────────
OLLAMA_HOST: str = "http://10.0.0.102:11434"
OLLAMA_GENERATE_URL: str = f"{OLLAMA_HOST}/api/generate"
OLLAMA_TAGS_URL: str = f"{OLLAMA_HOST}/api/tags"
REQUIRED_MODEL: str = "qwen2.5-coder:32b"
HTTP_TIMEOUT_SECS: int = 10


# ── Checks ────────────────────────────────────────────────────────────────────

def verify_inference_reachable() -> bool:
    """
    Confirm the Ollama HTTP endpoint responds on the internal bridge.

    Returns:
        True if Ollama responds with HTTP 200, False otherwise.
    """
    logger.info("Testing inference link: %s", OLLAMA_GENERATE_URL)
    try:
        payload = {"model": REQUIRED_MODEL, "prompt": "ping", "stream": False}
        response = requests.post(OLLAMA_GENERATE_URL, json=payload, timeout=HTTP_TIMEOUT_SECS)
        response.raise_for_status()
        logger.info("Ollama endpoint reachable (HTTP %d).", response.status_code)
        return True
    except requests.exceptions.ConnectionError:
        logger.error("Cannot connect to Ollama at %s — is LXC 102 running?", OLLAMA_HOST)
    except requests.exceptions.Timeout:
        logger.error("Ollama endpoint timed out after %d s.", HTTP_TIMEOUT_SECS)
    except requests.exceptions.HTTPError as exc:
        logger.error("Ollama returned an error: %s", exc)
    return False


def verify_model_loaded() -> bool:
    """
    Confirm the required model is present in Ollama's model registry.

    Returns:
        True if REQUIRED_MODEL is listed by Ollama, False otherwise.
    """
    logger.info("Checking model availability: %s", REQUIRED_MODEL)
    try:
        response = requests.get(OLLAMA_TAGS_URL, timeout=HTTP_TIMEOUT_SECS)
        response.raise_for_status()
        tags_data: dict = response.json()
        models: list[dict] = tags_data.get("models", [])
        model_names: list[str] = [m.get("name", "") for m in models]
        if REQUIRED_MODEL in model_names:
            logger.info("Model '%s' is present and loaded.", REQUIRED_MODEL)
            return True
        logger.error(
            "Model '%s' NOT found. Available models: %s",
            REQUIRED_MODEL,
            model_names or "(none)",
        )
    except requests.exceptions.ConnectionError:
        logger.error("Cannot reach Ollama tags endpoint: %s", OLLAMA_TAGS_URL)
    except requests.exceptions.Timeout:
        logger.error("Tags endpoint timed out after %d s.", HTTP_TIMEOUT_SECS)
    except requests.exceptions.HTTPError as exc:
        logger.error("Tags endpoint returned error: %s", exc)
    except (KeyError, ValueError) as exc:
        logger.error("Unexpected tags response format: %s", exc)
    return False


def verify_podman_sandbox() -> bool:
    """
    Confirm rootless Podman is functional inside the LXC.

    Returns:
        True if Podman can run a minimal container, False otherwise.
    """
    logger.info("Testing rootless Podman sandbox...")
    try:
        result = subprocess.run(
            ["podman", "run", "--rm", "--network=none", "alpine", "echo", "sandbox-ok"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            logger.info("Podman sandbox functional (output: %s).", result.stdout.strip())
            return True
        logger.error(
            "Podman exited with code %d. stderr: %s",
            result.returncode,
            result.stderr.strip(),
        )
    except FileNotFoundError:
        logger.error("Podman binary not found — is it installed in LXC 101?")
    except subprocess.TimeoutExpired:
        logger.error("Podman test container timed out after 30 s.")
    except OSError as exc:
        logger.error("Podman OS error: %s", exc)
    return False


def main() -> int:
    """
    Run all pre-flight checks and report overall readiness.

    Returns:
        Exit code: 0 = ready, 1 = not ready.
    """
    logger.info("═" * 54)
    logger.info(" AIR-GAP ENVIRONMENT PRE-FLIGHT CHECK")
    logger.info("═" * 54)

    results: dict[str, bool] = {
        "Inference Endpoint": verify_inference_reachable(),
        "Model Loaded":       verify_model_loaded(),
        "Podman Sandbox":     verify_podman_sandbox(),
    }

    logger.info("─" * 54)
    all_pass = all(results.values())
    for check, passed in results.items():
        symbol = "PASS" if passed else "FAIL"
        logger.info("  [%s] %s", symbol, check)

    logger.info("─" * 54)
    if all_pass:
        logger.info(" RESULT: Environment ready for Claude Code.")
        return 0

    logger.error(" RESULT: ENVIRONMENT NOT READY — address failures above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
