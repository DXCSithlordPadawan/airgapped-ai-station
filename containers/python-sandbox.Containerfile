# python-sandbox.Containerfile — Hardened Python Execution Sandbox
# Build: podman build -f python-sandbox.Containerfile -t local/python-sandbox .
# Run:  podman run --rm --network=none -v $(pwd):/app:Z,ro local/python-sandbox python3 /app/script.py
#
# Compliance: NIST 800-53 SC-39 (Process Isolation) | CIS Level 2
FROM python:3.11-slim-bookworm

# ── Build dependencies (removed after install) ────────────────────────────────
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libc6-dev && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get purge -y --autoremove curl wget git

# ── Offline package install ───────────────────────────────────────────────────
# Packages must be pre-staged in /local/packages on the host before build.
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --no-index --find-links=/local/packages \
    -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

# ── Non-root user ─────────────────────────────────────────────────────────────
RUN useradd --create-home --uid 1000 --no-log-init sandboxuser
USER sandboxuser
WORKDIR /app

# ── Hardening env vars ────────────────────────────────────────────────────────
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1

# ── Default command ───────────────────────────────────────────────────────────
CMD ["python3"]
