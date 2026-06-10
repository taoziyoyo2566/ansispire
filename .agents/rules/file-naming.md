# File Naming Rules

Naming conventions by artefact type. When in doubt: slug first, date last.

---

## Plan documents

`docs/reviews/<kind>-<topic>/plan-<slug>-YYYY-MM-DD.md`

- `kind` should match the workstream type (`feat`, `fix`, `refactor`, `chore`, `audit`, etc.)
- `slug` describes **what the plan does**, not which branch it lives on (2-5 words, kebab-case)
- date is the creation date, placed at the end so `ls` sorts by topic first
- one plan per distinct decision scope; if scope changes significantly, create a new file rather than rewriting the old one

Examples:
```
docs/reviews/feat-target-architecture/plan-semaphore-first-wiring-2026-06-09.md
docs/reviews/fix-inventory-hygiene-examples/plan-inventory-hygiene-2026-05-20.md
docs/reviews/refactor-claude-md-w-r14/plan-claude-workflow-thinning-2026-05-11.md
```

Anti-pattern - date only, slug missing:
```
plan-2026-05-25.md   <- cannot tell purpose without opening the file
```

Historical note:
- Existing historical filenames that predate this rule are valid evidence.
- Do not rename old files only for naming consistency.
- Apply this rule to new files and materially rewritten plans.

---

## Changelog / round evidence

`docs/reviews/<kind>-<topic>/round<N>-YYYY-MM-DD.changelog.md`

- `N` is a monotonically increasing integer within the topic
- date is the round completion date
- one file per work round; do not concatenate multiple rounds into one file

---

## Other dated review artefacts

`docs/reviews/<kind>-<topic>/<slug>-YYYY-MM-DD.md`

Covers everything in a topic directory that is neither a plan nor a round changelog:
backlogs, decision records, design notes, branch-management notes.

- `slug` describes the content (e.g. `backlog`, `onboard-execution-models`)
- date the file like plans: slug first, date last
- stable target-state descriptions may use `design-<slug>-YYYY-MM-DD.md`; treat the
  date as the snapshot date and add dated update sections rather than renaming

---

## Investigation reports

`docs/reference/investigations/IVG-<SCOPE>-<SLUG>.md`

- `SCOPE` is a short uppercase domain tag (e.g. `SEMAPHORE`, `EDA`, `RUNNER`)
- `SLUG` is a short uppercase descriptor (e.g. `INVENTORY-API`, `RULEBOOK-MIGRATION`)
- no date in the filename; the report is a living document updated in place
- if a new investigation round contradicts a prior conclusion, add a dated `## Update YYYY-MM-DD` section rather than rewriting the original finding — preserves the reasoning chain

---

## Test specifications (TSVS)

`docs/reference/test-specs/<kebab-slug>.md`

- slug names the surface plus the test tier (e.g. `vps-semaphore-native-e2e`, `eda-reactor-unit`, `molecule-database`)
- no date in the filename; the spec is a living document updated alongside the tests it describes
- draft from `TEMPLATE.md` in the same directory; register every new spec in that directory's `INDEX.md`

---

## Feature-map references

`docs/reference/feature-map/<kebab-slug>.md`

- slug mirrors the module or subsystem name as it appears in `ARCHITECTURE.md`
- `INDEX.md` in the same directory is the aggregate inventory; update it whenever adding or removing a feature-map file

---

## AGENTS routing files

`<directory>/AGENTS.md`

- always named exactly `AGENTS.md`; no date, no slug variant
- one file per directory that needs local routing context
