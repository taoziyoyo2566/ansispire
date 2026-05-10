# Ansispire — Reactive Infrastructure Control System

Ansispire is a high-availability infrastructure control system. It upgrades standard Ansible from "scripts + SSH" into a **self-healing platform** featuring a professional web-based control plane and a real-time event-driven reactor.

---

## 🏗 1. System Architecture (The 4 Planes)

- **Control Plane (`controller/semaphore/`)**: The Brain. Provides WebUI, REST API, and RBAC.
- **Audit Plane (`controller/audit/`)**: The Memory. Tracks system actions into a traceable `events.jsonl`.
- **Reaction Plane (`extensions/eda/`)**: The Reflexes. Monitors logs and triggers remediation templates.
- **Data Plane (`roles/`, `playbooks/`)**: The Hands. Idempotent roles (Nginx/MySQL/Security).

---

## 📋 2. Running Environment & Requirements

### Host Requirements (Control Node)
- **OS**: Linux (Ubuntu 22.04+, Debian 11/12 recommended).
- **Toolchain**: Python 3.10+, Ansible-Core 2.20.5.
- **Mandatory Packages**: `acl`, `gnupg2`, `net-tools`, `git`, `curl`, `jq`.
- **Containers**: Docker Engine 24.0+ & Compose Plugin.

### Network & Port Map
| Port | Service | Environment | Scope |
| :--- | :--- | :--- | :--- |
| **3300** | Semaphore UI | **Persistent (Local/Prod)** | Management Console |
| **3310** | Audit Sink | **All** | Event Ingestion Endpoint |
| **3320** | Semaphore UI | **Ephemeral (E2E)** | Test Verification Console |

---

## 🛡 3. Authentication & Security (The Truth)

- **UI Login**: Default credentials are stored in `controller/semaphore/.env` (Admin) and `controller/rbac/users.yml` (Demo users).
- **M2M Auth**: The Reactor uses **Bearer Tokens** stored in `.secrets`.
- **Secrets Management**: 
  - Uses `inventory/local/vault.yml` (gitignored).
  - Password synced via `.vault_pass`.
  - Deployment uses a "Password-to-Mint-Token" 2-stage flow.

---

## ✅ 4. Functional Capabilities

- **EDA Self-Healing**: 
  - **Disk Remediation**: Automatic cleanup of `/tmp`, APT caches, and logs (based on `clean-tiny.sh` logic).
  - **Status**: Stable v2.3, E2E-verified.
- **Security Hardening**:
  - **SSH**: Disabling PasswordAuth/RootLogin, adjusting `MaxAuthTries`.
  - **Firewall**: Cross-platform orchestration of UFW and Firewalld.
- **Full-Stack Provisioning**:
  - **Web**: Nginx with Vhosts and SSL DHparams generation.
  - **DB**: MySQL with primary-replica readiness (Task-008 target).

---

## 🧪 5. Validation Tiers (Code Roles)

| Folder | Logic Type | Verification Command | Description |
| :--- | :--- | :--- | :--- |
| `roles/` | Business Logic | `make deploy-dev` | Full-stack test on localhost |
| `molecule/` | Role Unit | `make test` | Integration test in clean containers |
| `controller/`| Reactor Brain | `make test-eda-unit` | Python logic validation (No Docker) |
| `e2e/` | System Loop | `make test-eda-e2e` | Full Loopback: Event -> Reaction |

---

## 🚀 6. Quick Start Guide

1.  **Initialize**: `make setup` (Configures `.venv` and toolchain).
2.  **Verify Logic**: `make test-eda-e2e` (Check the UI at http://localhost:3320).
3.  **Local Deploy**: `make hub-deploy` (Default: `HUB_NODE=local`).
4.  **Remote Deploy**: `make hub-deploy HUB_NODE=remote`.

---

## 🔮 7. Roadmap & Directions

- **Short-term**: **Task-007 Multi-OS Support**. Enabling Alpine and RHEL targets.
- **Mid-term**: **Task-008 DB Failover**. Implementing state-aware primary/replica recovery.
- **Concepts**: Moving towards full observability (Prometheus) and log-slimming automation.

---
*Maintained under the GEMINI.md protocol. Every command is verified.*
