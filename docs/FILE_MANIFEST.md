# File Manifest — Air-Gapped AI Development Station
**Version:** 1.1 | **Updated:** 2026-03-11  
**Integrity:** Run `python3 src/check_manifest_integrity.py` to verify this manifest.

---

## Repository Structure

```
airgapped-ai-station/
├── README.md                           — Project overview
├── CLAUDE.md                           — AI agent rules and build commands
├── requirements.txt                    — Python dependencies (offline install)
├── .gitignore                          — Excludes secrets and model artefacts
│
├── src/                                — Python operational scripts
│   ├── check_manifest_integrity.py     — File & permission auditor
│   ├── security_compliance_audit.py    — FIPS/ZFS/LXC compliance checker
│   ├── smoke_test_agent.py             — Pre-flight environment validator
│   ├── env_dashboard.py                — Real-time environment dashboard
│   ├── telemetry_scrubber.py           — Workspace telemetry scanner
│   └── egress_check.py                 — Network air-gap verification
│
├── scripts/                            — Bash operational scripts (Proxmox host)
│   ├── claude-launch.bash              — Standardised Claude Code launch
│   ├── security-audit.bash             — Host-level CIS/FIPS audit
│   ├── sneakernet-update.bash          — USB sideloading with SHA-256 verify
│   ├── zfs-key-manager.sh              — ZFS key lifecycle manager
│   └── zfs-snap-manager.bash           — Snapshot creation & pruning
│
├── config/                             — Configuration files
│   ├── 101.conf                        — LXC 101 (Claude agent) config
│   ├── 102.conf                        — LXC 102 (Ollama) config
│   ├── policy.yml                      — ZFS snapshot retention policy
│   └── .claude.env.example             — API env template (real file is gitignored)
│
├── containers/                         — Container definitions
│   ├── python-sandbox.Containerfile    — Hardened Python Podman sandbox
│   └── internal.yaml                   — Podman internal network definition
│
├── systemd/                            — Systemd unit files
│   ├── ollama-keepalive.service        — Ollama service (with User= hardening)
│   └── zfs-load-keys.service           — Boot-time ZFS key loader
│
├── ansible/                            — Infrastructure-as-code
│   ├── deploy-env.yml                  — Full provisioning playbook
│   └── inventory.ini                   — Ansible inventory template
│
├── tests/                              — pytest test suite
│   ├── conftest.py                     — Shared fixtures
│   ├── test_check_manifest.py          — Tests for integrity checker
│   ├── test_security_audit.py          — Tests for compliance auditor
│   ├── test_smoke_test.py              — Tests for smoke test (mocked)
│   ├── test_telemetry_scrubber.py      — Tests for scrubber
│   ├── test_env_dashboard.py           — Tests for dashboard
│   └── test_egress_check.py            — Tests for egress checker
│
└── docs/                               — Governance and compliance documents
    ├── ARCHITECTURE.md                 — System architecture
    ├── PRD_AIR_GAPPED_AI.md            — Master requirements document
    ├── USER_GUIDE.md                   — Operator runbook
    ├── API_GUIDE.md                    — Ollama/Claude API reference
    ├── DEPLOYMENT.md                   — Sideloading & rollback procedures
    ├── MAINTENANCE.md                  — Maintenance lifecycle guide
    ├── SECURITY_COMPLIANCE.md          — NIST/FIPS/CIS control mapping
    ├── RACI.md                         — Responsibility matrix
    ├── RBAC.md                         — Access control policy
    ├── FILE_MANIFEST.md                — This file
    └── GAP_ANALYSIS.md                 — Gap analysis & remediation record
```

---

## Required File Permissions (Host)

| Path | Permission | Rationale |
|---|---|---|
| `/etc/zfs/keys/` | `700` | Key store — root-only directory |
| `/etc/zfs/keys/*.key` | `600` | Key material — root read-only |
| `/etc/pve/lxc/101.conf` | `600` | LXC config — root read-only |
| `/etc/pve/lxc/102.conf` | `600` | LXC config — root read-only |
| `/usr/local/bin/*.sh` | `755` | Executable scripts |
| `/usr/local/bin/*.bash` | `755` | Executable scripts |
| `/etc/systemd/system/*.service` | `644` | systemd units |
| `/tank/workspace/.claude.env` | `600` | API credentials — owner read-only |

---

## Gitignored Files (Never Commit)

- `.claude.env` — API keys and redirects
- `*.key` — ZFS encryption keys
- `*.gguf`, `*.bin`, `*.safetensors` — Model weight files
