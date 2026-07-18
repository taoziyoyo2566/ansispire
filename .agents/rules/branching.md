# Branching Rules

Current branch policy is described in `CLAUDE.md §4`, but branch decisions should be cross-checked against active plan docs, branch-management notes, and the actual branch state.

- Branch authorization comes from `.agents/rules/authorization.md`; a request to
  edit files on the current branch does not implicitly authorize a branch
  switch, branch creation, commit, or publication.
- For git command behavior, read `.agents/rules/git.md`.
- `feat/<topic>` can start from `dev` or another `feat/<parent>`.
- `fix/`, `chore/`, and `refactor/` roll up through a parent `feat/`.
- No direct commits to `dev` or `master`.
- Do not merge `fix/` directly to `dev`.

- Project-wide agent guidance (`AGENTS.md`, `.agents/`, and broad path-local routing) is baseline governance: land it on a dev-based branch, then sync active feature branches from `dev`. Only feature-specific local guidance should ride with that feature branch.
- One topic should have one clear owner branch.
- Do not keep landing a new architecture direction into a transition branch if the topic has already diverged.
- If a workstream under `docs/workstreams/feat-<topic>/` (or an unmigrated
  legacy topic under `docs/reviews/feat-<topic>/`) has no matching branch and is
  becoming active, create the matching `feat/<topic>` branch and move future
  work there.
- If `CLAUDE.md` branch rules and active topic docs conflict, surface the conflict instead of silently choosing one.

## Multi-machine / publish sync

The same user works from multiple machines; an artifact that exists only in one
clone's working tree is invisible everywhere else.

- **Offer a governance checkpoint before switching away.** When leaving a topic
  or ending a session, identify uncommitted plan docs, TODO updates, and round
  notes and propose a scoped preservation/publication step. Do not create an
  unsolicited WIP commit or stash.
- **Offer publication at round close / session end.** An unpushed owner branch
  is stale truth on every other clone, but commit and push remain user-gated
  operations. Propose the exact scoped commands rather than executing
  unprompted or silently skipping.
- **Check freshness when resuming on any machine.** Run `git fetch origin`
  (stating the reason — see the freshness exception in `git.md`), then check
  `git log --oneline HEAD..origin/<branch>` before basing new work. A clean
  `git status` only means no local edits; it says nothing about being current.
  Basing a plan on a stale clone is how the 2026-06-09 conflicting-plan incident
  happened.

## Integration workflow

- A backup branch is only a recovery reference. It is not a completed task, not a merge target, and not evidence that prerequisites reached `dev`.
- Before continuing a parent branch, verify every prerequisite branch is either:
  - already merged into `origin/dev`, then sync the parent from `origin/dev`; or
  - intentionally stacked on the parent because the dependency is feature-specific.
- Baseline / project-wide work goes to a dev-based branch first, then into `dev`, then into active feature branches by trunk-sync.
- Feature-specific work can land directly on the feature owner branch or a child branch.
- Do not mark a prerequisite "done" merely because its local branch is clean or backed up. It is done only when it is merged to the intended base, or when the closeout explicitly says it remains local/unmerged.
- Before claiming a feature branch is ready, check both:
  - net diff against its intended base
  - commit/topic history for accidental add/revert churn that should be cleaned before PR
