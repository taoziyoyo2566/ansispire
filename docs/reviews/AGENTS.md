# docs/reviews/AGENTS.md

Use this file when touching `docs/reviews/`.

- `../../.agents/rules/branching.md`
- `../../.agents/rules/docs-sync.md`
- `../../.agents/rules/file-naming.md`
- `../../.agents/rules/plan-structure.md`
- `../../TODO.md`
- Treat review docs as execution evidence, not general documentation.
- Keep the topic directory stable once a workstream exists.
- Prefer adding a new dated file over rewriting old round history.
- If a plan changes materially, add a dated note or a new follow-up plan instead of silently overwriting the old intent.
- If a topic becomes active and has no owner branch, note that branch-management gap explicitly rather than hiding it in prose.
- If repo-level AI guidance conflicts with the topic's actual plan history, preserve the plan history and surface the mismatch.
- `plan-*.md`
  - active intent, boundaries, decisions, gates
- `design-*.md`
  - stable target-state description or RFC-style summary
- `round*.changelog.md`
  - what actually landed in that round
- `_archive/`
  - immutable history unless the task is explicitly archival hygiene
