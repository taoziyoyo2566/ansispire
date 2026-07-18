# Documentation Artifact Routing And File Naming

Choose the owning function/topic before choosing the artifact type or filename.
A document is not a plan merely because it is written before implementation.
The directory answers which functional bundle owns the material; the prefix
answers what kind of artifact it is.

## Choose the owner, then the artifact

| Responsibility | Canonical location | New-file pattern |
|---|---|---|
| Current task priority/status | `TODO.md` | update the existing ledger |
| Functional topic entry and artifact map | topic evidence directory | `README.md` |
| Approval-gated direction | topic evidence directory | `direction-<slug>-YYYY-MM-DD.md` |
| Approval-gated implementation approach | topic evidence directory | `execution-<slug>-YYYY-MM-DD.md` |
| Approval-gated detail for an existing plan | topic evidence directory | `addendum-<slug>-YYYY-MM-DD.md` |
| Bounded decision and rationale | topic evidence directory | `decision-<slug>-YYYY-MM-DD.md` |
| Formal review/audit findings | topic evidence directory | `review-<slug>-YYYY-MM-DD.md` |
| Completed-round evidence | topic evidence directory | `round<N>-YYYY-MM-DD.changelog.md` |
| Topic-owned empirical investigation or runtime/API probe | topic evidence directory | `investigation-<slug>.md` |
| Cross-topic investigation with an independent lifecycle | `docs/reference/investigations/` | `IVG-<SCOPE>-<SLUG>.md` |
| Current architecture/implemented behavior | `ARCHITECTURE.md` or `docs/reference/feature-map/` | stable semantic name; normally no date |
| Accepted target design or stable contract | owning `docs/<domain>/` document, clearly labeled TARGET versus AS-BUILT | stable semantic name; normally no date |
| Operator procedure/recovery | `docs/operations/` | `<kebab-slug>.md` |
| User workflow | `docs/user-guide/` | existing numbered convention |
| Repository policy/governance | `docs/governance/` | `<kebab-slug>.md` |
| Test contract | `docs/reference/test-specs/` | `<kebab-slug>.md` |

## Resolve the topic evidence directory

Use exactly one directory for a functional topic:

| Topic state | Topic evidence directory | Rule for new artifacts |
|---|---|---|
| New topic | `docs/workstreams/<kind>-<topic>/` | use the type-specific names in this file |
| Unmigrated legacy topic | `docs/reviews/<kind>-<topic>/` | keep all topic evidence here; new approval/review/decision artifacts use type-specific names |
| Migrated legacy topic | `docs/workstreams/<kind>-<topic>/` | preserve imported historical filenames; use type-specific names only for files created after migration |

`docs/workstreams/` is the preferred time-bounded approval, decision, review,
and round-evidence surface. The older `docs/reviews/` tree is a legacy root: do
not create new topics there, and do not split one topic across both roots.

The topic directory is a functional bundle, not a plan-only folder. All
topic-owned lifecycle material stays together there: plans, investigations,
decisions, reviews, branch notes, round evidence, and superseded inputs absorbed
from a predecessor topic. Do not route one of those files elsewhere merely
because its artifact type has a global-looking name.

Every new or reorganized active topic directory must contain `README.md` as its
single entry point. Existing active topics add it the next time their evidence
layout is materially changed. It records the function, owner branch, current
state, current action, artifact map, and links to any stable cross-topic
documents. `TODO.md` should normally link to this hub instead of exposing
readers to several internal files.

A migration moves the entire tracked topic directory in one change, preserves
historical filenames and contents unless a separately justified correction is
required, and updates all repository links. Renaming `plan-*`, `design-*`,
`decision-*`, or other historical files is not a migration requirement.

When one topic is absorbed into another functional owner, move the complete
source-topic evidence into the destination bundle (normally under
`_history/<old-topic>/`) and update links. Do not keep one functional change
split across two top-level topic directories merely to preserve an obsolete
branch name.

Stable documents with an independent lifecycle still keep their canonical
locations: repository-wide architecture, cross-topic investigations, shared
runbooks, governance, and reusable test contracts. Link them from the topic
hub; do not duplicate them.

Do not create a new child plan merely to restate a phase already approved by an
existing plan. Create one only when a distinct scope or implementation decision
needs separate approval.

---

## Plan documents

Use a type-specific prefix so a newly created approval artifact is identifiable
from a directory listing. Resolve `<topic-evidence-dir>` with the table above:

- direction: `<topic-evidence-dir>/direction-<slug>-YYYY-MM-DD.md`
- execution: `<topic-evidence-dir>/execution-<slug>-YYYY-MM-DD.md`
- detail addendum: `<topic-evidence-dir>/addendum-<slug>-YYYY-MM-DD.md`

Rules:

- `kind` matches the workstream type (`feat`, `fix`, `refactor`, `chore`,
  `audit`, etc.)
- `slug` describes **what the plan does**, not which branch it lives on (2-5 words, kebab-case)
- date is the creation date, placed at the end so `ls` sorts by topic first
- one plan per distinct decision scope; if scope changes significantly, create a new file rather than rewriting the old one

Examples:
```
docs/workstreams/feat-example-profile/direction-composable-profiles-2026-07-17.md
docs/workstreams/feat-example-profile/execution-identity-migration-2026-07-18.md
docs/workstreams/feat-example-profile/addendum-resolver-contract-2026-07-19.md
```

Anti-patterns:
```
plan-2026-05-25.md                 <- purpose and plan type are hidden
plan-carrier-probe-2026-07-18.md   <- a probe should be an investigation, not a plan
execution-wu0-restatement-*.md      <- duplicates an already-approved phase
```

Historical note:
- Existing `plan-*.md` and older nonconforming filenames remain valid evidence
  in either evidence root.
- Do not rename old files only for naming consistency, including during a
  whole-topic migration.
- Apply type-specific names to new files, including a replacement created for a
  materially changed approval scope.

---

## Changelog / round evidence

`<topic-evidence-dir>/round<N>-YYYY-MM-DD.changelog.md`

- `N` is a monotonically increasing integer within the topic
- date is the round completion date
- one file per work round; do not concatenate multiple rounds into one file

---

## Other dated review artifacts

Formal findings that belong to one workstream use:

`<topic-evidence-dir>/review-<slug>-YYYY-MM-DD.md`

Bounded decisions use:

`<topic-evidence-dir>/decision-<slug>-YYYY-MM-DD.md`

A decision record preserves what was decided, by whom, and why. Promote its
still-current conclusion to the owning stable architecture/domain/governance
document, but do not use that living document as a substitute for decision
provenance.

Branch-transition notes or one-off review inputs use
`note-<slug>-YYYY-MM-DD.md` when they need to remain as historical topic
evidence rather than current truth.

Use the topic evidence directory for a topic-owned investigation. Do not use it
for a shared canonical runbook, repository-wide stable design, reusable test
specification, or governance rule. Historical `design-*`, `decision-*`,
`backlog-*`, `IVG-*`, and other filenames remain valid after migration;
promote still-current cross-topic conclusions to the canonical location rather
than renaming or rewriting history.

---

## Investigation reports

Choose ownership before location:

| Ownership test | Location | Pattern |
|---|---|---|
| The investigation exists to unblock one functional topic and should close/archive with it | `<topic-evidence-dir>/` | `investigation-<slug>.md` |
| The investigation spans multiple topics or remains useful independently after one topic is removed | `docs/reference/investigations/` | `IVG-<SCOPE>-<SLUG>.md` |

- Topic-owned investigations are registered in that topic's `README.md`, not in
  the global investigation index.
- Cross-topic IVGs are registered in
  `docs/reference/investigations/INDEX.md`.
- Investigation reports are living documents updated in place. If a new round
  contradicts a prior conclusion, add a dated `## Update YYYY-MM-DD` section
  rather than rewriting the original finding.
- Never keep two live copies merely to satisfy both indexes.

## Functional bundle lifecycle

- Add, revise, supersede, archive, or remove topic-owned materials inside the
  functional bundle so one operation can see the whole impact.
- When the function is retired, `README.md` must state whether the bundle is
  archived, absorbed, or eligible for deletion.
- Deleting historical evidence still requires the exact authorization in
  `.agents/rules/authorization.md`; functional colocation makes the deletion
  boundary clear but does not silently authorize it.
- Removing a bundle requires updating `TODO.md` and every stable external link
  in the same change.

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
