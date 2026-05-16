# Feature: VPS Runner Plugin

## Status
✅ **Code complete 2026-05-16 (Round 3); operator docs + Makefile sync 2026-05-16 (Round 4-a).** Pending: live 3-host concurrency test (blocked on dev VPS SSH access) + cutover of legacy `vps_manager/` (Round 4-b, awaits user feature-parity ack).

Replaces the legacy `plugins/vps_manager/` (the three-layer anti-Ansible pattern: subprocess wrapping + custom callback + custom inventory state). See [`docs/reference/investigations/IVG-MULTI-SERVER-ANSIBLE-PRACTICE.md`](../investigations/IVG-MULTI-SERVER-ANSIBLE-PRACTICE.md) and [`IVG-REFLECT-BESTPRACTICE-GAP.md`](../investigations/IVG-REFLECT-BESTPRACTICE-GAP.md) for the framework best-practice analysis that drove the rewrite.

## Overview
`plugins/vps_runner/` is a thin Python CLI on top of [`ansible-runner`](https://ansible.readthedocs.io/projects/runner/) that drives standard Ansible playbooks against a standard inventory tree. No subprocess wrapping, no inbox state machine, no custom callback. Per-host structured results come from `Runner.stats` + `Runner.host_events()`; concurrency is the Ansible-native `forks` mechanism.

## Operational Entry Points

- Operator guide: [`docs/operations/vps-runner.md`](../../operations/vps-runner.md)
- Run unit tests (no SSH): `make test-vps-runner`
- Run integration test (real ansible-runner vs TEST-NET-1, ~11s): `make test-vps-runner-integration`
- Ansible syntax check on playbooks: `make vps-runner-syntax`
- CLI usage: `python -m plugins.vps_runner.cli {list|audit|onboard|modify|remove} --env {dev,stag,prod}`

## Supported Actions

| Action | Remote | Scope |
|---|---:|---|
| `list` | no | Display managed hosts in the given env (alias / connection / status / last_action / updated_at). Pure local YAML read. |
| `audit` | yes | Per-host probe: ping, uptime, disk usage, memory, OS facts. Read-only and idempotent. |
| `onboard` | yes | Apply `onboard.yml` to one alias. With `--first-time --ask-pass --ask-become-pass`, bootstraps from `root@22`-style state into managed user + non-22 SSH port + UFW + fail2ban + (optionally) Docker. Idempotent re-onboard supported. |
| `modify` | yes | Apply `modify.yml` with a `vps_changes` extravar: packages (install/remove), UFW TCP allows/removes, fail2ban toggle, network_tuning. Each section optional. |
| `remove` | optional | Drop alias from inventory; remote `remove.yml` (strip Ansispire sshd drop-ins + `sshd -t`) is opt-in via `--cleanup-remote`. UFW rules and the managed user are intentionally **left** for manual cleanup. |

## Architecture

### Module layout
```text
plugins/vps_runner/
  __init__.py
  plugin.yaml              # plugin manifest
  cli.py                   # argparse CLI dispatch (~370 lines)
  vps_runner.py            # core library (~333 lines)
  playbooks/
    onboard.yml            # 613 lines, host_vars-driven
    modify.yml             # 144 lines, `vps_changes` extravar driven
    remove.yml             # 43 lines, opt-in remote cleanup
    audit.yml              # 64 lines, ping + uptime + disk + memory probe
    templates/
      sshd_ansispire.conf.j2      # sshd drop-in
      ssh_socket_ansispire.conf.j2 # systemd ssh.socket drop-in
      sudoers_ansispire.j2         # NOPASSWD sudoers fragment
      fail2ban_sshd.local.j2       # fail2ban sshd jail
      docker_daemon.json.j2        # docker daemon.json
      ssh_config_entry.j2          # operator-side ~/.ssh/config.d/ entry
  tests/
    __init__.py
    test_vps_runner.py     # 22 tests (21 unit + 1 integration)
```

### Inventory contract
```text
inventory/vps_runner/<env>/
  hosts.yml                # all.children.vps_targets.hosts: { <alias>: }
  host_vars/<alias>.yml    # connection params + role vars + vps_runner.* metadata
```

`host_vars/<alias>.yml` schema:

| Section | Owner | Keys |
|---|---|---|
| top-level Ansible | playbooks read directly | `ansible_host`, `ansible_port`, `ansible_user`, `ansible_python_interpreter`, `ansible_ssh_private_key_file` |
| `security:` | playbooks read directly | `root_login_disabled`, `password_login_disabled`, `ufw_enabled`, `fail2ban_enabled` |
| `features:` | playbooks read directly | `base_packages`, `unattended_upgrades`, `system_limits`, `swap`, `network_tuning`, `ufw`, `fail2ban`, `docker` |
| `vps_runner:` | **CLI reads/writes; playbooks read connection-related sub-keys** | `bootstrap_port`, `bootstrap_user`, `managed_port`, `managed_user`, `identity_file`, `ansible_public_key`, `personal_keys[]`, `status`, `last_run`, `updated_at` |

### Execution flow

```text
CLI subcommand
  → core.run_playbook(
       project_dir=PROJECT_ROOT,
       playbook=<rel path>,
       inventory=<abs path inventory/vps_runner/<env>/>,
       artifact_dir=runtime/logs/vps_runner/,
       ident=<run_id>,
       extravars=<subcommand-specific>,
       envvars={ANSIBLE_CONFIG: ansible.cfg},
       suppress_env_files=True,
       rotate_artifacts=10,
       forks=20)
  → ansible_runner.run(...)
  → Runner.stats + Runner.host_events()
  → RunSummary(run_id, action, env, status, rc, artifact_dir, hosts=[HostResult(...)])
  → CLI prints summary; on success calls record_run() to update host_vars
```

### Hardening choices (codex r1 + W-R18)
- `project_dir=PROJECT_ROOT` + relative `playbook=` path → predictable resolution; no reliance on ansible-runner's default `private_data_dir/project`.
- `inventory=<absolute path>` → never depend on `ansible.cfg` default `inventory = inventory/prod` (which would otherwise target prod on a `--env dev` invocation).
- `suppress_env_files=True` → secrets / extravars never written to disk.
- `rotate_artifacts=10` → bounded retention window.
- `forks=20` explicit (Ansible default is 5; ansible.cfg has no `forks` setting).
- CLI requires `--env` (no default fallback).

## Data flow per subcommand

| Subcommand | Reads | Calls Ansible? | Writes | Records |
|---|---|---|---|---|
| `list` | `hosts.yml` + `host_vars/*.yml` | no | stdout (table/json) | — |
| `audit` | inventory | yes (`audit.yml`) | artifacts | — |
| `onboard` | `host_vars/<alias>.yml` (validates exists) | yes (`onboard.yml`) | artifacts | `record_run(set_status='active')` on success |
| `modify` | `host_vars/<alias>.yml` (validates exists) | yes (`modify.yml`) with `vps_changes` extravar | artifacts | `record_run()` |
| `remove` | inventory | yes only if `--cleanup-remote` (`remove.yml`) | drops alias from `hosts.yml` + deletes `host_vars/<alias>.yml` | — |

## Tests

22 tests live in `plugins/vps_runner/tests/test_vps_runner.py`:

- **Unit (12)**: `generate_run_id`, `inventory_path` error paths, `list_aliases`, `list_hosts`, host_vars read/write/delete roundtrip, `record_run`, `remove_alias_from_hosts`, `_collect_host_results` status classification, `_first_event_msg` extraction.
- **CLI dispatch (9)**: `list` table/json, `modify` empty-changes and unknown-alias guards, `remove --yes` guard, `remove` local-only happy path, `onboard` missing-alias, `modify` extravar assembly with mocked Runner, `onboard --first-time` connection override.
- **Integration (1, marker `integration`)**: `test_integration_run_playbook_against_unreachable` — drives `core.run_playbook` against a tmp inventory pointing at RFC 5737 `192.0.2.99` (TEST-NET-1, guaranteed unreachable). Verifies `Runner.stats` classification + artifact directory presence. ~11s, real ansible-runner invocation.

## Cross-references

- Plan + decision lock: [`docs/reviews/feat-vps-manager-v2/plan-2026-05-16.md`](../../reviews/feat-vps-manager-v2/plan-2026-05-16.md)
- Round changelogs: [`round2-2026-05-16.changelog.md`](../../reviews/feat-vps-manager-v2/round2-2026-05-16.changelog.md), [`round3-2026-05-16.changelog.md`](../../reviews/feat-vps-manager-v2/round3-2026-05-16.changelog.md), `round4-a-2026-05-16.changelog.md` (this round)
- Framework best-practice investigation: [`IVG-MULTI-SERVER-ANSIBLE-PRACTICE.md`](../investigations/IVG-MULTI-SERVER-ANSIBLE-PRACTICE.md)
- Governance gap analysis (drove workspace W-R18): [`IVG-REFLECT-BESTPRACTICE-GAP.md`](../investigations/IVG-REFLECT-BESTPRACTICE-GAP.md)
- Legacy plugin it replaces: [`vps-manager.md`](./vps-manager.md) (slated for removal in Round 4-b cutover)

## Open / Pending

- **Round 4-b cutover** (awaits user ack of feature parity): `git rm -r plugins/vps_manager/`; remove its Makefile / CI / docs entries; delete `runtime/state/vps_inventory.yml`.
- **3-host concurrency real test** (blocked on dev VPS SSH `Permission denied (publickey)`): once SSH access is restored, validate plan §1.4 — `audit` against 3 reachable nodes in < 2× single-node latency to confirm `forks=20` works as native parallelism.
- **`docker_host` / `deploy_compose` parity**: legacy `vps_manager` had these two actions; not yet ported. If still needed (vs. running a stand-alone docker compose role from another play), open new task.
