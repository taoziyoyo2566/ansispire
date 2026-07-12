# Feature: VPS Lifecycle Content

## Status
🟡 **Semaphore-native execution is proven on Ubuntu/Debian and partial on RHEL.**
The local `vps_manager` surface is removed. `VPS Audit` and `VPS Onboard` run
from Semaphore against `vps-fleet`; u24+d13 completed onboard → managed-channel
audit with `changed=0`. The r9 path first blocked at EPEL reachability, so the
remaining RHEL steps are not yet proven.

## Overview

`playbooks/vps/` is the kept part of the old VPS management work: the actual
Ansible lifecycle playbooks and their templates. The target architecture still
wants these actions, but no longer wants a second local control plane for task
inbox, runtime state, SSH config generation, or task history.

The intended control-plane truth is:

- Semaphore Inventory
- Semaphore Key Store
- Semaphore Task API

## Management Entry Points

The active and deferred entry points must converge on one managed-state truth:

| Entry point | Primary user | Current carrier | Writes managed state? | Current status |
|---|---|---|---|---|
| Semaphore UI | Human operator | `vps-fleet` + Key Store + `VPS Audit` / `VPS Onboard` | Yes | **Active MVP path.** Real audit on u24/r9/d13; complete onboard loop on u24+d13. |
| Browser Wizard / Worker REST | Deferred automation surface | `cf-worker/` | Intended to write the same static inventory | CRUD probe/deploy exists, but `onboard-bare` still emits the superseded `managed_private_key` contract. Do not use it for onboard until code/tests are refreshed. |
| Manual Ansible CLI | Maintainer / break-glass operator | `docs/operations/vps-onboard-runbook.md` + `ansible-playbook playbooks/vps/*.yml` | No, not by itself | Emergency path. It must use one fleet key for bootstrap transport and managed validation, then register the resulting managed channel in `vps-fleet`. |

Convergence rule: **Semaphore `static` inventory is the only managed-state
truth.** Local runtime inventory files such as `runtime/onboard/hosts.ini` and
`runtime/onboard/hosts.managed.ini` are disposable execution input, not durable
fleet state. A host that exists only in local runtime files is invisible to the
Semaphore UI, audit templates, and any future Worker/API surface.

## Operational Entry Points

- Syntax gate: `make vps-lifecycle-syntax`
- Operator reference: [`docs/operations/vps-lifecycle.md`](../../operations/vps-lifecycle.md)
- Directory README: [`playbooks/vps/README.md`](../../../playbooks/vps/README.md)
- Operator guide: [`docs/feat-target-architecture/operator-guide.md`](../../feat-target-architecture/operator-guide.md)
- Active plan: [`plan-semaphore-native-onboard-2026-06-10.md`](../../reviews/feat-target-architecture/plan-semaphore-native-onboard-2026-06-10.md)

## Retained Actions

The canonical per-playbook list and `vps_task` contract live in
[`playbooks/vps/README.md`](../../../playbooks/vps/README.md) — single source of
truth, do not duplicate the table here. Step-by-step manual usage is in
[`docs/operations/vps-onboard-runbook.md`](../../operations/vps-onboard-runbook.md).

## Current Contract

- Inventory must define `vps_targets`.
- Task payload is injected as top-level `vps_task`.
- Examples under `playbooks/vps/examples/` are `vps_task` payload references.
- Semaphore templates bind `vps-audit-env` / `vps-onboard-env`; their JSON injects
  `vps_task` and their process environment injects the vault-free `ANSIBLE_CONFIG`.
- `onboard.yml` accepts inline `public_key_content`. Managed-channel validation
  uses task-level `ansible_user` / `ansible_port` and reuses the run's transport
  key (Semaphore Key Store `--private-key`, or the equivalent manual run key).
  There is no mounted or payload-supplied managed private-key path.
- The deferred Worker `POST /vps` currently accepts explicit `mode` values:
  - `register-managed` records an already-managed SSH channel with
    `lifecycle_state=managed` and never calls `onboard.yml`.
  - `onboard-bare` records the bootstrap channel with
    `lifecycle_state=onboarding`, requires `SEMAPHORE_ONBOARD_TEMPLATE_ID`,
    and triggers `onboard.yml`. Post-success promotion to managed inventory
    remains a follow-up.
- The Worker still requires `managed_private_key` and emits
  `managed.ansible_key.private_key`; that field is obsolete and ignored by the
  current playbook. This is a known deferred-surface incompatibility, not an
  active Semaphore UI requirement.
- Worker inventory operations require the configured Semaphore inventory to be
  `type: "static"`. `file` inventories fail closed with `412`; they are never
  parsed as INI blobs or rewritten as static inventories.
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
| L1/L4 probe | `npm test --prefix cf-worker`, `npm run integration:live --prefix cf-worker` | Deferred Worker parser/client tests plus probe static-inventory CRUD; does not prove current onboard compatibility. |
| L5/manual+API | `TSVS-VPS-ONBOARD-E2E-001` | Real u24+d13 onboard → managed-channel audit proof. |
| L5 repeatable | `make controller-vps-smoke` | Managed-fleet `VPS Audit` must be success with changed/failed/unreachable all zero. |

The previous local lifecycle unit test belongs to the removed `vps_manager`
surface and is retired as an active coverage signal on this branch.

## Known Boundaries

- Semaphore template provisioning is implemented in `controller/semaphore/bootstrap.yml`; production inventory migration remains separate from the dedicated `vps-fleet` inventory.
- The checked-in Worker deployment config must not point at production
  `targets-managed` inventory id `2` while it remains a Semaphore `file`
  inventory. Live probe deploys should explicitly override non-secret vars to
  the dedicated static probe inventory.
- The Worker inventory format still stores `ansible_ssh_private_key_id` as a
  custom variable. Standard Ansible does not consume that variable directly;
  the Semaphore credential-mapping model must be finalized before real onboard
  task execution is enabled.
- The Worker REST API now has temporary Basic Auth on all routes except
  `/health`, but this is a shared operator gate rather than full API
  authorization. Keep it behind trusted Cloudflare controls until per-client
  authz or Cloudflare Access/service-token policy is solved.
- RHEL full onboard is not yet proven beyond the EPEL reachability blocker.
- Worker onboard compatibility is deferred and currently stale against the Key Store key-reuse contract.
- The old `vps_manager` MVP remains historical context only on older branches and retired specs.
