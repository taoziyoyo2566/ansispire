# Branching Rules

Current branch policy is described in `CLAUDE.md §4`, but branch decisions should be cross-checked against active plan docs, branch-management notes, and the actual branch state.

- For git command behavior, read `.agents/rules/git.md`.
- `feat/<topic>` can start from `dev` or another `feat/<parent>`.
- `fix/`, `chore/`, and `refactor/` roll up through a parent `feat/`.
- No direct commits to `dev` or `master`.
- Do not merge `fix/` directly to `dev`.

- Project-wide agent guidance (`AGENTS.md`, `.agents/`, and broad path-local routing) is baseline governance: land it on a dev-based branch, then sync active feature branches from `dev`. Only feature-specific local guidance should ride with that feature branch.
- One topic should have one clear owner branch.
- Do not keep landing a new architecture direction into a transition branch if the topic has already diverged.
- If a plan set under `docs/reviews/feat-<topic>/` has no matching branch and is becoming active, create the matching `feat/<topic>` branch and move future work there.
- If `CLAUDE.md` branch rules and active topic docs conflict, surface the conflict instead of silently choosing one.

## Multi-machine / publish sync

The same user works from multiple machines; an artifact that exists only in one
clone's working tree is invisible everywhere else.

- **Commit governance artifacts before switching away.** When leaving a topic for
  other work (or ending a session), commit plan docs, TODO updates, and round
  notes even if the code itself is mid-flight — a docs-only WIP commit is fine.
  An untracked plan cannot be superseded, reviewed, or seen by another machine.
- **Push the owner branch at round close / session end.** Push credentials are
  available on dev hosts; an unpushed branch is stale truth on every other clone.
- **Agent behavior**: commit and push remain user-gated operations — at round
  close, *propose* the commit/push explicitly (with the exact commands) rather
  than executing unprompted or silently skipping; the gap this section closes is
  the artifact never being offered for publication at all.
- **Check freshness when resuming on any machine.** Run `git fetch origin`
  (stating the reason — see `git.md` review-required list), then check
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
