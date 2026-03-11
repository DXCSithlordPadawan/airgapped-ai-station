# Maintenance Guide — Air-Gapped AI Development Station
**Version:** 1.1 | **Updated:** 2026-03-11

---

## 1. Regular Maintenance Schedule

| Frequency | Task | Script / Command |
|---|---|---|
| Daily (automated) | ZFS snapshot creation | `zfs-snap-manager.bash --policy` |
| Daily (automated) | Security audit | `security-audit.bash` |
| Weekly | Manifest integrity check | `check_manifest_integrity.py` |
| Monthly | ZFS pool scrub | `zpool scrub tank` |
| Monthly | Compliance audit review | `security_compliance_audit.py` + review JSON reports |
| Monthly | Log rotation / archival | See Section 5 |
| 90 days | API token rotation | See Section 3.2 |
| 180 days | ZFS encryption key rotation | See Section 3.1 |
| As needed | Model update (sneakernet) | `sneakernet-update.bash --models` |
| As needed | Container image update | `sneakernet-update.bash --images` |

---

## 2. ZFS Maintenance

### 2.1 Monthly Pool Scrub
Run on the Proxmox host:
```bash
zpool scrub tank
# Monitor progress
zpool status tank
```
Allow 2–6 hours for completion on the 8 TB SAS array.

### 2.2 Snapshot Management
Automated daily snapshots are managed via cron using `policy.yml`.
Manual snapshot:
```bash
/usr/local/bin/zfs-snap-manager.bash --dataset tank/workspace --keep 7
```

View snapshots:
```bash
zfs list -t snapshot -o name,creation,used -s creation
```

### 2.3 Capacity Monitoring
Check pool usage:
```bash
zpool list tank
zfs list -r tank
```

**Warning threshold:** 80% capacity. At this point, review snapshot counts and
model weight storage.

---

## 3. Key Rotation

### 3.1 ZFS Encryption Keys (every 180 days)
```bash
/usr/local/bin/zfs-key-manager.sh rotate tank/workspace
/usr/local/bin/zfs-key-manager.sh rotate tank/ollama-models
```
After rotation, store the new key backup on hardware-encrypted media in the
physical safe. Destroy old backup copy.

### 3.2 API Tokens (every 90 days)
The `ANTHROPIC_API_KEY` in `.claude.env` uses the placeholder `"ollama"` for
the local API and does not require rotation. If you introduce additional API
tokens for other services, rotate them every 90 days and update `.claude.env`.

---

## 4. LXC Container Updates (Offline)

### 4.1 OS Package Updates via Sneakernet
1. On an internet-connected staging machine, create a package bundle:
   ```bash
   apt-get download $(apt-cache depends --recurse --no-recommends \
       --no-suggests --no-conflicts --no-breaks --no-replaces \
       --no-enhances <package-name> | grep "^\w" | sort -u)
   ```
2. Transfer via encrypted USB.
3. Inside the LXC:
   ```bash
   dpkg -i /mnt/usb/packages/*.deb
   ```

### 4.2 Python Dependency Updates
1. Download updated wheels on internet-connected machine:
   ```bash
   pip download -r requirements.txt -d /local/packages
   ```
2. Transfer to `/local/packages` inside LXC 101 via sneakernet.
3. Reinstall:
   ```bash
   pip install --no-index --find-links=/local/packages -r requirements.txt
   ```

### 4.3 Podman Image Refresh
See DEPLOYMENT.md Section 2. Use `sneakernet-update.bash --images`.

---

## 5. Log Management

Logs accumulate in `/var/log/airgap/`. Rotate monthly:
```bash
# Archive logs older than 30 days
find /var/log/airgap/ -name "*.log" -mtime +30 \
    -exec gzip {} \; \
    -exec mv {}.gz /var/log/airgap/archive/ \;
```

Retain audit reports for 12 months per NIST AU-11.

---

## 6. Disk Capacity Thresholds

| Threshold | Action |
|---|---|
| 70% | Review and prune old model weights |
| 80% | **Warning**: Reduce snapshot retention, notify admin |
| 90% | **Critical**: Immediately free space before new sideloads |

Check with:
```bash
zpool list -o name,size,alloc,free,cap,health tank
```

---

## 7. After Any Change

After any file modification, always run the integrity check:
```bash
python3 /src/check_manifest_integrity.py
```

After any network change, verify the air-gap:
```bash
python3 /src/egress_check.py
```
