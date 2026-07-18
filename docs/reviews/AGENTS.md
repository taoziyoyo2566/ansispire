# docs/reviews/AGENTS.md

Use this file when touching the legacy `docs/reviews/` tree.

- `../../.agents/rules/branching.md`
- `../../.agents/rules/docs-sync.md`
- `../../.agents/rules/file-naming.md`
- `../../.agents/rules/plan-structure.md`
- `../../.agents/rules/plan-hierarchy.md` for parent/child/addendum plan relationships.
- `../../.agents/rules/evidence-backed-planning.md` for plans that depend on external/current knowledge.
- `../../.agents/rules/execution-reflection.md` for plans that will be executed against live infrastructure or external systems.
- `../../TODO.md`
- Do not create a new topic here. New topic evidence belongs under
  `docs/workstreams/`.
- Keep an existing topic wholly in this tree until a dedicated migration moves
  its entire directory and updates all repository links. Never split one topic
  across both roots.
- For an unmigrated topic, add new approval, decision, review, note, and round
  evidence here with the type-specific names in `file-naming.md`.
- Topic-owned investigations stay in this same legacy topic directory as
  `investigation-*.md` until the whole topic migrates.
- A migration preserves historical filenames and contents. Do not rename
  `plan-*`, `design-*`, `decision-*`, or other history merely to satisfy the new
  naming convention.
- If a plan changes materially, add a dated note or a new follow-up plan instead of silently overwriting the old intent.
- If a topic becomes active and has no owner branch, note that branch-management gap explicitly rather than hiding it in prose.
- If repo-level AI guidance conflicts with the topic's actual plan history, preserve the plan history and surface the mismatch.
- `plan-*.md`
  - historical/general plan naming; still valid evidence
- `review-*.md`
  - bounded findings for the workstream
- `decision-*.md`
  - bounded decision provenance; promote the current conclusion to its stable
    owner
- `note-*.md`
  - branch-transition or one-off historical topic evidence
- `round*.changelog.md`
  - what actually landed in that round
- `_archive/`
  - immutable history unless the task is explicitly archival hygiene

Do not add these as new review-topic artifacts:

- current behavior: update `ARCHITECTURE.md` or `docs/reference/feature-map/`
- accepted target design/contract: update an owning domain document and label
  TARGET versus AS-BUILT
- operator instructions/recovery: use `docs/operations/`
- test contracts: use `docs/reference/test-specs/`
- repository policy: use `docs/governance/`
- investigations spanning multiple functional topics: use
  `docs/reference/investigations/`

Historical `design-*`, `decision-*`, backlogs, and other topic artifacts remain
valid. Promote still-current conclusions to their canonical location; do not
rename or rewrite history only to match the new routing rule. Use
`../workstreams/AGENTS.md` for new or migrated topics.
