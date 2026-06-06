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
