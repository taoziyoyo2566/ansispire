# AGENTS.md

Lightweight Codex routing entry for `ansispire`.
Do not turn it into another monolithic governance file.

## Always Apply

- Read only what the task needs.
- Prefer existing repo docs as truth; `.agents/` routes to them.
- Prefer minimal diffs.
- If a deeper `AGENTS.md` exists, use it for that subtree.
- If user instructions conflict with this file, follow the user.
- `.agents/rules/authorization.md` is the permission/authorization SSOT. Read it
  before the first write, Git mutation, external write, or live operation, and
  whenever the user asks what requires permission.

## Session Bootstrap

When starting in this repo, after a context reset, or when the user asks "where are we", do a read-only status scan before proposing work:

1. Run:
   - `git status --short --branch`
   - `git log --oneline --decorate --max-count=5`
2. Read:
   - `.agents/rules/session-bootstrap.md`
   - `.agents/rules/codex-capabilities.md`
   - `.agents/project/overview.md`
   - `TODO.md`
3. If the current branch maps to a topic, read that functional bundle's
   `README.md` first when present, then the latest relevant plan,
   investigation, unresolved review, governing decision, and round changelog
   under `docs/workstreams/`; use `docs/reviews/` only for an unmigrated legacy
   topic. If an existing topic lacks `README.md`, read its current artifacts and
   report the missing hub as migration debt rather than stopping bootstrap.
4. Summarize current branch, clean/dirty state, active topic, likely next steps, and blocked/deferrable items.

Do not modify files during bootstrap.

## Choose Context Before Any Non-trivial Change

- Start with the smallest relevant set, then load more only when the task needs it.
- For repo facts and AI-guidance ordering: `.agents/project/overview.md` and `.agents/project/agent-strategy.md`.
- For architecture-sensitive work: `.agents/project/architecture.md`.
- For implementation or workflow edits: `.agents/rules/boundaries.md` and `.agents/rules/testing.md`.
- For coding-related implementation tasks: `.agents/rules/coding-plan.md`.
- For task-efficiency or tool-selection questions: `.agents/rules/codex-capabilities.md`.

## Read When Modifying Existing Behavior

- `.agents/scenarios/modify-existing-feature.md`
- `.agents/rules/coding-plan.md`
- `.agents/rules/docs-sync.md`
- `.agents/rules/operational-quirks.md`

## Read When Fixing A Bug

- `.agents/scenarios/fix-bug.md`
- `.agents/rules/coding-plan.md`
- `.agents/rules/operational-quirks.md`
- `.agents/rules/docs-sync.md`

## Read When Adding A New Feature Or Subsystem

- `.agents/scenarios/new-feature.md`
- `.agents/rules/coding-plan.md`
- `.agents/rules/branching.md`
- `.agents/rules/docs-sync.md`

## Read When Doing A Review Only

- `.agents/project/overview.md`
- `.agents/project/agent-strategy.md`
- `.agents/scenarios/review-change.md`
- `.agents/rules/review-closure.md`

## Read When User Explicitly Asks For A Commit

- `.agents/rules/authorization.md`
- `.agents/rules/git.md`
- `.agents/rules/commits.md`

## Read When Touching Branches / Plans / Workstream Docs

- `.agents/rules/authorization.md`
- `.agents/rules/git.md`
- `.agents/rules/branching.md`
- `.agents/rules/plan-hierarchy.md` when plans have parent/child/addendum relationships.
- `.agents/rules/evidence-backed-planning.md` when plan content depends on external knowledge or current best practice.
- `.agents/rules/execution-reflection.md` when executing or planning live infrastructure work.
- `docs/AGENTS.md`

## Path-specific Routing

- `docs/AGENTS.md` for `docs/` and workstream-evidence changes.
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
