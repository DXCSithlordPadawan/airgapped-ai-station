#!/usr/bin/env bash
# claude-launch.bash — Standardised Claude Code Launch Script
# Location: /usr/local/bin/claude-launch.bash (inside LXC 101)
#
# Compliance: NIST 800-53 SC-13, SI-12
set -euo pipefail

# ── API Redirect to local Ollama (LXC 102) ────────────────────────────────────
# NOTE: Key value must match .claude.env. "ollama" is the accepted placeholder
#       token when using the Ollama OpenAI-compatible API.
export ANTHROPIC_BASE_URL="http://10.0.0.102:11434/v1"
export ANTHROPIC_API_KEY="ollama"

# ── Telemetry Lockdown ────────────────────────────────────────────────────────
export CLAUDE_CODE_TELEMETRY=0
export CHECKPOINT_DISABLE=1
export ALLOW_DANGEROUS_COMMANDS=0

# ── Pre-flight check ──────────────────────────────────────────────────────────
echo "[*] Running pre-flight environment check..."
if ! python3 /src/smoke_test_agent.py; then
    echo "[ERROR] Pre-flight failed. Aborting Claude Code launch." >&2
    exit 1
fi

# ── Launch ────────────────────────────────────────────────────────────────────
echo "[*] Initialising Claude Code on local Ollama API..."
exec claude
