# Architecture Document — Air-Gapped AI Development Station
**Version:** 1.0 | **Updated:** 2026-03-11  
**Compliance:** NIST 800-53 | FIPS 140-3 | CIS Proxmox Level 2

---

## 1. System Overview

```mermaid
graph TD
    subgraph PHYSICAL ["Physical Host — Dell Precision T5500"]
        CPU["2x Xeon X5650 (12 cores total)"]
        RAM["72 GB DDR3 ECC"]
        SAS["8 TB SAS Array\n(ZFS Pool: tank)"]
    end

    subgraph HOST ["Proxmox VE 9.1 Hypervisor"]
        ZFS_W["tank/workspace\n128k recordsize\nAES-256-GCM"]
        ZFS_M["tank/ollama-models\n1MB recordsize\nAES-256-GCM"]
        KEY["Key Store\n/etc/zfs/keys\nchmod 700"]
        VMBR1["vmbr1 — Private Bridge\n10.0.0.0/24\nNo external NIC"]
    end

    subgraph LXC101 ["LXC 101 — claude-agent (10.0.0.101)"]
        CLAUDE_CLI["Claude Code CLI"]
        PODMAN["Rootless Podman\n(nesting=1)"]
        SANDBOX["python-sandbox container\nai-sandbox network (internal)\nno gateway"]
        SRC["/src bind-mount\n→ tank/workspace"]
    end

    subgraph LXC102 ["LXC 102 — ollama-brain (10.0.0.102)"]
        OLLAMA["Ollama Service\nPort 11434"]
        MODEL["qwen2.5-coder:32b\n~22 GB RAM"]
        MODELS_MNT["/root/.ollama/models\n→ tank/ollama-models"]
    end

    SAS --> ZFS_W & ZFS_M
    KEY -.-> ZFS_W & ZFS_M
    ZFS_W --> SRC
    ZFS_M --> MODELS_MNT
    VMBR1 --- LXC101 & LXC102
    CLAUDE_CLI --> PODMAN --> SANDBOX
    CLAUDE_CLI -- "HTTP :11434/v1" --> OLLAMA
    OLLAMA --> MODEL
```

---

## 2. Security Architecture

```mermaid
graph LR
    subgraph "Threat Boundary"
        AIRGAP["Physical Air-Gap\nNo external NIC on vmbr1"]
    end

    subgraph "Layer 1 — Hypervisor Isolation"
        PROXMOX["Proxmox RBAC\nUnprivileged LXC\nUID mapping 0→100000"]
    end

    subgraph "Layer 2 — Container Isolation"
        LXC["LXC Unprivileged\nNo capability escalation"]
    end

    subgraph "Layer 3 — Execution Isolation"
        ROOTLESS["Rootless Podman\nInternal-only network\nRead-only /app mount"]
    end

    subgraph "Layer 4 — Cryptography"
        FIPS["FIPS 140-3 kernel\nAES-256-GCM ZFS\n/dev/urandom DRBG"]
    end

    AIRGAP --> PROXMOX --> LXC --> ROOTLESS --> FIPS
```

---

## 3. Data Flow

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant LXC101 as LXC 101 (Claude Agent)
    participant Podman as Podman Sandbox
    participant LXC102 as LXC 102 (Ollama)

    Dev->>LXC101: claude-launch.bash
    LXC101->>LXC101: smoke_test_agent.py (pre-flight)
    LXC101->>LXC102: GET /api/tags (verify model)
    LXC102-->>LXC101: qwen2.5-coder:32b confirmed
    LXC101->>LXC101: Launch Claude Code CLI
    Dev->>LXC101: Coding request
    LXC101->>LXC102: POST /v1/chat/completions
    LXC102-->>LXC101: AI response
    LXC101->>Podman: Execute generated code
    Podman-->>LXC101: Result (network=none)
```

---

## 4. Storage Architecture

| Dataset | Recordsize | Encryption | Purpose |
|---|---|---|---|
| `tank/workspace` | 128 KB | AES-256-GCM | Source code, config, scripts |
| `tank/ollama-models` | 1 MB | AES-256-GCM | LLM model weights (sequential reads) |

ZFS ARC is capped at 16 GB to leave ~50 GB for the 32B model in system RAM.

---

## 5. Network Architecture

| Network | Bridge | Subnet | Gateway | Purpose |
|---|---|---|---|---|
| Internal AI | `vmbr1` | `10.0.0.0/24` | None | LXC-to-LXC communication only |
| Podman Sandbox | `podman1` | `172.16.200.0/24` | None | Complete network isolation for code execution |

---

## 6. Component Inventory

| Component | Version | Location |
|---|---|---|
| Proxmox VE | 9.1 | Physical host |
| Ollama | Latest at sideload | LXC 102 |
| qwen2.5-coder | 32B | LXC 102 via Ollama |
| Claude Code CLI | Latest at sideload | LXC 101 |
| Python | 3.11 | LXC 101 + sandbox |
| Podman | System package | LXC 101 |
