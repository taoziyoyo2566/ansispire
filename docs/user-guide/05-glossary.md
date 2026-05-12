# Glossary & File Index

> **Audience**: anyone reading other docs and unsure what a term or file means.

---

## Concepts

| Term | What it means in Ansispire |
|---|---|
| **Control Plane** | The management layer (Semaphore web UI + REST API + RBAC). Lives in `controller/semaphore/`. Deploys via Path A (Ansible role) or Path B (docker compose). |
| **Audit Plane** | Three Python micro-services (`sink.py`, `relay.py`, `reactor.py`) under `controller/audit/`. Captures every Semaphore action into an append-only `events.jsonl`, then the reactor matches and dispatches remediation. |
| **Data Plane** | The managed servers — what Ansible actually configures via `roles/` and `playbooks/`. |
| **Reaction Plane (EDA)** | The "self-healing" loop: events → rule match → remediation playbook fired via Semaphore API. |
| **Hub** | A node that hosts the full Control + Audit stack. In `inventory/hosts.ini` it lives in `[hub_local]` (workstation) or `[hub_remote]` (real VPS); `[hub:children]` is the union. |
| **Targets** | Managed VPS that receive `infra_baseline` and application roles only — they do **not** host the hub. Grouped by OS family in `[targets_debian|rhel|alpine]`. |
| **Path A** | The "real deployment" path: `make hub-deploy HUB_NODE=...` invokes the `ansispire_hub` role to deploy the hub onto a remote VPS (or `localhost` for a permanent local hub). Persistent. |
| **Path B** | The "dev / testing" path: `make controller-up && make controller-bootstrap && make controller-audit-up` uses docker-compose on the workstation. Ephemeral. |
| **Bootstrap** | An Ansible playbook (`controller/semaphore/bootstrap.yml`) that registers Semaphore project / inventory / templates / API token via the REST API. IaC; UI-zero-touch. |
| **Bearer Token (M2M)** | Machine-to-machine auth used by the reactor to call Semaphore. Minted by bootstrap, persisted to `controller/semaphore/.secrets` (Path B) or `<hub>:/var/lib/ansispire/state/.eda_token` (Path A). The admin password never enters the reaction loop. |
| **SSOT** | Single Source of Truth. Two SSOT files: `config/manifest.yml` (ports + image versions) and `inventory/hosts.ini` (physical topology). |
| **Manifest sync** | `make manifest-sync` renders the SSOT manifest into `controller/semaphore/.env` (between `# BEGIN manifest` and `# END manifest` markers). Auto-runs before `make controller-up`. |
| **Cooldown** | Per-rule timestamp in the reactor that prevents event-storm cascades (default 600 s). |
| **`enabled: false`** | Soft-disable on a rule in `rules.json`. Reactor early-returns from `match_rule`; the rule stays in the file as documentation. |
| **Tier 1 / Tier 2** | Platform support tier. Tier 1 = tested in CI + Molecule (Debian 12, Ubuntu 22.04+). Tier 2 = skeleton support, not first-class (Rocky 9, Alpine). See [`governance/operational-truths.md`](../governance/operational-truths.md). |

---

## Key files

| Path | What it is |
|---|---|
| `config/manifest.yml` | Ports + image-version SSOT |
| `inventory/hosts.ini` | Physical-topology SSOT (hub_local / hub_remote / targets_*) |
| `inventory/local/vault.yml` | Encrypted Semaphore admin password (gitignored) |
| `inventory/local/vault.yml.example` | Template for the above (tracked) |
| `inventory/{dev,stag,prod}/` | Per-environment overlay (group_vars + hosts) |
| `extensions/eda/rules.json` | EDA rule definitions |
| `extensions/eda/events.schema.json` | Event contract (JSON Schema Draft-07) |
| `extensions/eda/rulebooks/clean-tiny.sh` | Disk-cleanup script for the disk_full self-healing path on Debian targets |
| `controller/semaphore/bootstrap.yml` | IaC provisioning (project / templates / token) |
| `controller/semaphore/docker-compose.yml` | Semaphore container spec |
| `controller/semaphore/.env.example` | Template for the Path B environment file |
| `controller/audit/reactor.py` | Reaction engine |
| `controller/audit/sink.py` | Audit log receiver |
| `controller/audit/relay.py` | Semaphore → sink forwarder (cursor-paginated) |
| `controller/audit/e2e/run.sh` | L4 disposable e2e harness (port 3320) |
| `playbooks/site.yml` | Main data-plane playbook (common + webserver + database) |
| `playbooks/deploy_hub.yml` | Path A entry point |
| `playbooks/manifest_sync.yml` | manifest → `.env` renderer |
| `playbooks/remediation/*.yml` | Per-rule remediation playbooks (executed on managed targets) |
| `roles/infra_baseline/` | OS baseline (apt + docker + ansible user) |
| `roles/ansispire_hub/` | Hub deployment (rsync + .env render + token mint) |
| `roles/ansispire_audit/` | Audit-stack deployment |
| `roles/common/` | Cross-cutting baseline (sysctl, SSH hardening, packages) |
| `roles/webserver/` | Nginx role |
| `roles/database/` | MySQL role |
| `Makefile` | All `make <target>` entry points; run `make help` for the list |

---

## Test specs (TSVS)

See [`reference/test-specs/INDEX.md`](../reference/test-specs/INDEX.md) — registry of every active TSVS with its test layer, owning surface, and status. Kept current as the test surface evolves; this guide deliberately does not enumerate so it cannot drift.

---

## Design / process docs

| Path | Purpose |
|---|---|
| [`ARCHITECTURE.md`](../../ARCHITECTURE.md) | Top-level architecture (read first) |
| [`reference/investigations/INDEX.md`](../reference/investigations/INDEX.md) | RCA / spike history; rows with `Applied` route to where the finding was actioned |
| [`reviews/`](../reviews/) | Per-task plan docs and per-round changelogs. Browse the topic directories for any specific workstream's history. |
| [`reviews/_archive/`](../reviews/_archive/) | Pre-W-R10 round-flat-named files; historical only |
