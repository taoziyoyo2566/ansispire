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
- The owner plan for the eventual Semaphore Inventory / Key Store / Task API
  cutover lives in:
  - `docs/reviews/feat-target-architecture/plan-2026-05-25.md`
  - `docs/reviews/feat-target-architecture/design-2026-05-26.md`

## Retained Actions

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

## Examples

- `examples/*.yml` are `extra_vars` payloads meant for Semaphore Task API or
  manual `ansible-playbook -e @file` usage.
- `make vps-lifecycle-syntax` runs native Ansible syntax checks across all six
  playbooks.

## Intentionally Removed

- no local task inbox or archive management
- no `runtime/state/vps_inventory.yml` source of truth
- no SSH config generation on the operator machine
- no wrapper CLI for `new`, `submit`, `process`, or `tasks`

## Next Steps

- Phase 1: verify the Semaphore Inventory / Task API contract
- Phase 2: add CF Worker or other API-facing task submission
- Phase 3: wire these playbooks into the accepted Semaphore-first execution path
