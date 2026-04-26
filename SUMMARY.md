# Ansispire Project Summary (Master Map)

## 1. Core Mission
Ansispire is a **Multi-Server Management Control System** designed for high-availability infrastructure operations. It upgrades standard Ansible from "ad-hoc scripts" into a governed, audited, and self-healing platform.

## 2. System Architecture (The Four Planes)
- **Control Plane**: API-driven management via Semaphore (BoltDB backend).
- **Data Plane**: Execution logic via modular Ansible Roles and Playbooks.
- **Audit Plane**: Zero-data-loss event tracking (Relay + Sink).
- **Reaction Plane (EDA)**: Lightweight reactor that triggers autonomous actions based on audit events (e.g., Nginx auto-restart on health-check failure).

## 3. Ground Truths & Environment
- **Runtime**: Docker-containerized services on Linux.
- **Toolchain**: Python 3.12+ (venv), Ansible-core, Ansible-lint.
- **State**: Configuration in Git; Operational state in BoltDB.
- **Verification**: Evidence-based (Lint + Syntax + Molecule).

## 4. Vendor Patching Truths (Protected Roles)
The following external roles are **patched locally** for quality standards. Do NOT overwrite via `ansible-galaxy` without re-applying lint fixes:
- `geerlingguy.docker`: Fixed for FQCN and Octal value standards.

## 5. Design Direction
- **Decoupling First**: Control logic must never leak into the Data Plane.
- **Audit Integrity**: Every action must leave a permanent, retrievable trace.
- **Lightweight Efficiency**: Maintain a minimal footprint (~200MB RAM for the controller).
- **AI-Native**: Designed for high-efficiency AI collaboration through layered documentation.

---
*This document is the authoritative entry point for all developers and AI agents.*
