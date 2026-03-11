# Deployment Guide — Air-Gapped AI Development Station
**Version:** 1.1 | **Updated:** 2026-03-11

---

## 1. Initial Deployment

### 1.1 Prerequisites
- Proxmox VE 9.1 installed on T5500 hardware.
- 8 TB SAS array configured as a ZFS pool named `tank`.
- Management network access from Ansible controller (pre-air-gap phase only).

### 1.2 Run the Ansible Playbook
From an internet-connected management machine:
```bash
cd ansible/
ansible-playbook -i inventory.ini deploy-env.yml --ask-become-pass
```

This provisions:
- FIPS 140-3 kernel flag in GRUB.
- ZFS datasets with AES-256-GCM encryption.
- LXC container configurations.
- All scripts, systemd units, and cron jobs.

### 1.3 Generate Encryption Keys (Host)
On the Proxmox host (FIPS mode must be active):
```bash
/usr/local/bin/zfs-key-manager.sh generate tank/workspace
/usr/local/bin/zfs-key-manager.sh generate tank/ollama-models
```

Backup the generated keys to hardware-encrypted media immediately.

### 1.4 Air-Gap the System
Once all software is deployed and verified:
1. Disconnect the management network cable from `vmbr0` (if present).
2. Run `python3 /src/egress_check.py` to confirm isolation.
3. Document the air-gap date in the RACI log.

---

## 2. Model Updates (Sneakernet)

### 2.1 Prepare on Internet-Connected Machine
```bash
# Download model
ollama pull qwen2.5-coder:32b

# Export to file
ollama show --modelfile qwen2.5-coder:32b > qwen25_modelfile.txt
# Copy model blobs from ~/.ollama/models/blobs/ to USB

# Generate SHA-256 checksums for EVERY file
sha256sum <model-file> > <model-file>.sha256
```

### 2.2 Transfer via Encrypted USB
Use a FIPS 140-3 validated USB device (e.g. IronKey D300S or equivalent).

### 2.3 Deploy with Integrity Verification
On the Proxmox host:
```bash
mount /dev/sdX1 /mnt/usb
/usr/local/bin/sneakernet-update.bash --models
```
The script will abort if any SHA-256 checksum fails.

---

## 3. Container Image Updates

### 3.1 Prepare on Internet-Connected Machine
```bash
# Build the sandbox image
podman build -f containers/python-sandbox.Containerfile -t local/python-sandbox .

# Export
podman save -o sandbox.tar local/python-sandbox

# Checksum
sha256sum sandbox.tar > sandbox.tar.sha256
```

### 3.2 Sideload
```bash
/usr/local/bin/sneakernet-update.bash --images
```

---

## 4. Rollback Procedures

### 4.1 Model Rollback via ZFS Snapshot
If a newly sideloaded model causes problems:
```bash
# List model dataset snapshots
zfs list -t snapshot tank/ollama-models

# Rollback to last known-good snapshot
zfs rollback tank/ollama-models@autosnap_2026-03-10_0200

# Restart Ollama
pct exec 102 -- systemctl restart ollama-keepalive
```

### 4.2 Workspace Rollback
If a code change or Claude Code session corrupts the workspace:
```bash
# View available snapshots
zfs list -t snapshot tank/workspace

# Rollback (CAUTION: destroys changes made after the snapshot)
zfs rollback tank/workspace@autosnap_2026-03-10_0200
```

### 4.3 Container Image Rollback
Podman retains the previous image layer until explicitly pruned:
```bash
# List images inside LXC 101
pct exec 101 -- podman images

# Tag and restore previous image
pct exec 101 -- podman tag <previous-image-id> local/python-sandbox:latest
```

### 4.4 Emergency: Full Dataset Recovery from Backup
If ZFS pool is degraded or corrupted:
```bash
# Check pool status
zpool status tank

# Attempt repair
zpool scrub tank

# If irrecoverable — restore from offline encrypted backup:
# 1. Mount backup media
# 2. zfs receive tank/workspace < /mnt/backup/workspace_backup.zfs
# 3. Run manifest integrity check
python3 /src/check_manifest_integrity.py
```

---

## 5. Post-Deployment Verification Checklist

After any deployment or update, run:

```bash
# 1. Pre-flight
python3 /src/smoke_test_agent.py

# 2. Integrity
python3 /src/check_manifest_integrity.py

# 3. Compliance
python3 /src/security_compliance_audit.py

# 4. Air-gap
python3 /src/egress_check.py

# 5. Dashboard
python3 /src/env_dashboard.py
```

All checks must show PASS before resuming normal operations.
