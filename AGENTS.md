# AGENTS.md

Lightweight Codex routing entry for `ansispire`.
Do not turn it into another monolithic governance file.

## Always Apply

- Read only what the task needs.
- Prefer existing repo docs as truth; `.agents/` routes to them.
- Prefer minimal diffs.
- If a deeper `AGENTS.md` exists, use it for that subtree.
- If user instructions conflict with this file, follow the user.

## Choose Context Before Any Non-trivial Change

- Start with the smallest relevant set, then load more only when the task needs it.
- For repo facts and AI-guidance ordering: `.agents/project/overview.md` and `.agents/project/agent-strategy.md`.
- For architecture-sensitive work: `.agents/project/architecture.md`.
- For implementation or workflow edits: `.agents/rules/boundaries.md` and `.agents/rules/testing.md`.

## Read When Modifying Existing Behavior

- `.agents/scenarios/modify-existing-feature.md`
- `.agents/rules/docs-sync.md`
- `.agents/rules/operational-quirks.md`

## Read When Fixing A Bug

- `.agents/scenarios/fix-bug.md`
- `.agents/rules/operational-quirks.md`
- `.agents/rules/docs-sync.md`

## Read When Adding A New Feature Or Subsystem

- `.agents/scenarios/new-feature.md`
- `.agents/rules/branching.md`
- `.agents/rules/docs-sync.md`

## Read When Doing A Review Only

- `.agents/project/overview.md`
- `.agents/project/agent-strategy.md`
- `.agents/scenarios/review-change.md`
- `.agents/rules/review-closure.md`

## Read When User Explicitly Asks For A Commit

- `.agents/rules/commits.md`

## Read When Touching Branches / Plans / Review Docs

- `.agents/rules/branching.md`
- `docs/AGENTS.md`

## Path-specific Routing

- `docs/AGENTS.md` for `docs/` and review-plan work.
- `plugins/AGENTS.md` for `plugins/`.
- `controller/AGENTS.md` for `controller/`.
- `roles/AGENTS.md` for `roles/`.
- `inventory/AGENTS.md` for `inventory/`.
- `playbooks/AGENTS.md` for `playbooks/`.
- `extensions/eda/AGENTS.md` for `extensions/eda/`.

## Do Not

- Duplicate long governance docs here.
- Assume every task needs every rule file.
- Invent project facts.
