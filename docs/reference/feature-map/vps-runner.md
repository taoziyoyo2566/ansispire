# Feature: VPS Runner Plugin

## Status
✅ **Cutover complete 2026-05-16 (Round 4-b).** Pending: live 3-host concurrency verification (blocked on dev VPS SSH access).

The plugin was built to replace a prior anti-Ansible implementation (subprocess wrapping + custom callback + custom inventory state). See [`docs/reference/investigations/IVG-MULTI-SERVER-ANSIBLE-PRACTICE.md`](../investigations/IVG-MULTI-SERVER-ANSIBLE-PRACTICE.md) and [`IVG-REFLECT-BESTPRACTICE-GAP.md`](../investigations/IVG-REFLECT-BESTPRACTICE-GAP.md) for the framework best-practice analysis that drove the rewrite.

## Overview
`plugins/vps_runner/` is a thin Python CLI on top of [`ansible-runner`](https://ansible.readthedocs.io/projects/runner/) that drives standard Ansible playbooks against a standard inventory tree. No subprocess wrapping, no inbox state machine, no custom callback. Per-host structured results come from `Runner.stats` + `Runner.host_events()`; concurrency is the Ansible-native `forks` mechanism.

## Operational Entry Points

- Operator guide: [`docs/operations/vps-runner.md`](../../operations/vps-runner.md)
- Run unit tests (no SSH): `make test-vps-runner`
- Run integration test (real ansible-runner vs TEST-NET-1, ~11s): `make test-vps-runner-integration`
- Ansible syntax check on playbooks: `make vps-runner-syntax`
- CLI usage: `python -m plugins.vps_runner.cli {list|audit|onboard|modify|remove} --env {dev,stag,prod}` (假设 `.venv/bin/activate` 已 source；否则用 `.venv/bin/python -m plugins.vps_runner.cli ...`。完整说明见 [`operations/vps-runner.md §3`](../../operations/vps-runner.md#3-cli-子命令))

## Supported Actions

| Action | Remote | Scope |
|---|---:|---|
| `list` | no | Display managed hosts in the given env (alias / connection / status / last_action / updated_at). Pure local YAML read. |
| `add-host` | wizard 内置 first-time onboard | Create `host_vars/<alias>.yml` + add alias to `hosts.yml`. R11 wizard (no-arg) is the canonical first-time entry: 8 fields (alias / ip / bootstrap user / auth p\|k / password OR pasted PEM / sudo pw if non-root / bootstrap port / managed user / managed port) → inventory write → optional auto-onboard via ansible-runner `passwords=` dict (password branch) or temp key in `runtime/keys/vps_runner/<alias>.key` + post-onboard verify (key branch). Flag mode (R6) still scaffolds inventory only; template manual stays for hand-edits. Same-alias collision shows a 4-option menu (skip / new alias / verify / overwrite). |
| `audit` | yes | Per-host probe: ping, uptime, disk usage, memory, OS facts. Read-only and idempotent. |
| `onboard` | yes | Apply `onboard.yml` to one alias (**key-only**; R11 removed `--ask-pass`/`--ask-become-pass`). With `--first-time`, temporarily flips connection to `vps_runner.bootstrap_user@bootstrap_port`; auto-injects `ansible_ssh_private_key_file` from `vps_runner.bootstrap_key` if a wizard retry hint is recorded there. Standard re-onboard (no flag) uses the automation key chain. Idempotent re-onboard supported. **Docker install/config is deferred — see Open / Pending.** |
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
| `features:` | playbooks read directly | `base_packages`, `unattended_upgrades`, `system_limits`, `swap`, `network_tuning`, `ufw`, `fail2ban` |
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

### Post-onboard side effect (Round 7)

After `onboard` reports `successful`, the CLI also writes `~/.ssh/config.d/<alias>.conf` (operator-side per-alias SSH config rendered from `playbooks/templates/ssh_config_entry.j2`). The file uses `IdentityFile=~/.ssh/id_ed25519` (operator key) — **independent** from Ansible's automation key (`~/.ssh/ansispire_ed25519`, configured in `group_vars/vps_targets.yml::vps_runner_defaults.identity_file`). The two key paths are non-overlapping by design: Ansible never reads the operator key, the operator SSH config never references the automation key.

If `~/.ssh/config` has no `Include …config.d/…` line, the CLI prints a one-shot warning (does not modify the user's main config). Write failure is non-fatal — onboard's overall status is unchanged.

`remove` deletes `~/.ssh/config.d/<alias>.conf` regardless of `--cleanup-remote` (local SSH alias is meaningless without inventory).

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

124 tests live in `plugins/vps_runner/tests/test_vps_runner.py` (121 unit + 3 integration; R11 cumulative):

- **Core helpers + CLI dispatch**: list/audit/onboard/modify/remove paths, host_vars roundtrip, `record_run`, alias / hostname / ssh-user validators (R9), list_hosts chokepoint (R10), `_FakeStdin` wizard harness.
- **R11 wizard layer**: prompt_new_host 8-field happy paths (password / key branches), getpass mock for password, multi-line PEM collection, entry-check missing-keys reject, same-alias 4-option menu (× 4 outcomes including verify-fail→overwrite), wizard collision sub-flows, add_host overwrite, temp-key write/cleanup/normalize/reject, onboard `--first-time` auto-injects host_vars.vps_runner.bootstrap_key.
- **Integration (3, marker `integration`)**: ansible-runner driven against `192.0.2.99` (TEST-NET-1) — basic status classification, PATH bin injection (codex review P1.4), envvars allowlist canary (P1.3). ~33s real ansible-runner invocations.

## Cross-references

- Plans: [`plan-2026-05-16`](../../reviews/feat-vps-manager-v2/plan-2026-05-16.md), [`plan-2026-05-22`](../../reviews/feat-vps-manager-v2/plan-2026-05-22.md) (R7 add-host triple-entry), [`plan-2026-05-22b-wizard`](../../reviews/feat-vps-manager-v2/plan-2026-05-22b-wizard.md) (R11 wizard rewrite)
- Round changelogs: round2-7 + [`round8 (R8 F1+F3)`](../../reviews/feat-vps-manager-v2/round8-2026-05-22.changelog.md), [`round9 (R9 F2)`](../../reviews/feat-vps-manager-v2/round9-2026-05-22.changelog.md), [`round10 (R10 F4)`](../../reviews/feat-vps-manager-v2/round10-2026-05-22.changelog.md), [`round11 (wizard rewrite)`](../../reviews/feat-vps-manager-v2/round11-2026-05-22.changelog.md)
- Framework best-practice investigation: [`IVG-MULTI-SERVER-ANSIBLE-PRACTICE.md`](../investigations/IVG-MULTI-SERVER-ANSIBLE-PRACTICE.md)
- Governance gap analysis (drove workspace W-R18): [`IVG-REFLECT-BESTPRACTICE-GAP.md`](../investigations/IVG-REFLECT-BESTPRACTICE-GAP.md)

## Open / Pending

- **3-host concurrency real test** (blocked on dev VPS SSH `Permission denied (publickey)`): once SSH access is restored, validate plan §1.4 — `audit` against 3 reachable nodes in < 2× single-node latency to confirm `forks=20` works as native parallelism.
- **Docker install / config / deploy_compose parity**: the predecessor plugin had `docker_host` + `deploy_compose` actions; **not ported** in the cutover. If still needed, open a new task to add a `playbooks/docker.yml` (or invoke a stand-alone `community.docker` role). Until then, `features.docker` is intentionally absent from the schema; the `docker_daemon.json.j2` template was removed in Round 5 to match.
- **`runtime/state/vps_inventory.yml`** (legacy artifact): not git-tracked, no longer read or written, retained on disk for operator inspection. Remove locally when ready.
