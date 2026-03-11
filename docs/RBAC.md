# RBAC Policy: Proxmox & LXC

## Role: AI-Inference-Admin (LXC 102)
- **Permissions:** `VM.Audit`, `VM.Config.Options`, `VM.Console`.
- **Scope:** Managing model weights and Ollama service health.

## Role: AI-Developer (LXC 101)
- **Permissions:** `VM.Console`, `VM.Backup`.
- **Restriction:** No host shell access. Limited to `/src` via ZFS bind-mount.

## Enforcement
- All containers must remain **Unprivileged**.
- UID Mapping: Root (0) inside LXC -> UID 100000 on Host.