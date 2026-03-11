# Product Requirement Document (PRD): Project "Air-Gapped Intel"

**Project Name:** Air-Gapped AI Development Station  
**Revision:** 1.0  
**Compliance Standard:** NIST 800-53 / CIS Proxmox Level 2  
**Host Workstation:** Dell Precision T5500 (Dual CPU, 72GB RAM, 8TB SAS)

---

## 1. Executive Summary
The goal of Project "Air-Gapped Intel" is to establish a high-performance, strictly isolated AI development environment. By leveraging local inference (Ollama) and agentic interfaces (Claude Code) on a hardened Proxmox 9.1 hypervisor, the system enables modern AI-assisted coding without data exfiltration risks.

---

## 2. Infrastructure Architecture

### 2.1 Virtualization & Isolation
- **Hypervisor:** Proxmox VE 9.1 (Host Hardened).
- **Inference Engine (LXC 102):** Unprivileged container running Ollama.
- **Agent Interface (LXC 101):** Unprivileged container running Claude Code CLI.
- **Network Isolation:** All internal API traffic is restricted to `vmbr1` (Private Bridge) with no physical NIC uplink.

### 2.2 Storage Layer (ZFS)
The 8TB SAS array is managed via ZFS with the following dataset optimizations:
- **`tank/ollama-models`**: 
    - **Recordsize:** 1MB (Optimized for large model weights).
    - **Encryption:** AES-256-GCM.
- **`tank/workspace`**: 
    - **Recordsize:** 128k (Standard for source code).
    - **Attributes:** `xattr=sa` for performance.
- **Key Management:** FIPS-compliant key storage in `/etc/zfs/keys` (Host-only).

### 2.3 Compute Resource Mapping
- **Total RAM:** 72GB.
- **ZFS ARC Cap:** 16GB (via `zfs_arc_max`).
- **Available LLM RAM:** ~50GB (Allocated for 32B+ models).

---

## 3. Functional Requirements

### 3.1 AI Agent Capabilities
- **Model:** Qwen 2.5 Coder 32B (running locally via Ollama).
- **Protocol:** Claude Code CLI using `ANTHROPIC_BASE_URL` redirection to the local LXC 102 IP.
- **Tool Use:** Automated file editing, shell execution, and architectural analysis.

### 3.2 Security Sandboxing
- **Primary Barrier:** Unprivileged LXC (UID mapping 0 -> 100000).
- **Secondary Barrier:** Rootless Podman runtime inside the LXC for executing AI-generated scripts.
- **Encryption:** FIPS 140-3 validated cryptographic modules enabled at the kernel level.

---

## 4. Operational Maintenance
- **Updates (Sneakernet):** Manual sideloading of models and container images via encrypted physical media.
- **Integrity Checks:** Monthly `zpool scrub` and automated daily snapshots.
- **Auditing:** Execution of `security_audit.py` to verify FIPS and RBAC status.

---

## 5. Success Metrics
- **Zero Leakage:** No external packets crossing the air-gap boundary.
- **Performance:** Sub-second response for local file indexing and low-latency inference on Dual CPUs.
- **Safety:** 100% of AI-generated code executed within the Podman sandbox.

---

## 6. Project Governance Documents
The following files are required for compliance and are located in the project root:
1. `CLAUDE.md` - Agent Rules & Build Commands
2. `RACI.md` - Roles & Responsibilities
3. `RBAC.md` - Access Control Policies
4. `SECURITY_COMPLIANCE.md` - Control Mapping
5. `DEPLOYMENT.md` - Update Lifecycle Guide

---
**Approver:** System Administrator  
**Date:** March 2026