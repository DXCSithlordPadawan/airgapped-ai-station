# User Guide — Air-Gapped AI Development Station
**Version:** 1.1 | **Updated:** 2026-03-11

---

## 1. Overview

This guide describes the day-to-day operation of the Air-Gapped AI Development
Station for all operators. The system consists of:

- **Proxmox Host** — The physical T5500 server running the hypervisor.
- **LXC 101** (`claude-agent`, `10.0.0.101`) — The Claude Code / developer workspace.
- **LXC 102** (`ollama-brain`, `10.0.0.102`) — The Ollama LLM inference engine.

---

## 2. Starting a Session

### Step 1 — Verify the Environment

Log into LXC 101 and run the pre-flight check:

```bash
python3 /src/smoke_test_agent.py
```

Expected output:
```
[PASS] Inference Endpoint
[PASS] Model Loaded
[PASS] Podman Sandbox
RESULT: Environment ready for Claude Code.
```

If any check fails, see Section 6 (Troubleshooting).

### Step 2 — Launch Claude Code

```bash
bash /usr/local/bin/claude-launch.bash
```

This script:
1. Runs the pre-flight check automatically.
2. Sets `ANTHROPIC_BASE_URL` to redirect to the local Ollama instance.
3. Disables all telemetry.
4. Launches the `claude` CLI.

---

## 3. Running Audits

### Manifest Integrity Check
```bash
python3 /src/check_manifest_integrity.py
```
Verifies all required files exist with correct permissions. Run this after any
manual file change.

### Security Compliance Audit
```bash
python3 /src/security_compliance_audit.py
```
Checks FIPS mode, ZFS ARC limits, and LXC privilege levels. Saves a JSON
report to `/var/log/airgap/audit_reports/`.

### Host-Level Bash Audit
```bash
/usr/local/bin/security-audit.bash
```
Checks SSH hardening, key permissions, and LXC configs. Logs to
`/var/log/airgap/`.

### Network Egress Verification
```bash
python3 /src/egress_check.py
```
Confirms no default gateway exists and the external internet is unreachable.
Run this after any network configuration change.

### Telemetry Scrubber
```bash
# Audit only
python3 /src/telemetry_scrubber.py --dry-run

# Remove telemetry artefacts
python3 /src/telemetry_scrubber.py --execute
```

---

## 4. Executing Code via Podman Sandbox

All AI-generated scripts must be executed inside the Podman sandbox, not
directly in the LXC:

```bash
podman run --rm \
    --network=none \
    -v $(pwd):/app:Z,ro \
    local/python-sandbox \
    python3 /app/my_script.py
```

---

## 5. Viewing System Status

```bash
python3 /src/env_dashboard.py
```

Displays ZFS pool health, ARC usage, LXC container states, and FIPS status.

---

## 6. Troubleshooting

### Ollama endpoint unreachable
1. Check LXC 102 is running: `pct status 102` on the Proxmox host.
2. Check Ollama service: `pct exec 102 -- systemctl status ollama-keepalive`.
3. Verify bridge: `ip link show vmbr1` — ensure both veth interfaces are up.

### Model not loaded
```bash
# List loaded models
pct exec 102 -- ollama list

# Manually pull (if USB has been sideloaded)
pct exec 102 -- ollama run qwen2.5-coder:32b ""
```

### Podman fails with permission error
Check nesting is enabled in `/etc/pve/lxc/101.conf`:
```
features: nesting=1
```

### ZFS datasets not mounted
```bash
/usr/local/bin/zfs-key-manager.sh load tank/workspace
/usr/local/bin/zfs-key-manager.sh load tank/ollama-models
```

---

## 7. Sideloading Updates (Sneakernet)

See [DEPLOYMENT.md](DEPLOYMENT.md) for the full procedure.  
Quick reference:

```bash
# Mount encrypted USB at /mnt/usb
mount /dev/sdX1 /mnt/usb

# Sideload with integrity verification
/usr/local/bin/sneakernet-update.bash --all
```

---

## 8. Log File Locations

| Log | Path |
|---|---|
| Smoke test | `/var/log/airgap/smoke_test.log` |
| Manifest audit | `/var/log/airgap/manifest_audit_YYYYMMDD.log` |
| Compliance audit | `/var/log/airgap/compliance_audit_YYYYMMDD.log` |
| Audit reports (JSON) | `/var/log/airgap/audit_reports/` |
| Security audit (bash) | `/var/log/airgap/security_audit_*.log` |
| Egress check | `/var/log/airgap/egress_check.log` |
| Dashboard | `/var/log/airgap/dashboard.log` |
| ZFS snapshots | `/var/log/airgap/snapshots.log` |
