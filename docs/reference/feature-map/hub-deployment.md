# Feature: Hub Deployment

## Status

Stable. Path A (Ansible role-based) and Path B (docker-compose) both shipped in TASK-001 (closed 2026-05-10). Both deploy the same hub image set; they differ only in lifecycle.

## Overview

The "hub" is one machine that runs the full Ansispire control + audit stack. Two deployment paths target this same configuration:

- **Path A** (`make hub-deploy HUB_NODE={local|remote|all}`): the `ansispire_hub` Ansible role applies onto a node in `[hub_local]` or `[hub_remote]`. Persistent across reboots; idempotent.
- **Path B** (`make controller-up && make controller-bootstrap && make controller-audit-up`): docker-compose on the workstation. Disposable / dev-grade.

Path A is the production deployment path; Path B is the developer's iteration loop.

## Components deployed (per hub host)

- **Semaphore container** — control plane (web UI, REST API, RBAC). SQLite-backed.
- **Audit sink + relay + reactor** — three Python micro-services packaged as containers, sharing `ansispire-controller-net`.
- **Bootstrap inventory + project + templates + API token** — created via `controller/semaphore/bootstrap.yml` (IaC, UI-zero-touch).
- **`ansible` user on the host** (Path A only) — NOPASSWD sudo, SSH key copied from `/root/.ssh/authorized_keys`.

## Configuration SSOT

- **Ports + image versions**: [`config/manifest.yml`](../../../config/manifest.yml). Rendered into `controller/semaphore/.env` by `make manifest-sync`. See [`docs/user-guide/03-configuration.md`](../../user-guide/03-configuration.md) §1.
- **Hub topology**: [`inventory/hosts.ini`](../../../inventory/hosts.ini). `[hub_local]` (workstation) / `[hub_remote]` (real VPS) / `[hub:children]` (union).
- **Admin credential**: [`inventory/local/vault.yml`](../../../inventory/local/) (encrypted).

## Engineering mandates

- **All-in-One**: control + audit + reactor co-locate on the same host. (Future: TASK-003 Controller HA.)
- **State separation**: stateful files live at `/var/lib/ansispire/state/` on the hub — outside the rsync target dir, so `rsync --delete` cannot wipe them across deploys:
  - `.eda_token` — Semaphore M2M API token consumed by the reactor.
  - `.security_keys` — JSON `{access_key_encryption, cookie_hash, cookie_encryption}` minted on first deploy and rendered into `.env`; **deleting it makes every stored Semaphore AccessKey undecryptable and invalidates every active session** — restore from backup, do not re-mint.
- **Rsync hygiene**: 21 exclude patterns enforced (`roles/ansispire_hub/tasks/main.yml`) across 4 categories: local-artefacts, secrets, stateful files, docs. Verify each `--check` run with `grep -E "\.env|\.secrets|\.demo_|users\.yml|\.eda_token"`.
- **OS-family gating**: `infra_baseline` accepts Debian/Ubuntu (Tier 1); RHEL/Alpine paths exist as explicit-fail placeholders pending TASK-007 (multi-OS target fleet).
- **Inventory integrity**: every group referenced by `[<env>:children]` must be defined in the same inventory source — Ansible 2.20+ rejects forward references silently.
- **No UI provisioning**: every Semaphore resource (project / template / inventory / user) must come from `bootstrap.yml`. The UI is for inspection and one-off vault key entry only. Full ownership map per resource type: [`docs/governance/iac-vs-ui-boundary.md`](../../governance/iac-vs-ui-boundary.md).
- **Admin password enforcement on every deploy (post-WU-2)**: the role runs `semaphore user change-by-login` on every `make hub-deploy`, so rotating `vault_semaphore_admin_password` and re-deploying is enough to refresh the admin credential. The previous structure gated user-add inside the first-deploy token-mint block and silently dropped re-deploy rotations.
- **API contract preflight (post-WU-4)**: [`bootstrap_preflight.yml`](../../../controller/semaphore/bootstrap_preflight.yml) is imported at the top of `bootstrap.yml`. Schema mode (default, ~2 s) verifies auth + top-level GETs return arrays with id/name fields; full mode (`make test-api-contract`, ~30–60 s) walks all 5 project-scoped GETs + token mint on a throwaway project. CI runs the full mode in matrix `[pinned, latest]` (latest is `continue-on-error` — early warning of upstream drift). Skippable per-run with `-e skip_preflight=true`.

## Deployment paths summary

| Aspect | Path A | Path B |
|---|---|---|
| Entry | `make hub-deploy HUB_NODE=...` | `make controller-up && make controller-bootstrap && make controller-audit-up` |
| Inventory | `inventory/hosts.ini` (`[hub_local]` / `[hub_remote]`) | n/a (compose on workstation) |
| Persistence | Survives reboot; idempotent re-deploy | Wiped by `make controller-reset` |
| Secrets | Encrypted `inventory/local/vault.yml` + `.vault_pass` | Plaintext `controller/semaphore/.env` (gitignored) |
| Token location | `<hub>:/var/lib/ansispire/state/.eda_token` | `controller/semaphore/.secrets` |

## Operational entry points

- **Maintainer 速查**: [`docs/operations/hub-deployment.md`](../../operations/hub-deployment.md) — terse command reference (deploy / verify / reset / troubleshooting).
- **First-time deep dive**: [`docs/user-guide/02-quickstart-eda.md`](../../user-guide/02-quickstart-eda.md) §6 — Path A walkthrough with rationale and failure paths.

## Dependencies

- [`infra_baseline`](../../../roles/infra_baseline/) role: OS prep (apt + docker + ansible user).
- [`ansispire_hub`](../../../roles/ansispire_hub/) role: rsync code, render `.env`, mint token.
- [`ansispire_audit`](../../../roles/ansispire_audit/) role: bring up the audit-stack containers.
- [`bootstrap.yml`](../../../controller/semaphore/bootstrap.yml): IaC provisioning.
- [`audit-plane`](./audit-plane.md) feature: dependency for the reaction loop.
- [`eda-core`](./eda-core.md) feature: dependency for the reactor and rule contract.
