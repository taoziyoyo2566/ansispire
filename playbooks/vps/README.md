# VPS Lifecycle Playbooks

This directory is the retained VPS automation content on
`feat/target-architecture`.

The old local `plugins/vps_manager/` control surface is intentionally gone on
this branch. What remains here is the Ansible content that the target
architecture still needs: lifecycle playbooks, their templates, and
Semaphore-ready `extra_vars` examples.

## Current Contract

- Inventory must expose a `vps_targets` host or group.
- Task input is passed as the top-level mapping `vps_task`.
- Templates resolve relative to `playbooks/vps/`; there is no local
  `runtime/inbox/`, `runtime/state/`, or SSH-config side effect.
- The active Semaphore-native execution plan lives in
  `docs/reviews/feat-target-architecture/plan-semaphore-native-onboard-2026-06-10.md`
  with the implementer addendum in
  `plan-saberu-vps-takeover-execution-2026-06-24.md`.
- `VPS Audit` and `VPS Onboard` are provisioned as Semaphore templates against
  the `vps-fleet` static inventory. Ubuntu/Debian have completed the real
  onboard → managed-audit loop; RHEL remains partially validated.

## Retained Actions

This table is the **canonical** per-playbook list for the VPS lifecycle content;
the operations reference and the feature map link here instead of repeating it.

| Playbook | Purpose |
|---|---|
| `onboard.yml` | Bootstrap a new or reinstalled VPS, create the managed user, switch to a non-22 SSH management port, and apply the security baseline. |
| `modify.yml` | Apply managed-host changes to packages, firewall ports, fail2ban, and network tuning. |
| `audit.yml` | Run host-health checks such as disk, memory, reboot marker, and failed services. |
| `remove.yml` | Perform the optional remote cleanup step used when de-registering a host. |
| `docker_host.yml` | Prepare a managed VPS as a Docker host with safe defaults. |
| `deploy_compose.yml` | Upload and run a Docker Compose project, defaulting non-public exposure to `127.0.0.1`. |

`recover` is no longer a separate local-plugin concept. Recovery-style flows are
expected to reuse `onboard.yml` with bootstrap-capable access and the right
`vps_task` payload.

## Examples & Manual Use

- `examples/*.yml` are `extra_vars` payloads meant for Semaphore Task API or
  manual `ansible-playbook -e @file` usage. They are **not playbooks**; each
  carries a `# yaml-language-server: $schema=vps_task.schema.json` modeline so
  editors validate them against the `vps_task` envelope
  ([`examples/vps_task.schema.json`](examples/vps_task.schema.json)) instead of
  the Ansible playbook schema. Gate: `make test-vps-examples-schema`.
- End-to-end manual onboarding from a control node (the break-glass path):
  [`docs/operations/vps-onboard-runbook.md`](../../docs/operations/vps-onboard-runbook.md).
- `make vps-lifecycle-syntax` runs native Ansible syntax checks across all six
  playbooks.

## Intentionally Removed

- no local task inbox or archive management
- no `runtime/state/vps_inventory.yml` source of truth
- no SSH config generation on the operator machine
- no wrapper CLI for `new`, `submit`, `process`, or `tasks`

## Current validation and next step

- `make vps-lifecycle-syntax` covers all six playbooks.
- `make controller-vps-smoke` re-runs `VPS Audit` against the managed fleet and
  requires `success`, `changed=0`, `failed=0`, and `unreachable=0`.
- `TSVS-VPS-ONBOARD-E2E-001` records the u24+d13 real-host proof.
- Next: restore EPEL reachability on r9 (or use another recoverable RHEL host)
  and complete the remaining RHEL onboard path.
