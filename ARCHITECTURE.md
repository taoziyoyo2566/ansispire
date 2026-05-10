# Ansispire Architecture

## 0. Quick Start
- [Installation Guide](docs/user-guide/01-installation.md) — *clean machine → working self-healing (Path B + Path A)*
- **[EDA Self-Healing Operator Guide](docs/user-guide/02-quickstart-eda.md)** — *deep dive: rationale, failure modes, recovery*
- [Environments Reference](docs/operations/environments.md) — *which inventory / Make target for dev / stag / prod*

## 1. Core Mission
Ansispire is a **Multi-Server Management Control System** for high-availability infrastructure operations. It upgrades standard Ansible from "ad-hoc scripts" into a reliable, audit-ready, and reactive automation engine.

## 2. Architectural Blueprint
- **Control Plane** (`controller/`): Go-based (Semaphore) management interface; deployed via Ansible role (`ansispire_hub`) or directly via docker compose.
- **Audit Plane** (`controller/audit/`): Real-time event tracking + non-repudiation logging (sink + relay + reactor).
- **Data Plane** (`roles/`, `playbooks/`): Idempotent server state definitions.
- **Reaction Plane** (EDA / Reactor): Event-driven remediation (API-driven via Bearer Token) and notification. Supports dynamic template resolution by name.
- **Database Backend**: SQLite (BoltDB deprecated upstream).
- **Config-as-Code (IaC)**: Standardized bootstrap via `controller/semaphore/bootstrap.yml` automates project / template / token provisioning. UI zero-touch.
- **SSOT**: `config/manifest.yml` is the single source of truth for both **host ports** and **image versions**; `make manifest-sync` renders to `.env`.
- **Tiered Environment Model**:
  - **Dev** (`inventory/dev/`): local development, unit testing, ephemeral EDA validation (`make test-eda-e2e`).
  - **Stag** (`inventory/stag/`): pre-production mirroring on real infrastructure (`make deploy-stag`).
  - **Prod** (`inventory/prod/`): live management and application plane (`make hub-deploy`, `make deploy-prod`).
- **Inventory taxonomy**: `[hub_local]` / `[hub_remote]` / `[hub:children]` for management nodes; `[targets_debian|rhel|alpine]` placeholders for managed VPS.

## 3. Module Scope (Logic Truths)
- [Hub Deployment](docs/reference/feature-map/hub-deployment.md) — feature map · ops: [`docs/operations/hub-deployment.md`](docs/operations/hub-deployment.md)
- [Audit Plane Reliability](docs/reference/feature-map/audit-plane.md)
- [EDA Core Engine](docs/reference/feature-map/eda-core.md) — feature map · ops: [`docs/operations/eda-core.md`](docs/operations/eda-core.md)
- [EDA Remediation (Nginx)](docs/reference/feature-map/eda-remediation.md) — first remediation rule
- **[EDA Self-Healing Operator Guide](docs/user-guide/02-quickstart-eda.md)** — long-form user guide (zero-knowledge → production)
- [Test Infrastructure & Stability](docs/reference/feature-map/test-infra.md)
- [Empirical Investigations Index](docs/reference/investigations/INDEX.md) — root cause analysis and feasibility spike history
- [Test Specifications (TSVS)](docs/reference/test-specs/) — mandatory verification records

## 4. Design Direction
- **Decoupling First**: Control logic must never leak into the Data Plane.
- **Audit Integrity**: Every action must leave a trace.
- **Lightweight Efficiency**: Minimal footprint (~200 MB RAM for the controller).
- **AI-Native**: Layered documentation for high-efficiency AI collaboration.

---
*Architecture truth lives here. Operational lessons live in [docs/governance/operational-truths.md](docs/governance/operational-truths.md). Vendor patch obligations live in [docs/governance/vendor-patches.md](docs/governance/vendor-patches.md).*
