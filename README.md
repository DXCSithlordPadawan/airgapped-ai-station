# Air-Gapped AI Development Station

A hardened, offline AI development environment running on Proxmox VE 9.1 with
local LLM inference via Ollama and agentic coding via Claude Code CLI.

## Architecture at a Glance

| Layer | Component | Details |
|---|---|---|
| Hypervisor | Proxmox VE 9.1 | T5500 Dual CPU, 72GB RAM, 8TB SAS |
| Storage | ZFS (`tank`) | AES-256-GCM encrypted, 1 MB recordsize for models |
| Inference | LXC 102 — Ollama | `qwen2.5-coder:32b`, 48 GB RAM, 24 cores |
| Agent | LXC 101 — Claude Code | 16 GB RAM, 12 cores, rootless Podman sandbox |
| Network | `vmbr1` (10.0.0.0/24) | Isolated private bridge, no external NIC |

## Quick Start

```bash
# 1. Verify environment
python3 src/smoke_test_agent.py

# 2. Run compliance audit
python3 src/security_compliance_audit.py

# 3. Check manifest integrity
python3 src/check_manifest_integrity.py

# 4. Launch Claude Code
bash scripts/claude-launch.bash
```

## Installation (Air-Gapped)

```bash
pip install --no-index --find-links=/local/packages -r requirements.txt
```

## Running Tests

```bash
pytest tests/ -v --tb=short
```

## Compliance Standards

- NIST 800-53
- FIPS 140-3
- CIS Proxmox Level 2
- DISA STIG

## Documentation

| Document | Purpose |
|---|---|
| [docs/PRD_AIR_GAPPED_AI.md](docs/PRD_AIR_GAPPED_AI.md) | Master requirements |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System architecture |
| [docs/USER_GUIDE.md](docs/USER_GUIDE.md) | Operator runbook |
| [docs/API_GUIDE.md](docs/API_GUIDE.md) | Ollama API reference |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Sideloading procedures |
| [docs/MAINTENANCE.md](docs/MAINTENANCE.md) | Maintenance lifecycle |
| [docs/SECURITY_COMPLIANCE.md](docs/SECURITY_COMPLIANCE.md) | Control mapping |
| [docs/RACI.md](docs/RACI.md) | Responsibility matrix |
| [docs/RBAC.md](docs/RBAC.md) | Access control policy |
| [docs/FILE_MANIFEST.md](docs/FILE_MANIFEST.md) | File inventory |
| [docs/GAP_ANALYSIS.md](docs/GAP_ANALYSIS.md) | Gap analysis & remediation |
