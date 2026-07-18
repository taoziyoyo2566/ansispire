# docs/AGENTS.md

Use this file when the task primarily touches `docs/`.

- Treat `docs/` as evidence, not decoration.
- Use `../.agents/rules/authorization.md` for edit authority. Documentation
  changes requested by the user do not need per-file confirmation, but
  governance and historical-evidence changes are classified by effect rather
  than treated as L0 automatically.
- Preserve historical review and investigation records unless the task is explicitly to archive or correct them.
- Choose the artifact type and canonical location with
  `../.agents/rules/file-naming.md` before creating a file. Do not default to
  the legacy `docs/reviews/` root or a plan wrapper.
- Prefer adding new historical evidence instead of rewriting old evidence to
  match the present; update living canonical documents in place.
- `../.agents/rules/branching.md`
- `../.agents/rules/docs-sync.md`
- `governance/contributing.md`
- New topic evidence belongs under `docs/workstreams/`; keep an unmigrated
  legacy topic wholly under `docs/reviews/` until an explicit whole-topic
  migration.
- Treat each topic directory as one functional bundle. Plans, topic-owned
  investigations, decisions, reviews, and round evidence stay together, with a
  `README.md` as the entry point for every new or reorganized bundle. Existing
  bundles add the hub when their evidence layout is next materially changed.
- Current architecture/behavior belongs in `ARCHITECTURE.md` or the feature
  map; accepted target design belongs in an owning domain document with
  TARGET/AS-BUILT labeling. Only cross-topic investigations belong in
  `docs/reference/investigations/`; shared runbooks remain in operations and
  policy in governance.
- If editing a plan, avoid silently changing historical scope without a dated note.
- If editing operator docs, check that referenced commands and paths still exist.
- `workstreams/AGENTS.md` for active workstream evidence.
- `reviews/AGENTS.md` for `docs/reviews/`.
