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

## Management Entry Points

There are three supported entry-point shapes, but they must converge on one
managed-state truth:

| Entry point | Primary user | Current carrier | Writes managed state? | Current status |
|---|---|---|---|---|
| Browser Wizard | Human operator | `GET /` in `cf-worker/` | Yes, through Semaphore `static` inventory | Deployed and CRUD-verified against probe inventory `3`; add flow now separates register-managed from onboard-bare; onboard/audit task IDs still missing. |
| Worker REST API | Other applications / automation | `GET/POST /vps`, `PUT/DELETE /vps/:alias`, `POST /vps/:alias/audit` | Yes, same Worker code path as the Wizard | Protected by temporary Worker Basic Auth; not approved as an open multi-client API until per-client authz or Cloudflare Access/service-token policy is documented. |
| Manual Ansible CLI | Maintainer / break-glass operator | `docs/operations/vps-onboard-runbook.md` + `ansible-playbook playbooks/vps/*.yml` | No, not by itself | Bootstrap/emergency path only. After a host is manually prepared, it must be registered into Semaphore through the Worker/API register-managed path. |

Convergence rule: **Semaphore `static` inventory is the only managed-state
truth.** Local runtime inventory files such as `runtime/onboard/hosts.ini` and
`runtime/onboard/hosts.managed.ini` are disposable execution input, not durable
fleet state. A host that exists only in local runtime files is invisible to the
Wizard, REST API, audit templates, and future Semaphore-driven lifecycle tasks.

## Operational Entry Points

- Syntax gate: `make vps-lifecycle-syntax`
- Operator reference: [`docs/operations/vps-lifecycle.md`](../../operations/vps-lifecycle.md)
- Directory README: [`playbooks/vps/README.md`](../../../playbooks/vps/README.md)
- Owner plan: [`docs/reviews/feat-target-architecture/plan-2026-05-25.md`](../../reviews/feat-target-architecture/plan-2026-05-25.md)

## Retained Actions

The canonical per-playbook list and `vps_task` contract live in
[`playbooks/vps/README.md`](../../../playbooks/vps/README.md) — single source of
truth, do not duplicate the table here. Step-by-step manual usage is in
[`docs/operations/vps-onboard-runbook.md`](../../operations/vps-onboard-runbook.md).

## Current Contract

- Inventory must define `vps_targets`.
- Task payload is injected as top-level `vps_task`.
- Examples under `playbooks/vps/examples/` are `vps_task` payload references; the Phase 2 Worker carries runtime payloads through Semaphore task-level `environment` JSON.
- Worker `POST /vps` accepts explicit `mode` values:
  - `register-managed` records an already-managed SSH channel with
    `lifecycle_state=managed` and never calls `onboard.yml`.
  - `onboard-bare` records the bootstrap channel with
    `lifecycle_state=onboarding`, requires `SEMAPHORE_ONBOARD_TEMPLATE_ID`,
    and triggers `onboard.yml`. Post-success promotion to managed inventory
    remains a follow-up.
- `onboard.yml` requires `vps_task.managed.ansible_key.private_key` because
  managed-channel validation shells out to `ssh -i <path>` from the Semaphore
  execution environment. The Worker now rejects onboard-triggering requests
  that omit the corresponding `managed_private_key` field instead of allowing a
  late playbook failure.
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
| L1/L4 probe | `npm test --prefix cf-worker`, `npm run integration:live --prefix cf-worker` | Worker parser/client unit tests plus live Semaphore probe static inventory CRUD. |

The previous local lifecycle unit test belongs to the removed `vps_manager`
surface and is retired as an active coverage signal on this branch.

## Known Boundaries

- Semaphore Inventory / Task API wiring is implemented by `cf-worker/` and verified against a live probe static inventory; real lifecycle template provisioning and production inventory migration remain follow-up work.
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
- Real Semaphore-driven execution on this branch does not yet have a dedicated TSVS.
- The old `vps_manager` MVP remains historical context only on older branches and retired specs.
