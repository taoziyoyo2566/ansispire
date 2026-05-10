# Ansispire Project Summary (Master Map)

## 0. Quick Start
- [Getting Started Guide](docs/GETTING_STARTED.md) — *Zero-to-One Lifecycle*
- **[EDA Self-Healing Operator Guide](docs/features/eda-core/operator-guide.md)** — *TASK-001 详细 guideline，零基础入门 → 生产部署*

## 1. Core Mission
Ansispire is a **Multi-Server Management Control System** designed for high-availability infrastructure operations. It upgrades standard Ansible from "ad-hoc scripts" into a reliable, audit-ready, and reactive automation engine.

## 2. Architectural Blueprint
- **Control Plane** (`controller/`): Go-based (Semaphore) management interface; deployed via Ansible role (`ansispire_hub`) or directly via docker compose.
- **Audit Plane** (`controller/audit/`): Real-time event tracking + non-repudiation logging (sink + relay + reactor).
- **Data Plane** (`roles/`, `playbooks/`): Idempotent server state definitions.
- **Reaction Plane** (EDA/Reactor): Event-driven remediation (API-driven via Bearer Token) and notification. Supports dynamic template resolution by name.
- **Database Backend**: SQLite (BoltDB deprecated upstream).
- **Config-as-Code (IaC)**: Standardized bootstrap via `controller/semaphore/bootstrap.yml` to automate project/template/token provisioning. UI zero-touch.
- **SSOT (Round 4+)**: `config/manifest.yml` is the single source of truth for both **host ports** and **image versions**; `make manifest-sync` renders to `.env`.
- **Two operational paths**:
  - **Path A** — Ansible role-based real deployment (`make hub-deploy NODE=local|remote|all`); production target.
  - **Path B** — direct docker compose (`make controller-up && make controller-bootstrap && make controller-audit-up`); dev / testing.
- **Inventory taxonomy**: `[hub_local]` / `[hub_remote]` / `[hub:children]` for management nodes; `[targets_debian|rhel|alpine]` placeholders for managed VPS (next-stage 4-VPS expansion).

## 3. Module Scope (Logic Truths)
- [Hub Deployment & Ops](docs/features/hub-deployment/operations.md) — maintainer 速查
- [Audit Plane Reliability](docs/features/audit-plane/summary.md)
- [EDA Core Engine](docs/features/eda-core/summary.md) — feature map
- **[EDA Self-Healing Operator Guide](docs/features/eda-core/operator-guide.md)** — **TASK-001 详细 guideline (从零部署 + 故障排查 + 安全注意 + 词汇表)**
- [Test Infrastructure & Stability](docs/features/test-infra/summary.md)
- [Empirical Truths (Investigations)](docs/investigations/) — *Root cause analysis and feasibility spike history*
- [Test Specifications (TSVS)](docs/test-specs/) — *Mandatory verification records*

## 4. Operational Integrity (Lessons Learned)
- **AI-Native Governance**: Integrated Gemini and Claude rules.
- **Cross-AI Audit**: Mandatory peer-review and archiving protocol for multi-AI investigation consistency.
- **Environment Sensing**: Never assume a feature (IPv6, SSH, Cron) is available in test containers. Use `stat` and `stat.exists` to make roles adaptive. Specifically: roles that modify `/etc/ssh/sshd_config` must guard with `stat` or be skipped entirely in Docker where `openssh-server` may not be installed.
- **Variable Precedence**: In Molecule, use `provisioner.inventory.host_vars` to override platform-specific limitations.
- **Python 3.9+ Baseline**: Following the 2026 LTS upgrade (Ansible-Core 2.20.5), managed nodes MUST have Python 3.9+. Ubuntu 20.04 is dropped from Tier 1 support.
- **RedHat 9 Compatibility**: Rocky Linux 9 has deep PAM entanglements in Docker; focus functional role testing on Ubuntu/Debian in containerized CI. Rocky Linux 9 is moved to Tier 2 for functional validation only.
- **Molecule Plugin Isolation**: Docker does not inherit the local `PYTHONPATH` or `ANSIBLE_FILTER_PLUGINS`; both must be explicitly mapped in `molecule.yml` (e.g., to support custom filters like `ljust`).
- **Core Engine (2026 LTS)**: Upgraded to Ansible-Core 2.20.5. Dependencies and collections are strictly locked in `requirements.txt` and `requirements.yml` to prevent version drift. Config-level `ansible_managed` is deprecated in 2.20 and moved to `group_vars/all/vars.yml`.
- **Minimal Image Dependency**: Ensure corresponding packages (e.g., `cron`, `openssh-server`) are installed in the `prepare` phase, as minimal images often omit them.

## 5. Vendor Patching Truths (Protected Roles)
The following external roles are **patched locally**. Do NOT overwrite via `ansible-galaxy` without re-applying fixes:
- `geerlingguy.docker`: Fixed for FQCN and Octal value standards.

## 6. Design Direction
- **Decoupling First**: Control logic must never leak into the Data Plane.
- **Audit Integrity**: Every action must leave a trace.
- **Lightweight Efficiency**: Minimal footprint (~200MB RAM for controller).
- **AI-Native**: Layered documentation for high-efficiency AI collaboration.

---
*This document is the authoritative entry point for all developers and AI agents.*
