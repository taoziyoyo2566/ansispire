# Changelog

All **user-visible** changes to Ansispire are documented here. The project does
not yet use semantic versioning; entries are grouped by branch / round of work.

The format is loosely adapted from [Keep a Changelog](https://keepachangelog.com).

## What counts as user-visible (when to add an entry)

A change qualifies as user-visible — and therefore requires an entry in
`[Unreleased]` in the same commit (`CLAUDE.md §0 Sync Guard #4`) — when it
touches any of:

- **CLI behavior** — Make targets, scripts users invoke, output format
- **Configuration defaults** — variables in `defaults/`, `group_vars/`, role-public knobs
- **Public interface** — role contracts, EDA rule schema, controller HTTP surfaces
- **Breaking refactor** — variable renames, removed aliases, path moves users may reference
- **Security policy** — firewall, RBAC, secrets handling, hardening defaults

Changes that do NOT trigger a CHANGELOG entry:

- Pure-internal refactors with no caller-visible effect
- Test additions / changes (covered by TSVS records)
- Documentation cleanup
- AI-collaborator instruction changes (`CLAUDE.md`, `GEMINI.md`)
- Per-round plan / changelog files under `docs/reviews/`

---

## [Unreleased]

### VPS Runner: add-host triple-entry + post-onboard SSH alias write (feat/vps-manager-v2 Round 7, 2026-05-22)

Closes 4 gaps in the v2 plugin without architectural changes (G1 orphan `ssh_config_entry.j2` template, G2 broken docs promise about `~/.ssh/config.d/`, G3 no interactive scaffold, G4 no hand-write template).

- **CLI `add-host` — three input modes**: ① wizard (no args) prompts for 4 essential fields (alias / IP / managed_port [1156] / managed_user [ansible]) then optionally chains into `onboard --first-time --ask-pass --ask-become-pass`; ② flag mode (`ALIAS=x IP=y`) unchanged from R6; ③ template-manual via new `plugins/vps_runner/examples/host_vars.yml.template` (slim, 4 user-fillable fields). Wizard refuses non-TTY stdin with rc=2 + flag-mode hint; aborts gracefully on Ctrl-C / EOF with rc=130.
- **CLI `onboard` — post-success side effect**: after `onboard` reports `successful`, the CLI renders `playbooks/templates/ssh_config_entry.j2` to `~/.ssh/config.d/<alias>.conf` (chmod 0600, dir created with 0700 if missing) using `IdentityFile=~/.ssh/id_ed25519` (operator key). Independent from Ansible's automation key (`~/.ssh/ansispire_ed25519`, configured in `group_vars/vps_targets.yml::vps_runner_defaults.identity_file`). If `~/.ssh/config` lacks `Include …config.d/…`, prints a one-shot warning with the exact line to add (does not modify the user's main config). Write failure is non-fatal — onboard's overall status is unchanged.
- **CLI `remove`**: always deletes `~/.ssh/config.d/<alias>.conf` (regardless of `--cleanup-remote`) after dropping host_vars. Local SSH alias is meaningless without inventory; clean both together.
- **Makefile `vps-add-host`**: no-arg invocation now enters wizard mode; partial-flag mode (only `ALIAS=` or only `IP=`) is rejected with usage hint.
- **Docs**: `docs/operations/vps-runner.md §3.1b` rewritten to cover the three input modes with the two-key separation table. Step 7 of §4 updated to reflect per-alias config files (was `ansispire.conf` single-file, never implemented on v2).

### Multi-OS target fleet — RHEL family support (TASK-007 round 1, 2026-05-19)

First-class data-plane support for managed VPS across two OS families: Debian (Debian 13 + Ubuntu 24.04) and RHEL (Rocky Linux 9 + AlmaLinux 9). Closes the placeholder fail-stub that `infra_baseline` carried for RHEL since the role's inception. Alpine remains a placeholder for follow-up TASK-007.B.

- **Role**: `roles/infra_baseline/tasks/redhat.yml` (new) — dnf-based Docker CE install via vendor `.repo`; SELinux `container_manage_cgroup` boolean flip (enforcing OR permissive); `python3.11` install + interpreter pivot to satisfy `infra_baseline_python_min_version: 3.10` (RHEL 9 ships 3.9 by default); `--check` mode safety via stat probe + `meta: end_host` for fresh-host preview.
- **Role**: `roles/infra_baseline/tasks/main.yml` (refactored) — Python version assert moved from position 1 to after per-family blocks; Docker service start relocated from family-agnostic into the Debian `block:` (RHEL handles its own via `redhat.yml`); RHEL fail-stub replaced with `include_tasks: redhat.yml`; user creation parameterized to use OS-appropriate admin group (`sudo` on Debian, `wheel` on RHEL via `vars/RedHat.yml`).
- **CLI**: `make target-deploy TARGET_NODE=debian|rhel|all|<alias>` + `target-deploy-check` (`--check --diff`) + `target-ping` (read-only connectivity probe). `ANSIBLE_USER=root` env-var override for fresh-host bootstrap (before role creates the `ansible` user).
- **Inventory**: `inventory/hosts.ini` + `inventory/prod/hosts.ini` now have populated `[targets_debian]` (`d13`, `u24`) and `[targets_rhel]` (`rocky9`, `alma9`) with `[targets:vars]` common SSH/Python settings. Steady-state inventory uses `ansible_user=ansible`; fresh-host onboarding uses the Makefile knob.
- **Playbooks**: `playbooks/deploy_target.yml` (new) applies `infra_baseline` to `hosts: targets` only — no hub roles. `playbooks/ping_targets.yml` (new) supports the Semaphore "Ping all targets" Job Template registered in `controller/semaphore/bootstrap.yml`.
- **Verified**: all 4 VPS baselined cleanly with idempotent re-runs (`ok=20–21 changed=0` on RHEL, `ok=13 changed=0` on Debian).

### Hub role: rsync preflight UX (2026-05-19, Round 7)

Branch `fix/codex-cross-compare-hygiene`. Engineering improvement (not a correctness fix) for the `ansispire_hub` role.

- **Preflight added** (`roles/ansispire_hub/tasks/main.yml`): 4 tasks inserted between "Ensure state directory" and "Hub | Sync Code" — `rsync --version` probes on both the Ansible controller (`delegate_to: localhost`) and the target host, each gated by an `assert` task with an install-hint `fail_msg`. Replaces `ansible.posix.synchronize`'s opaque failure modes (`rsync error code 12` on remote, generic "command not found" on controller) with an actionable message before any mutating step. Probe uses `command: rsync --version` rather than path-stat so macOS Homebrew, Alpine, and Debian all work without hard-coded paths.

### Cross-pollination from fix/ansible-docs-review-remediation (2026-05-19, Round 8)

Branch `fix/codex-cross-compare-hygiene`. Codex's second-pass review against the Round 6 HEAD surfaced 4 new defects; each was independently reproduced before acceptance (per W-R13). Two of the defects are runtime correctness issues (data loss + tag-name conflation), two are documentation accuracy:

- **Reactor v2.5 → v2.6** (`controller/audit/reactor.py`):
  - **Cursor=0 disambiguation** (data-loss fix). `load_cursor()` now returns `Optional[int]`: `None` for absent / disabled cursor (fresh boot → seek EOF); `int` (including 0) for present-and-authoritative (offset 0 → seek to start, the post-truncate marker case). Previous v2.5 collapsed both into `seek(EOF)`, so a reactor crash immediately after `save_cursor(0)` would silently drop the entire post-rotate file on next boot — defeating the truncation fix itself.
  - **Non-dict rule isolation**. `process_event` now guards with `isinstance(rule, dict)` at the head of the per-rule loop. Previous v2.5 except-block called `rule.get(...)` on whatever object `match_rule` rejected, re-raising AttributeError on non-dict rule entries and killing the tail loop.
- **AUDIT_IMAGE_TAG semantic split**:
  - **New env var `AUDIT_PYTHON_BASE_TAG`**: the upstream `python:VERSION` tag for non-baked containers (audit-relay + the e2e stack's three python services). Default `3.12-alpine`.
  - **`AUDIT_IMAGE_TAG`** retains its original role: the tag for our OWN baked images (`ansispire/audit-sink`, `ansispire/audit-reactor`). Default unchanged.
  - Previous behaviour conflated the two: setting `AUDIT_IMAGE_TAG=v0.1.0` (intending to tag our images) silently resolved relay to the nonexistent `python:v0.1.0`. Affected `controller/audit/docker-compose.yml:56` (main relay) + `controller/audit/e2e/compose.e2e.yml` (three services). Propagated through `config/manifest.yml` (new `audit_baked` key), `playbooks/manifest_sync.yml` (writes both vars), `.env.example` × 2, and `scripts/loopback_test_runner.sh`.
- **Round 6 changelog retraction**. The Round 6 verification record claimed "No regressions" and described Codex's tag pattern as "Not adopted"; both statements were over-broad. The Round 6 changelog now carries an in-place Retraction section pointing at Round 8.

### Cross-pollination from fix/ansible-docs-review-remediation (2026-05-19, Round 6)

Branch `fix/codex-cross-compare-hygiene`. Engineering-bug remediation after diff'ing this branch against parallel branch `fix/ansible-docs-review-remediation`, which surfaced 6 real defects in the WU-2 / WU-3 work units shipped in Rounds 3-4.

- **Reactor v2.4 → v2.5** (`controller/audit/reactor.py`):
  - **Truncation handling: seek(0), not seek(EOF)** (data-loss fix). Both at startup (`cursor > file_size` at boot) and during run (per-tick `f.tell() > size` check), the reactor now seeks to the start of the post-rotate file. Previous behaviour silently dropped every event written between the truncation point and the next reactor restart, defeating cursor persistence's whole purpose.
  - **Per-rule exception isolation**: `match_rule` is wrapped in try/except inside `process_event`. A malformed rule logs and is skipped rather than crashing the tail loop.
  - **Defense-in-depth `_contains` coercion**: `if str(value) not in actual_val` so a numeric `_contains` value in hand-edited `rules.json` (bypassing `make test-rules-schema`) cannot raise TypeError.
- **Reactor healthcheck** (`controller/audit/docker-compose.yml`): replaced `pgrep -f reactor.py` (self-matches its own grep argv on some implementations → false-healthy) with `tr '\0' ' ' </proc/1/cmdline | grep -q '/app/reactor.py'`. Bulletproof since reactor runs as PID 1.
- **Hub role admin-password idempotency** (`roles/ansispire_hub/tasks/main.yml`): added an `API | Probe admin password` task that calls `/api/auth/login`; the subsequent `CLI | Enforce admin password` runs only when the probe is rejected (status ∉ {200, 204}). Previous version reported `changed=1` on every deploy regardless of whether the password actually changed — Ansible idempotency violation.
- **Audit role build: always + dropped admin password env** (`roles/ansispire_audit/tasks/main.yml`): added `build: always` so re-deploys after editing `reactor.py`/`sink.py` actually rebuild the baked image (module default `policy` only builds if missing). Removed `SEMAPHORE_ADMIN_PASSWORD` from the env block — the audit stack authenticates via Bearer token, the admin password was unused secret exposure.
- **Rules schema tightened** (`extensions/eda/rules.schema.json`):
  - `_contains` keys are constrained to string values via `patternProperties`. Numbers/booleans no longer pass schema; reactor's `str()` coercion is the defense-in-depth net for hand edits.
  - `semaphore_api` actions now require BOTH a project identifier (id|name) AND a template identifier (id|name) via `allOf` + `anyOf`. Reactor's POST `/api/project/{id}/tasks` payload mandates both — the previous schema let through actions that would fail at runtime.

### Semaphore API contract preflight (2026-05-19)

Branch `fix/codex-cross-compare-hygiene`. WU-4 from `docs/reviews/feat-semaphore-cross-compare/plan-2026-05-17.md`.

- **New playbook `controller/semaphore/bootstrap_preflight.yml`** — schema-mode (default) + full-mode API contract probe. Imported at the top of `bootstrap.yml` so every bootstrap run fails fast on upstream Semaphore schema drift before mutating state. Skip per-run with `-e skip_preflight=true`.
  - Schema mode (~2 s): verifies `POST /api/auth/login` sets a session cookie; `GET /api/projects` and `GET /api/users` return arrays with `id` + `name` / `username` fields.
  - Full mode (~30–60 s): also creates a throwaway `__preflight__` project, walks all 5 project-scoped GETs (`keys` / `repositories` / `inventory` / `environment` / `templates`), mints a throwaway API token via `POST /api/user/tokens`, deletes the throwaway project on exit.
- **New harness `controller/semaphore/preflight/`** — disposable `compose.yml` (bare Semaphore, isolated host port `3301`) + `run.sh` (clean → up → wait healthy → preflight `mode=full` → teardown).
- **Make target `test-api-contract`** — wraps `controller/semaphore/preflight/run.sh`. Override the image tag via `SEMAPHORE_IMAGE_TAG=...`. Not part of `make verify` (needs Docker daemon).
- **CI matrix `api-contract`** — runs full preflight against both the manifest-pinned tag (gating) and `latest` (`continue-on-error: true` — surfaces upstream drift as a warning, not a merge block).
- **Governance**: `docs/governance/testing-governance.md` §3 decision tree gains rows for `bootstrap.yml` / `bootstrap_preflight.yml` / `config/manifest.yml` Semaphore tag bumps. §4.1 catalogues `make test-api-contract`. §4.2 documents the new CI dependency.

### Audit-plane engineering robustness (2026-05-18)

Branch `fix/codex-cross-compare-hygiene`. WU-2 from `docs/reviews/feat-semaphore-cross-compare/plan-2026-05-17.md`.

- **Reactor v2.3 → v2.4** (`controller/audit/reactor.py`):
  - **Cursor persistence**: byte-offset into `events.jsonl` flushed to `CURSOR_FILE` every `CURSOR_FLUSH_INTERVAL` s (default `5s`). Cold-start resumes from last cursor; missing/oversized cursor falls back to EOF (with explicit log). New compose volume `audit-reactor-state:/var/lib/audit-reactor`.
  - **Rules mtime cache**: `load_rules` only re-reads when (a) `RULES_PATH` mtime changed AND (b) `RULES_MIN_RELOAD_INTERVAL` (default `30s`) elapsed. Per-tick poll cost drops from "open+parse+json.loads" to a cached stat.
  - **Outer-loop restart**: fatal exception path no longer recurses into `main()`; uses a flat `while True` wrapper with `FATAL_RESTART_BACKOFF` s sleep. Avoids growing call stack across long-running deployments.
  - 4 new envs exposed: `CURSOR_FILE` / `CURSOR_FLUSH_INTERVAL` / `RULES_MIN_RELOAD_INTERVAL` / `FATAL_RESTART_BACKOFF` (all with safe defaults).
- **Audit container images** (`controller/audit/Dockerfile.{sink,reactor}` new; `docker-compose.yml` updated):
  - `audit-sink` and `audit-reactor` now build locally (`ansispire/audit-{sink,reactor}:${AUDIT_IMAGE_TAG}`); `logrotate` baked into the sink image, `jq` + `procps` baked into the reactor image. Eliminates runtime `apk add` from container `command:`.
  - Healthchecks added for `audit-relay` (`pidof python3`) and `audit-reactor` (`pgrep -f reactor.py`).
- **Hub admin password rotation** (`roles/ansispire_hub/tasks/main.yml`): `semaphore user change-by-login` now runs on **every** deploy, not just the first-deploy token mint. Rotating `vault_semaphore_admin_password` in vault.yml and re-deploying now actually lands the new password.
- **CLI behavior**: `make test-rules-schema` was already in `make test-eda` (from WU-3); reactor v2.4 introduces no new Make targets but extends `make test-eda` coverage transparently via existing component tests.
- **Bootstrap workspace branch**: `controller/semaphore/bootstrap.yml` `git_branch` is now overridable (`semaphore_workspace_git_branch`); defaults to `dev` to match the dev-trunk model. Previously hard-pinned to `master`, which was wrong during the dev-trunk phase.
- **Documentation**:
  - `controller/semaphore/README.md` updated for SQLite default + port 3300 + manifest SSOT + Path A vs Path B password rotation guidance.
  - `docs/reference/feature-map/{audit-plane,eda-core,hub-deployment}.md` updated to reflect v2.4 reactor semantics + new Dockerfiles + admin password enforcement.

### Semaphore cross-compare hygiene + OSS key absorption (2026-05-17 → 2026-05-18)

Branch `fix/codex-cross-compare-hygiene`. Bundles WU-1 (hygiene fixes) + WU-3 (OSS key absorption + schema gate + governance doc) from `docs/reviews/feat-semaphore-cross-compare/plan-2026-05-17.md`.

- **Configuration defaults**:
  - `SEMAPHORE_DB_PATH` removed from `controller/semaphore/docker-compose.yml` — the upstream wrapper treats it as a *directory* and appends `database.sqlite`; pinning it to a file path silently turned the leaf into a directory.
  - `SEMAPHORE_ACCESS_KEY_ENCRYPTION` / `SEMAPHORE_COOKIE_HASH` / `SEMAPHORE_COOKIE_ENCRYPTION` added to compose `environment:` with empty `${VAR:-}` defaults; `.env.example` documents how to generate (`head -c32 /dev/urandom | base64`). Empty = ephemeral keys at restart (safe for first-run discovery; production needs them persisted).
- **Security policy (Path A)**: `roles/ansispire_hub` now mints `state/.security_keys` once on first deploy, persists across redeploys, and renders the three envs into `.env`. Deleting `.security_keys` invalidates every stored Semaphore AccessKey and every active session — restore from backup, do not re-mint.
- **Public interface — EDA rule contract**: new `extensions/eda/rules.schema.json` (JSON Schema Draft-07) covers rule structure (name / cooldown / enabled / condition / actions); validation gated by `make test-rules-schema`, wired into `make test-eda`.
- **CLI behavior**: `make test-rules-schema` added (inline `jsonschema.validate`; no new script files); included by default in `make test-eda` chain.
- **Hygiene fixes (WU-1)**:
  - `controller/audit/reactor.py` `webhook` action implemented (was `pass` no-op); POSTs `{rule_action, event}` JSON to `action.url`.
  - `roles/ansispire_hub/tasks/main.yml` first-deploy token path now sets `ansispire_hub_eda_token` fact directly from the mint response (previously fell through to a stat-gated slurp that ran before the file existed).
  - `roles/ansispire_hub/tasks/main.yml` rsync excludes extended with `runtime/` (vps_manager workstation-local artefacts must never leak to the hub).
- **Documentation**:
  - `docs/governance/iac-vs-ui-boundary.md` (new) — authoritative ownership map for every Semaphore resource type (project / user / inventory / repo / env / key / template / token / future runner) plus hybrid resource patterns and a decision flowchart.
  - `docs/reference/feature-map/{eda-core,hub-deployment,INDEX}.md` updated to reflect rules schema + security keys lifecycle + IaC/UI boundary link.
  - `docs/reference/investigations/IVG-EDA-RULEBOOK-MIGRATION.md` (new, WU-5a) — recommend deferring `ansible-rulebook` adoption; 4 trigger conditions recorded.
  - `docs/reference/investigations/IVG-EXECUTION-PLANE-RUNNER.md` (new, WU-5b) — recommend deferring OSS Runner abstraction; 5 trigger conditions + 6-Gate landing path drafted; strong coupling to ACCESS_KEY_ENCRYPTION called out.
- **Dependency**: `jsonschema>=4.0` pinned in `requirements.txt` (was transitively present via molecule plugins; now explicit because the EDA schema gate consumes it directly).

### VPS Runner — `add-host` cutover-regression fix + daily-ops Makefile wrappers (2026-05-17, round 6)

Closes the lifecycle UX gap that plan-2026-05-16 §1.2 omitted (only ported 5 of legacy vps-manager's 8 subcommands; round 4-b removed the 3 lifecycle Make wrappers without porting). Plan: [`plan-2026-05-17b.md`](docs/reviews/feat-vps-manager-v2/plan-2026-05-17b.md). Closeout: [`round6-2026-05-17.changelog.md`](docs/reviews/feat-vps-manager-v2/round6-2026-05-17.changelog.md).

- **New CLI subcommand `add-host`**: `vps-runner add-host <alias> --ip <ip> [--port 1156 --user ansible --status pending --env dev]`. Creates `host_vars/<alias>.yml` (slim format; shared defaults inherited from group_vars) AND adds the alias to `hosts.yml` under `vps_targets:`. Validates alias uniqueness (against both hosts.yml AND host_vars file existence — covers orphan edge), port in [1024, 65535] excluding 22 (mirrors onboard.yml `pre_tasks` assert exactly), non-empty alias/ip. Pure local YAML write; no Ansible call.
- **Core helpers**: `add_alias_to_hosts(env, alias)` mirrors existing `remove_alias_from_hosts`; `add_host(env, alias, **kw)` is the public façade. Both consistent with the file's read-modify-write-via-PyYAML pattern (PyYAML lossiness on `hosts.yml` already present in `remove_alias_from_hosts`; deferred to a future `ruamel.yaml` cleanup TASK).
- **6 new Makefile daily-ops wrappers**: `vps-list`, `vps-audit` (ALIAS optional), `vps-add-host`, `vps-onboard`, `vps-modify` (ARGS slot for raw flags), `vps-remove`. All accept `ENV=dev` default. **Critical knob naming**: `MANAGED_PORT` / `MANAGED_USER` (not `PORT` / `USER`) to avoid collision with Make-inherited shell `$USER` — caught at Gate 3 of iteration 1 when canary `make vps-add-host` produced spurious `--user netcup`.
- **Tests**: +12 unit cases for `add_host` (creates file, hosts.yml update, duplicate alias refusal, orphan-alias refusal, port=22 refusal, parameterized out-of-range port refusal, empty input refusal, CLI dispatch end-to-end, CLI rc=2 on duplicate). Total now 33 unit + 3 integration.
- **Docs**: `docs/operations/vps-runner.md` §3 入口 callout now lists all 6 Make wrappers; new §3.1b `add-host` subsection with typical 3-step flow (`vps-add-host` → `vps-onboard` → `vps-audit`). `docs/reference/feature-map/vps-runner.md` Actions table adds `add-host` row. `inventory/vps_runner/dev/hosts.yml` comment header line updated to point at the correct entry command.
- **Operator UX delta**: adding a new managed VPS now takes 3 short commands instead of "manually write YAML + edit hosts.yml + onboard". Surfaces the typical workflow as `make vps-add-host ALIAS=<new> IP=<ip>` → `make vps-onboard ALIAS=<new>` → `make vps-audit ALIAS=<new>`.

### VPS Runner — best-practice review hardening (2026-05-17, round 5)

Driven by the post-cutover [`ansible-best-practices-review-2026-05-16.md`](docs/reviews/feat-vps-manager-v2/ansible-best-practices-review-2026-05-16.md) (4 P1 + 2 P2 actionable findings). Plan: [`plan-2026-05-17.md`](docs/reviews/feat-vps-manager-v2/plan-2026-05-17.md). Closeout: [`round5-2026-05-17.changelog.md`](docs/reviews/feat-vps-manager-v2/round5-2026-05-17.changelog.md).

- **P1.1 SSH reversibility + handler model**: 8x inline `systemd state=reloaded/restarted` in `plugins/vps_runner/playbooks/onboard.yml` replaced with `notify:` → 3 named handlers (`Reload sshd` / `Reload systemd manager` / `Restart sshd.socket`) + `meta: flush_handlers` after each `sshd -t` validation. Comment marker for `/etc/ssh/sshd_config` directives changed from `# <dir> managed by ...` (value-loss; non-reversible) to `# ANSISPIRE-COMMENTED: <dir> <value>` (value-preserving, reversible). `plugins/vps_runner/playbooks/remove.yml` now (a) notifies sshd reload on drop-in removal — closes a parallel silent bug, (b) runs the reverse `replace` to restore commented directives when `--cleanup-remote` is passed, (c) has its own `handlers:` block.
- **P1.2 Docker scope clarified**: `features.docker: true` removed from 4 host_vars + `docs/operations/vps-runner.md` + `docs/reference/feature-map/vps-runner.md`; unused `plugins/vps_runner/playbooks/templates/docker_daemon.json.j2` deleted. Future Docker integration tracked as a follow-up TASK (changelog §6).
- **P1.3 Artifact env scrubbing**: `plugins/vps_runner/vps_runner.py` adds `_build_runner_envvars()` allowlist (PATH/ANSIBLE_CONFIG/ANSIBLE_COLLECTIONS_PATH/ANSIBLE_ROLES_PATH + 5-key locale allowlist) + `_scrubbed_environ()` ctx mgr replacing `os.environ` for the `ansible_runner.run()` call. The artifact `command` file no longer leaks ambient process env (e.g. caller-side API keys).
- **P1.4 Direct CLI self-sufficient**: PATH built from `Path(sys.prefix) / "bin"` so `python -m plugins.vps_runner.cli` works without Makefile wrapping. Documented invocations now match reality.
- **P2 inventory dedup**: new `inventory/vps_runner/dev/group_vars/vps_targets.yml` holds `security:` / `features:` / `vps_runner_defaults:` shared blocks; 4 host_vars slimmed to per-host overrides only (`ansible_host`, `ansible_port`, `ansible_user`, `vps_runner.{managed_port,managed_user,status,os}`). onboard.yml's `vr = vps_runner_defaults | combine(vps_runner)` pattern documented.
- **P2 native SSH validation**: 2x `delegate_to: localhost ssh -o StrictHostKeyChecking=no` validation tasks replaced with `meta: reset_connection` + `wait_for_connection` + `command` using per-task `vars:` for new connection params. Respects inventory `ansible_ssh_common_args`/ProxyJump; doesn't require local OpenSSH CLI.
- **Tests**: +2 regression-guard integration tests (`test_integration_run_playbook_without_path` for P1.4, `test_integration_envvars_artifact_excludes_unwhitelisted` for P1.3); total now 21 unit + 3 integration.
- **Deferred** (follow-up TASKs, not this round): onboard.yml role decomposition (P2 explicit suggestion), `docker_host`/`deploy_compose` parity, 3-host concurrency live test (still SSH-blocked).

### VPS Manager → VPS Runner cutover (2026-05-16, round 4-b) ⚠ BREAKING

**Removed**: `plugins/vps_manager/` (33 files), `docs/operations/vps-manager.md`, `docs/reference/feature-map/vps-manager.md`, and all related Makefile targets (`test-vps-manager`, `vps-manager-syntax`, `vps-new`, `vps-recover`, `vps-submit`, `vps-tasks`, `vps-manager-init`, `vps-manager-process`, `vps-manager-validate`).

**Migration**: All `vps_manager` use cases are covered by `plugins/vps_runner/` (see below — list / audit / onboard / modify / remove). Operators who relied on the YAML inbox flow should switch to `python -m plugins.vps_runner.cli` directly. Existing `host_vars/<alias>.yml` files in `inventory/vps_runner/<env>/` retain all per-host state; `runtime/state/vps_inventory.yml` (legacy custom SSOT) is **no longer read or written** — it remains on disk untouched (was never git-tracked) for operator inspection or removal at will.

**Why the cutover landed without live 3-host concurrency verification**: dev VPS SSH (`deploy@82.152.164.147 Permission denied (publickey)`) blocked real-node parity testing. User explicitly accepted "22 tests + ansible-runner integration + ansible-lint production = sufficient parity evidence" trade-off, with the understanding that live verification will land as TASK-007 / TASK-010 progress.

### VPS Runner plugin — ansible-runner native rewrite (2026-05-16, rounds 2–4-a)

Driven by W-R18 framework best-practice pre-check ([`IVG-MULTI-SERVER-ANSIBLE-PRACTICE`](docs/reference/investigations/IVG-MULTI-SERVER-ANSIBLE-PRACTICE.md), [`IVG-REFLECT-BESTPRACTICE-GAP`](docs/reference/investigations/IVG-REFLECT-BESTPRACTICE-GAP.md)) that identified the **then-legacy** `plugins/vps_manager/`'s three-layer anti-Ansible pattern (subprocess wrapping + custom callback + custom inventory state).

- **New plugin**: `plugins/vps_runner/` invokes Ansible via `ansible_runner.run()` against a standard inventory tree (`inventory/vps_runner/<env>/hosts.yml` + `host_vars/<alias>.yml`). No inbox, no custom state file, no callback plugin.
- **CLI subcommands**: `python -m plugins.vps_runner.cli {list|audit|onboard|modify|remove} --env {dev,stag,prod}`. `onboard` supports `--first-time` + `--ask-pass` + `--ask-become-pass` for bootstrap from `root@22`-style initial state; `modify` accepts CSV `--add-package` / `--remove-package` / `--add-port` / `--remove-port` plus `--toggle-fail2ban on|off`; `remove` requires `--yes` and has opt-in `--cleanup-remote` for stripping Ansispire sshd drop-ins.
- **Hardening** (per `ansible-runner` codex review): `inventory=<abs path>` (no reliance on `ansible.cfg` default `inventory = inventory/prod`), `suppress_env_files=True` (secrets not on disk), `rotate_artifacts=10`, explicit `forks=20`.
- **Artifacts**: every invocation writes to `runtime/logs/vps_runner/<run_id>/` with structured per-host events.
- **Operator UX**: new Make targets `test-vps-runner`, `test-vps-runner-integration`, `vps-runner-syntax`; `make verify` includes `test-vps-runner` alongside the existing legacy test target.
- **Documentation**: operator guide `docs/operations/vps-runner.md`; per-module spec `docs/reference/feature-map/vps-runner.md`; INDEX, ARCHITECTURE, README updated to register both plugins (legacy clearly marked).
- **Tests**: 22 cases (21 unit + 1 ansible-runner integration vs RFC 5737 TEST-NET-1).

### VPS Manager plugin MVP (2026-05-14) — REMOVED in Round 4-b above

- **New plugin**: `plugins/vps_manager/` processes one-shot VPS task YAML from
  `runtime/inbox/vps/pending/`, moves tasks through
  `processing → done|failed`, redacts archives, and maintains
  `runtime/state/vps_inventory.yml`.
- **Actions**: `onboard`, `modify`, `audit`, `remove`, `docker_host`, and
  `deploy_compose` ship with playbooks, examples, templates, and schema
  documentation.
- **Security defaults**: managed SSH port must be non-22, inline passwords and
  inline private key material are rejected, duplicate active `onboard` is
  refused, automation keys are separated from personal operator keys, and
  non-public Compose exposure must bind `127.0.0.1`; missing bootstrap
  password env vars can be supplied through an interactive hidden prompt
  without persisting the secret.
- **Onboarding hardening**: Ubuntu 24.04 `ssh.socket` activation is handled
  explicitly by staging the bootstrap and managed ports together, validating
  the managed login, then locking down to the managed port only. SSH hardening
  is installed as `00-ansispire.conf` so it wins over provider/cloud-init
  drop-ins that enable root or password auth.
- **Defaults**: newly generated onboarding tasks now default the managed user
  to `ansible` when the operator leaves the prompt or `--managed-user` unset.
- **Operator UX**: new Make targets `vps-new`, `vps-submit`, `vps-tasks`,
  `vps-manager-init`, `vps-manager-process`, `vps-manager-validate`,
  `vps-manager-syntax`, and `test-vps-manager`; `make verify` now includes
  the VPS Manager L1 lifecycle tests and native Ansible syntax checks.

### Testing governance §9 + feature-map sync (2026-05-13)

Closure pass tied to the PR-readiness audit. Per-round detail under
[`docs/reviews/audit-pr-readiness/`](docs/reviews/audit-pr-readiness/).

- **Test hygiene** (`docs/governance/testing-governance.md` §9): codifies
  clean-before-test discipline that was implicit until now —
  when L4/L5 tests must clean (failed previous run, cross-branch
  retest, leave-running e2e stack), when they must NOT (L0–L3,
  intra-iteration `molecule converge`), and a dev-stack-vs-test-stack
  isolation contract so cleanup commands don't accidentally take down
  the long-running dev stack.
- **Functional Index** (`docs/reference/feature-map/INDEX.md`):
  aggregate inventory of roles · playbooks · controller modules ·
  EDA rules · inventory taxonomy · SSOT layer · Make UX · capability
  boundaries; intended as the lazy-loaded entry point for future
  sessions instead of re-deriving the inventory each time.
- **Sync Guard #5** (`CLAUDE.md` §0): mandates `INDEX.md` updates
  whenever `roles/` · `playbooks/` · `controller/` · `extensions/eda/`
  · `inventory/` · `Makefile` · `config/manifest.yml` change.
- **feature-map per-feature refresh**: `audit-plane.md` (R5/R6
  hardening notes), `test-infra.md` (testing governance + TSVS
  registry + §9), `eda-remediation.md` (current rule set: Disk Full
  enabled / DB Failure placeholder / nginx restart unrouted),
  `eda-core.md` (round 5/6 + testing-strategy + tier-c history).

### Test infrastructure & security hardening (rounds 5–6, 2026-05-10)

User-visible changes from a Molecule deep-loop testing round (round 5, executed
by external agent Gemini) and the follow-up corrections (round 6). Per-round
detail under [`docs/reviews/feat-eda-advanced-healing/round{5,6}-2026-05-10.changelog.md`](docs/reviews/feat-eda-advanced-healing/).

- **Security**: `common` role now explicitly allows loopback traffic
  (`ufw allow in on lo`) when UFW is enabled — without this, internal
  service health checks (nginx self-probe, MySQL socket connections)
  silently fail with "Connection refused" on hardened hosts.
- **Templates**: `ansible_managed` is now wrapped with the `comment` filter
  in `nginx.conf.j2`, `vhost.conf.j2`, `my.cnf.j2`, and `backup.sh.j2`.
  Previously the bare string was emitted into config bodies and parsed as
  an unknown directive (notably nginx refused to start).
- **Database**: MySQL root-password setting is now safely re-runnable —
  added `check_implicit_admin: true` plus explicit `login_user`/`login_password`
  to handle the empty-password vs configured-password race on second runs.
- **Breaking (internal-only)**: dropped the `nginx_vhosts` legacy alias.
  All internal call sites (defaults, group_vars, molecule, role tasks,
  role README) now use the canonical `webserver__vhosts`. The
  `roles/webserver/tasks/preflight.yml` `default(...)` fallback chain has
  been removed. No production inventory used the legacy name.
- **Removed**: `scripts/verify_report.py` and the regenerated root-level
  `ANSISPIRE_TEST_REPORT.md` snapshot. The script duplicated lint+syntax
  work already done by the `verify` target, hardcoded `✅ PASS` rows for
  steps it never actually measured, and resurrected a snapshot file the
  prior docs round had explicitly removed. `make verify-full`'s exit code
  is now the report.
- **Docs**: `docs/operations/environments.md` gains a Molecule section
  with five gotchas (UFW loopback, `ansible_managed` filter, MySQL auth,
  vhost variable naming, plugin-path env vars).

### Documentation refactor (P1–P6, 2026-05-10)

- **README.md** rewritten as a concise (~80-line) product entry page; no
  more hardcoded version pins in narrative; sections trimmed to:
  positioning · capabilities · prerequisites · quickstart · document map · governance
- **SUMMARY.md → ARCHITECTURE.md** (rename + slim to architecture-only content)
- **`docs/` restructured by audience**:
  - `docs/user-guide/` — long-form guides with rationale (installation,
    quickstart-eda)
  - `docs/operations/` — terse maintainer command references
  - `docs/reference/` — feature maps, test specs, investigations
  - `docs/governance/` — contribution rules, AI workflow, testing governance,
    operational truths, vendor patches
- **Deleted** broken `docs/GETTING_STARTED.md` (referenced removed inventory paths)
- **Consolidated** `docs/env-{dev,stag,prod}.md` → `docs/operations/environments.md`
- **Migrated** former `SUMMARY.md` §4 lessons → `docs/governance/operational-truths.md`
- **Migrated** former `SUMMARY.md` §5 vendor patches → `docs/governance/vendor-patches.md`
- **Archived** 38 retired-format review files under `docs/reviews/_archive/`
- **Added** `LICENSE` (Apache-2.0), `SECURITY.md`, `CHANGELOG.md`, `docs/README.md` (nav)
- **Removed** outdated root-level `ANSISPIRE_STABILITY_REPORT.md` and
  `ANSISPIRE_TEST_REPORT.md` (snapshot-only reports superseded by feature maps)

### Testing governance docs (rounds 1–2 of feat-testing-strategy, 2026-05-11)

Establishes the project's testing **strategy** + **plan** as load-bearing
governance. Both files live under `docs/governance/`. Per-round detail under
[`docs/reviews/feat-testing-strategy/`](docs/reviews/feat-testing-strategy/).

**Round 1 (2026-05-11)** — two governance docs land:

- **`testing-governance.md`** (was a 20-line stub; now 8 sections):
  test pyramid (L0–L5) with current carriers · path-based decision tree
  (16 rows mapping change → required tests) · local-vs-CI responsibility
  split · 4-level quality gates · Molecule operating modes (test / converge
  / verify / login) · TSVS mandate · doc self-maintenance triggers.
- **`test-plan.md`** (new): surface inventory (12 surfaces) · coverage
  matrix (13 quality properties × 6 layers) · per-surface assertion
  lists for every `molecule/*/verify.yml` · 9 known gaps (G1–G9) with
  risk ratings and assigned ownership · new-code acceptance criteria.
- **Round 1 scope**: doc-only. No Make / CI / test-code changes. Targets
  cited by the new docs (`make verify-quick`, `make verify`, `make
  verify-full`, `make test-eda*`, `make controller-*-smoke`) are all
  pre-existing; the docs codify their semantics.

**Round 2 (2026-05-11)** — TSVS discoverability:

- **`docs/reference/test-specs/INDEX.md`** (new): registry for all 10 TSVS
  (4 new Molecule + 6 pre-existing EDA / audit / RBAC), Active/Retired
  status machine, surface coverage map, naming convention, maintenance flow.
- **4 new Molecule TSVS**: `molecule-common.md`, `molecule-webserver.md`,
  `molecule-database.md`, `molecule-full-stack.md` — each enumerates the
  exact assertions the corresponding `verify.yml` makes today (no new
  assertions added; codifies existing intent). Closes plan gaps G4 + G5.
- **`Makefile` help text** refined for `verify-quick` / `verify` /
  `verify-full` — adds "Save-point gate" / "Push gate" / "Release gate"
  semantics + duration. No target-dependency changes.
- **`testing-governance.md` cheatsheet** — single-line quick-reference
  at the top: `verify-quick` (commit) → `verify` (push) → `verify-full`
  (release).
- **`test-plan.md` sync**: TSVS column on §2 surface inventory filled in;
  §5 G4 + G5 marked CLOSED 2026-05-11; INDEX link added in §6.

### Infrastructure changes (2026-05-10)

- Inventory layout standardized as `inventory/{dev,stag,prod}/` (renamed
  from `production/`, `staging/` for symmetry with the Tiered Environment Model)
- `make hub-deploy` variable rename `NODE` → `HUB_NODE`; default switched
  from `remote` to `local` for safer ops
- `bootstrap.yml`: parameterized `semaphore_inventory_{name,path}` so the
  e2e harness can inject an isolated inventory
- e2e `run.sh`: prepend a clean step; leave the stack running on success
  for manual inspection; emit a gitignored `hosts.e2e.ini`
- New `extensions/eda/rulebooks/clean-tiny.sh` — disk-cleanup script for
  the `disk_full` self-healing path on Debian targets
- Fixed `Makefile` `ansible-lint --profile prod` (invalid argument) →
  `--profile production`
- `inventory/prod/hosts.ini` made self-contained (was failing parse on
  `-i inventory/prod` due to forward-referencing `targets_*` groups)
- `.gitignore`: e2e dynamic inventory + root build artefacts

---

## [TASK-001 closure] — branch `feat/eda-advanced-healing`, 2026-04-09 to 2026-05-10

The first major round of work on the EDA self-healing chain. Spanned 4
implementation rounds plus documentation closure. Highlights:

- **Path A** (real deployment): Ansible role-based hub deploy with rsync
  exclude hardening (21 patterns across 4 categories), state file
  separation (`/var/lib/ansispire/state/.eda_token` outside the rsync
  target), and OS-family validation
- **Path B** (dev): docker-compose dev stack with IaC bootstrap, disposable
  e2e on port 3320
- **Reactor v2.3**: Bearer-token auth (no admin password in reaction loop);
  dynamic `template_name → template_id` resolution; per-rule cooldown
  (default 600 s); `enabled: false` soft-disable; startup banner with
  schema version
- **4-layer test pyramid** (TSVS-tracked): unit (14 cases) / contract (9) /
  component (5) / disposable e2e (1); `make test-eda` covers L1+L2+L3
- **Audit relay** with cursor-based pagination, heartbeat, and zero-loss
  semantics across restarts
- **SSOT**: `config/manifest.yml` is the single source for ports + image
  versions; `make manifest-sync` propagates to `.env`
- **Inventory taxonomy**: `[hub_local]` / `[hub_remote]` / `[hub:children]`
  for management nodes; `[targets_debian|rhel|alpine]` for managed VPS

Full per-round history under [`docs/reviews/feat-eda-advanced-healing/`](docs/reviews/feat-eda-advanced-healing/).

---

## [Earlier]

For history pre-2026-04-09 see archived round changelogs under
[`docs/reviews/_archive/`](docs/reviews/_archive/) (round-2 through round-9
review iterations, the rename-to-ansispire change, the i18n refactor a/b/c
series, and the platform support addendum).
