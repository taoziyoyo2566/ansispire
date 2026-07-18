# docs/reviews/feat-target-architecture/AGENTS.md

Use this file when touching `docs/reviews/feat-target-architecture/`.

- `../../../.agents/rules/branching.md`
- `../../../.agents/rules/review-closure.md`
- `../../../TODO.md`
- This directory is the owner planning surface for the "return to Ansible + Semaphore" direction.
- This is an unmigrated legacy topic. Keep its evidence wholly here until a
  deliberate whole-topic move to `docs/workstreams/`; do not split it across
  both roots.
- Treat `feat/target-architecture` as the parent planning branch for this topic.
- Do not land new target-architecture planning into `feat/vps-manager-v2`.
- Current branch truth has removed the local `vps_manager` control surface; historical references remain only as review evidence and retired specs.
- `direction-*.md`, `execution-*.md`, `addendum-*.md`
  - new branch-owned approval artifacts by scope while this topic remains
    unmigrated
- `decision-*.md`, `review-*.md`, `note-*.md`
  - new bounded decision, review, or transition evidence
- `plan-*.md`, `design-*.md`
  - historical naming retained before and after any whole-topic migration; new
    accepted design belongs under `docs/feat-target-architecture/` or the
    feature map
- `TODO-*.md`
  - branch bootstrap and management backlog
- `round*.changelog.md`
  - what actually landed on this planning branch
