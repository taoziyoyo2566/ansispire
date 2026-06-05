# Feature: VPS Lifecycle Content

## Status
✅ **Branch cleanup landed on 2026-06-03 for `feat/target-architecture`.**
The local `vps_manager` control surface is removed on this branch. The retained
VPS lifecycle Ansible content now lives under `playbooks/vps/`.

## Overview

`playbooks/vps/` is the kept part of the old VPS management work: the actual
Ansible lifecycle playbooks and their templates. The target architecture still
wants these actions, but no longer wants a second local control plane for task
inbox, runtime state, SSH config generation, or task history.

The intended control-plane truth is:

- Semaphore Inventory
- Semaphore Key Store
- Semaphore Task API

## Operational Entry Points

- Syntax gate: `make vps-lifecycle-syntax`
- Operator reference: [`docs/operations/vps-lifecycle.md`](../../operations/vps-lifecycle.md)
- Directory README: [`playbooks/vps/README.md`](../../../playbooks/vps/README.md)
- Owner plan: [`docs/reviews/feat-target-architecture/plan-2026-05-25.md`](../../reviews/feat-target-architecture/plan-2026-05-25.md)

## Retained Actions

| Playbook | Remote | Scope |
|---|---:|---|
| `playbooks/vps/onboard.yml` | yes | Bootstrap through provider SSH, create the managed user, install keys, configure sudo, UFW/fail2ban, and switch to a non-22 management port. |
| `playbooks/vps/modify.yml` | yes | Apply package, firewall, fail2ban, and network-tuning changes through managed SSH. |
| `playbooks/vps/audit.yml` | yes | Check disk, memory, failed services, and reboot-required marker. |
| `playbooks/vps/remove.yml` | no by default | Optional remote cleanup step for de-registration. |
| `playbooks/vps/docker_host.yml` | yes | Install Docker Engine and daemon defaults. |
| `playbooks/vps/deploy_compose.yml` | yes | Upload and run a Compose project, with non-public exposure forced to `127.0.0.1`. |

## Current Contract

- Inventory must define `vps_targets`.
- Task payload is injected as top-level `vps_task`.
- Examples under `playbooks/vps/examples/` are `extra_vars` payload references.
- Recovery-style flows are expected to reuse `onboard.yml`; there is no
  separate `recover` dispatcher in this branch.

## Explicit Non-Features On This Branch

- no local task inbox / archive state machine
- no `runtime/state/vps_inventory.yml`
- no SSH config generation on the operator machine
- no Python wrapper CLI
- no carried-over schema from the removed local plugin

## Test Coverage

| Layer | Carrier | Scope |
|---|---|---|
| L0 | `make vps-lifecycle-syntax` | Native Ansible syntax-check across all retained lifecycle playbooks. |

The previous local lifecycle unit test belongs to the removed `vps_manager`
surface and is retired as an active coverage signal on this branch.

## Known Boundaries

- Semaphore Inventory / Task API wiring is still a follow-up phase, not a done state.
- Real Semaphore-driven execution on this branch does not yet have a dedicated TSVS.
- The old `vps_manager` MVP remains historical context only on older branches and retired specs.
