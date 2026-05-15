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

## [Unreleased] — branch `feat/vps-manager-plugin`

### VPS Manager plugin MVP (2026-05-14)

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
