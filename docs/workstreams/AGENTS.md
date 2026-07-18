# docs/workstreams/AGENTS.md

Use this file for active, time-bounded functional bundles.

- `../../.agents/rules/branching.md`
- `../../.agents/rules/docs-sync.md`
- `../../.agents/rules/file-naming.md`
- `../../.agents/rules/plan-structure.md`
- `../../.agents/rules/plan-hierarchy.md`
- `../../.agents/rules/evidence-backed-planning.md` when external/current
  knowledge affects a plan.
- `../../.agents/rules/execution-reflection.md` for live infrastructure or
  external-system execution.
- `../../TODO.md`

Allowed topic artifacts:

- `README.md`
  - mandatory single entry point for a new or reorganized bundle: function,
    owner branch, state, current action, artifact map, stable external links
  - an existing bundle adds it when its evidence layout is next materially
    changed
- `direction-*.md`, `execution-*.md`, `addendum-*.md`
  - approval artifacts differentiated by scope
- `investigation-*.md`
  - empirical investigation or runtime/API probe owned by this topic
- `decision-*.md`
  - bounded decision, authority, and rationale; promote the active conclusion
    to its stable owner
- `review-*.md`
  - bounded findings for the workstream
- `note-*.md`
  - branch-transition or one-off historical topic evidence
- `round*.changelog.md`
  - what actually landed in that round
- historical filenames imported by a whole-topic migration
  - retain `plan-*`, `design-*`, `backlog-*`, `IVG-*`, and other original names
    and contents rather than renaming history for consistency
- `_history/<old-topic>/`
  - complete evidence from a predecessor topic absorbed by this function

Keep all materials whose lifecycle belongs to the function in this one
directory. In particular, do not move topic-owned probes to the global
investigation tree or keep an absorbed child/predecessor topic in a second
top-level directory.

Shared stable documents whose lifecycle is independent of this workstream still
belong to architecture/feature maps, cross-topic investigations, operations,
test specs, or governance. Link those documents from `README.md`; do not copy
them into the bundle.

Functional colocation also defines the maintenance boundary: normal edits,
supersession, and archival happen inside the bundle. Whole-bundle deletion
still requires exact authorization for historical evidence and must remove or
update `TODO.md` plus stable external links in the same change.

One topic must exist under exactly one root. Do not duplicate or split a topic
between `docs/workstreams/` and legacy `docs/reviews/`. A migration moves the
whole tracked topic, preserves historical filenames, and updates all repository
links in one change.
