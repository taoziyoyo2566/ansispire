# Ansispire Project Summary (Master Map)

## 1. Core Mission
Ansispire is a **Multi-Server Management Control System** designed for high-availability infrastructure operations. It upgrades standard Ansible from "ad-hoc scripts" into a reliable, audit-ready, and reactive automation engine.

## 2. Architectural Blueprint
- **Control Plane** (`controller/`): Go-based (Semaphore) or Python-based management interface.
- **Audit Plane** (`controller/audit/`): Real-time event tracking and non-repudiation logging.
- **Data Plane** (`roles/`, `playbooks/`): Idempotent server state definitions.
- **Reaction Plane** (EDA/Reactor): Event-driven remediation and notification.

## 3. Module Scope (Logic Truths)
- [Audit Plane Reliability](docs/features/audit-plane/summary.md)
- [EDA Core Engine](docs/features/eda-core/summary.md)
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
