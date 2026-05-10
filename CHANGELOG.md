# Changelog

All notable changes to Ansispire are documented here. The project does not yet
use semantic versioning; entries are grouped by branch / round of work.

The format is loosely adapted from [Keep a Changelog](https://keepachangelog.com).

---

## [Unreleased] — branch `feat/eda-advanced-healing`

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
