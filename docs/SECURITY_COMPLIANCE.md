# Security & Compliance Mapping

## 1. Regulatory Controls
- **NIST 800-53 (AC-3):** Least Privilege via Proxmox RBAC.
- **FIPS 140-3:** AES-256-GCM encryption with `fips=1` kernel flag.
- **CIS Level 2:** Hardened via disabled SSH password auth and isolated `vmbr1`.

## 2. Hardening Measures
- **Network:** Physical air-gap; no NIC assigned to the internal API bridge.
- **Storage:** Data-at-rest encryption via ZFS Native Encryption.
- **Execution:** Double-wall isolation (LXC + Rootless Podman).