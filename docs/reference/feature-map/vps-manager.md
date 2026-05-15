# Feature: VPS Manager Plugin

## Status
✅ **MVP implemented 2026-05-14; Ubuntu 24.04 real-target smoke passed
2026-05-15**. Local task lifecycle, validation, redacted archive, YAML
inventory, SSH config generation, examples, and action playbooks exist.

## Overview
`plugins/vps_manager/` is a lightweight VPS lifecycle extension. It consumes
one-shot task YAML files from `runtime/inbox/vps/pending/`, moves them through
`processing/ → done|failed`, dispatches remote changes through Ansible
playbooks, and records long-lived host state in
`runtime/state/vps_inventory.yml`.

## Operational Entry Points

- Initialize runtime: `make vps-manager-init`
- Create a validated onboarding draft: `make vps-new`
- Recover an existing alias through bootstrap SSH: `make vps-recover ALIAS=<alias>`
  defaults to processing the confirmed task immediately.
- Submit a draft to pending: `make vps-submit ALIAS=<alias>`; use
  `FILE=<draft.yml>` when multiple drafts share the same alias.
- List task files by state: `make vps-tasks`
- Process pending tasks: `make vps-manager-process`
- Validate one task file: `make vps-manager-validate FILE=<task.yml>`
- Local lifecycle tests: `make test-vps-manager`
- User guide: [`plugins/vps_manager/README.md`](../../../plugins/vps_manager/README.md)

## Supported Actions

| Action | Remote | Scope |
|---|---:|---|
| `onboard` | yes | Bootstrap through provider SSH, create managed user, install key, configure sudo, UFW/fail2ban, managed SSH and `ssh.socket` drop-ins, and local SSH config. |
| `recover` | yes | Restore management for an existing alias through bootstrap SSH when managed SSH is broken or after provider OS reinstall. |
| `modify` | yes | Apply package, firewall, fail2ban, and network tuning changes through managed SSH. |
| `audit` | yes | Check disk, memory, failed services, reboot marker, and update inventory health on success. |
| `remove` | no by default | Remove local inventory and generated SSH config state; remote cleanup is opt-in. |
| `docker_host` | yes | Install Docker Engine and daemon defaults. |
| `deploy_compose` | yes | Upload and run a Compose project, with non-public exposure forced to `127.0.0.1`. |

## Safety Contract

- `ssh.managed_port` must be an integer from 1024 to 65535 and must not be 22.
- Inline passwords and inline private key material are rejected; tasks should
  reference `password_env` and key file paths.
- Generated VPS Manager inventories pin `ansible_python_interpreter` to
  `/usr/bin/python3` to avoid interpreter auto-discovery drift.
- Missing `password_env` values are collected with an interactive hidden
  password prompt during `process` when a TTY is available; non-interactive
  runs must provide the environment variable up front.
- Automation and operator credentials are separated:
  `managed.ansible_key` is the private key path used by follow-up Ansible
  actions, while `managed.personal_keys` uploads operator public keys for
  human SSH access.
- New guided onboarding tasks default to `managed.user: ansible` when the
  operator does not supply another managed user.
- Ubuntu/Debian hosts using systemd socket activation are staged with both the
  bootstrap and managed SSH ports open, then locked down to the managed port
  after the managed login succeeds.
- SSH hardening is written to `/etc/ssh/sshd_config.d/00-ansispire.conf` so it
  takes precedence over provider and cloud-init drop-ins that may enable root
  or password login.
- Successful and remote-execution failed archives are redacted.
- YAML validation errors and non-interactive missing environment variables are
  preflight blockers: the run exits non-zero, prints the errors, and leaves the
  task in `pending/` for correction.
- A repeated `onboard` for an active alias is rejected; managed-host changes
  use `modify`, and bootstrap-based recovery uses `recover`.
- A successful immediate `recover` archives older same-alias `onboard` and
  `recover` drafts to keep alias-based submit unambiguous without hiding
  unrelated follow-up tasks.
- Docker application exposure is separate from host UFW; non-public modes must
  bind to `127.0.0.1`.

## State Sources

- Task inbox/history:
  `runtime/inbox/vps/{drafts,pending,processing,done,failed,cancelled,archived}/`
- Long-lived host state: `runtime/state/vps_inventory.yml`
- Task locks and transient Ansible inventory/vars: `runtime/state/tasks/`
- Ansible logs: `runtime/logs/vps_manager/`
- Generated SSH config: per-task `local.ssh_config_file`, defaulting to
  `~/.ssh/config.d/ansispire.conf`

`runtime/` is gitignored. Task examples and templates live under
`plugins/vps_manager/examples/` and `plugins/vps_manager/templates/`.

## Test Coverage

| Layer | Carrier | Scope |
|---|---|---|
| L1 | `make test-vps-manager` | Local lifecycle: archive movement, inventory and SSH config updates, duplicate onboard rejection, secret redaction, compose exposure guard. |
| L0 | `yamllint`, `ansible-lint`, `make vps-manager-syntax` | YAML lint, Ansible lint, and native syntax-check for action playbooks. |

Python tests intentionally stop at the local task manager boundary. UFW,
fail2ban, Docker, Compose, and SSH reachability belong to Ansible check/diff
coverage and a future real-target smoke, not mocked Python unit tests.

## Known Boundaries

- Real remote onboarding has one Ubuntu 24.04 operator smoke, but is not
  covered by a disposable Molecule scenario yet.
- OS support is centered on Debian/Ubuntu first; RHEL paths need hardening.
- `rotate_key`, Cloudflare Tunnel provisioning, and signed task files are
  future actions, not part of the MVP.
