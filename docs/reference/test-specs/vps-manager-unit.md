# TSVS-VPS-MANAGER-UNIT-001 — VPS Manager Local Lifecycle

## Status
Active — first registered 2026-05-14.

## Surface
`plugins/vps_manager/vps_manager.py` and its local runtime state model.

## Carrier

```bash
make test-vps-manager
```

The carrier runs `plugins/vps_manager/tests/test_vps_manager.py` with
`--no-execute` semantics through the Python API, so it never contacts a remote
VPS and does not require Ansible network access.

## Assertions

- A valid `onboard` task moves from `pending/` to `done/`.
- Onboard writes an active server record to `runtime/state/vps_inventory.yml`.
- Onboard renders the generated SSH config block with the non-22 managed port.
- Onboard stores separate automation and operator identity paths: follow-up
  Ansible actions use `ansible_identity_file`, while generated SSH config uses
  `ssh_config_identity_file`.
- The guided onboarding CLI defaults the managed user to `ansible` when
  `--managed-user` is omitted.
- Draft submission can select a unique draft by alias and rejects ambiguous
  alias matches without moving any draft.
- A repeated `onboard` for an already active alias is rejected during preflight
  and left in `pending/`.
- A `recover` task is accepted only for an existing alias, reuses the onboard
  inventory update path, and the CLI can generate it from existing inventory
  defaults.
- The interactive `recover` confirmation defaults to processing the current
  task immediately, without leaving an extra draft or pending file on success.
- A successful immediate `recover` archives older `onboard`/`recover` drafts
  for the same alias while leaving other same-alias task drafts in place.
- Generated VPS Manager inventories pin `ansible_python_interpreter` to
  `/usr/bin/python3`.
- Inline password fields and missing password environment variables are
  rejected during preflight without consuming the pending task.
- In an interactive process, a missing password environment variable can be
  supplied through a hidden prompt without writing the secret to the successful
  task archive.
- `remove` deletes the local inventory record and removes the generated SSH
  config block.
- Non-public `deploy_compose` exposure must bind to `127.0.0.1`; violations
  block before execution and leave the pending task untouched.

## Boundary

The carrier does not mock or assert Ansible module effects. Remote behavior
belongs to `make vps-manager-syntax`, Ansible `--check --diff` runs with real
task input, and a future real-target smoke.

## Out of Scope

- Real SSH connectivity and remote rollback behavior.
- UFW/fail2ban effects on a live host.
- Docker Engine installation and Compose application health on a real VPS.
