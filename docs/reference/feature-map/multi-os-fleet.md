# Feature: Multi-OS Target Fleet

## Status

Initial implementation (TASK-007 round 1, 2026-05-19). Debian + RHEL families implemented; Alpine deferred to TASK-007.B.

## Overview

`[targets_*]` are managed VPS that receive `infra_baseline` only — they form the *data plane* under one or more hubs. The hub dispatches Ansible jobs against these hosts (via SSH from the Semaphore container) but the targets themselves run no control-plane software.

Two OS families are supported as of this round:

| Family | Distros | Path |
|---|---|---|
| **Debian** | Debian 13 (`d13`), Ubuntu 24.04 (`u24`) | `roles/infra_baseline/tasks/main.yml` inline block — apt + Docker CE repo + systemd |
| **RHEL** | Rocky Linux 9 (`rocky9`), AlmaLinux 9 (`alma9`) | `roles/infra_baseline/tasks/redhat.yml` — dnf + python3.11 pivot + Docker CE repo + SELinux container_manage_cgroup + systemd |
| Alpine | (none) | `main.yml` fail-stub; implementation pending TASK-007.B |

## Configuration SSOT

- **Physical inventory**: [`inventory/hosts.ini`](../../../inventory/hosts.ini) `[targets_debian]` / `[targets_rhel]` / `[targets_alpine]` / `[targets:children]` / `[targets:vars]`.
- **Prod inventory** ([`inventory/prod/hosts.ini`](../../../inventory/prod/hosts.ini)) **deliberately keeps the `[targets_*]` blocks empty**. Reason: `playbooks/site.yml` first play is `hosts: all`, so populating prod's targets would sweep them on every `make deploy-prod` / Semaphore "site.yml (check mode)" run — broadening blast radius beyond the role those hosts actually receive (infra_baseline only). The SSOT `inventory/hosts.ini` carries the targets; Semaphore consumes them via a dedicated `targets-managed` inventory record (see "Semaphore integration" below).
- **Connection vars** ([`inventory/hosts.ini` `[targets:vars]`](../../../inventory/hosts.ini)):
  - `ansible_user=ansible` (steady-state; created by the role on first run)
  - `ansible_ssh_private_key_file=~/.ssh/ansible`
  - `ansible_python_interpreter=/usr/bin/python3` (RHEL pivots to `/usr/bin/python3.11` mid-play; see Engineering mandates below)
  - `ansible_ssh_common_args=-o StrictHostKeyChecking=accept-new` (handles fresh fingerprints on first reach)

## Engineering mandates

- **Per-family `include_tasks` pattern**: `main.yml` dispatches to `redhat.yml` (RHEL) via `include_tasks` when `ansible_facts['os_family'] == "RedHat"`. Alpine still uses inline `fail:` until TASK-007.B; Debian still uses an inline `block:` because consolidating it into `debian.yml` was out of scope for this round.
- **Python pivot on RHEL 9** (`redhat.yml` D8): RHEL 9 ships `/usr/bin/python3` = 3.9, below `infra_baseline_python_min_version: 3.10`. The role's first RHEL task installs `python3.11` from AppStream using the existing 3.9 interpreter, then `set_fact: ansible_python_interpreter=/usr/bin/python3.11` + `setup:` re-gathers facts. The family-agnostic Python assert in `main.yml` now runs AFTER the per-family blocks (refactored task order) so it sees the pivoted interpreter on RHEL.
- **`--check` mode safety**: `redhat.yml` stat-probes `/usr/bin/python3.11` with `check_mode: false`. On a fresh host in `--check` mode (binary not yet present), the role emits a preview-only debug notice and ends the play for that host via `meta: end_host` — avoiding the downstream "module interpreter not found" failure. Real runs install python3.11 first and proceed normally.
- **SELinux on RHEL**: `getenforce` probe (with `check_mode: false` so it actually runs under `--check`); when status ∈ `{Enforcing, Permissive}`, installs `python3-libselinux + python3-libsemanage` and flips `container_manage_cgroup=on` via `ansible.posix.seboolean` (interpreter overridden to `/usr/bin/python3` for that one task since the system Python is what owns the SELinux Python bindings). Permissive mode is intentionally included so the persistent boolean is in place if the operator later switches to Enforcing.
- **Admin group is OS-family-aware**: Debian uses `sudo`, RHEL uses `wheel`. Single var `infra_baseline_mgr_admin_group` defaults to `sudo` in `defaults/main.yml` and is overridden to `wheel` in `vars/RedHat.yml`. NOPASSWD sudo is granted via `/etc/sudoers.d/ansible` on both families.
- **First-run vs steady-state**: fresh / OS-reinstalled hosts have only `root` + the operator's SSH key. The role creates the `ansible` user and copies `/root/.ssh/authorized_keys` to `/home/ansible/.ssh/`. After first successful run, inventory steady-state is `ansible_user=ansible` with `become: true`. Fresh-host onboarding uses the Makefile knob `ANSIBLE_USER=root` (see below).

## Deployment commands

| Command | Effect |
|---|---|
| `make target-deploy TARGET_NODE=all` | Apply `infra_baseline` to every host in `[targets:children]` |
| `make target-deploy TARGET_NODE=debian` | Only `[targets_debian]` |
| `make target-deploy TARGET_NODE=rhel` | Only `[targets_rhel]` |
| `make target-deploy TARGET_NODE=<alias>` | Single host (e.g. `rocky9`, `d13`) |
| `make target-deploy TARGET_NODE=<alias> ANSIBLE_USER=root` | Fresh-host bootstrap (before role creates `ansible` user) |
| `make target-deploy-check ...` | `--check --diff` variant of any above |
| `make target-ping` | Read-only connectivity probe via [`playbooks/ping_targets.yml`](../../../playbooks/ping_targets.yml); no role applied |

## Semaphore integration

[`controller/semaphore/bootstrap.yml`](../../../controller/semaphore/bootstrap.yml) sets up TWO things for TASK-007 (idempotent — both skipped if they already exist):

1. A dedicated **`targets-managed`** Semaphore inventory record pointing at `inventory/hosts.ini` (the SSOT). This deliberately bypasses `inventory/prod/hosts.ini` so the targets don't get swept into the prod `hosts: all` lane.
2. A **`Ping all targets`** Job Template that runs `playbooks/ping_targets.yml` against the `targets-managed` inventory.

Both materialize on the next `make hub-deploy` after this branch lands. End-to-end execution additionally requires:

- The hub host has an SSH private key that authorizes against each target's `ansible` user (typically the same key used by the operator, copied into the hub during deployment — out-of-band setup not covered by this role).
- The Semaphore container's bind-mount can read `/workspace/inventory/hosts.ini` (which carries the populated `[targets_*]` blocks).

## Dependencies

- [`roles/infra_baseline/`](../../../roles/infra_baseline/) — the role this feature depends on; per-family files: `tasks/main.yml`, `tasks/redhat.yml`, `vars/RedHat.yml`, `defaults/main.yml`.
- [`playbooks/deploy_target.yml`](../../../playbooks/deploy_target.yml) + [`playbooks/ping_targets.yml`](../../../playbooks/ping_targets.yml).
- `ansible.posix` collection (`>= 2.1.0`) — provides `seboolean`.

## Known limitations (this round)

- **Alpine**: no host provisioned; `main.yml` Alpine block remains a fail-stub. Tracked as **TASK-007.B**.
- **Per-OS Molecule coverage**: existing 4 scenarios cover Debian only. A `roles/infra_baseline/molecule/redhat/` scenario would catch regressions inside the dnf/SELinux path.
- **`[hub_remote]` orphan**: the `ans-hk01` reference in `inventory/hosts.ini` `[hub_remote]` points at an IP (89.185.26.211:1156) that was wiped by the user's OS reinstall on 2026-05-19. Same IP is now Debian 13 target `d13` (port 22). Cleanup is tracked as a separate TODO follow-up; not in TASK-007 scope (W-R13 minimum-modification).
- **End-to-end Semaphore "Ping all targets" execution**: declared in `bootstrap.yml` but not materialized this round (requires a running Semaphore + bootstrap re-run + hub-side SSH key authorized on targets).

## Related references

- Plan-doc + per-round changelogs: [`docs/reviews/feat-multi-os-target-fleet/`](../../reviews/feat-multi-os-target-fleet/)
- TODO entry: [`TODO.md`](../../../TODO.md) §TASK-007
- Hub deployment feature-map: [`hub-deployment.md`](./hub-deployment.md) — control plane counterpart to this data-plane feature.
