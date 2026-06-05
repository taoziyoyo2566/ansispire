# playbooks/vps/AGENTS.md

Use this file when touching `playbooks/vps/`.

- `../../.agents/project/architecture.md`
- `../../.agents/rules/boundaries.md`
- `../../.agents/rules/testing.md`
- `../../docs/reviews/feat-target-architecture/plan-2026-05-25.md`
- `../../docs/reviews/feat-target-architecture/design-2026-05-26.md`
- `../../docs/reference/feature-map/vps-lifecycle.md`
- `../../docs/operations/vps-lifecycle.md`
- Keep this directory Ansible-only: playbooks, templates, and input examples for Semaphore-driven execution.
- Do not reintroduce local inbox/state handling, SSH config generation, task archiving, or wrapper CLI behavior here.
- If the `vps_task` contract changes, sync the examples and the operator docs in the same round.
