# playbooks/AGENTS.md

Use this file when touching `playbooks/`.

- `../.agents/project/architecture.md`
- `../.agents/rules/boundaries.md`
- `../.agents/rules/testing.md`
- relevant feature maps under `../docs/reference/feature-map/`
- Keep playbooks thin orchestration layers; push reusable logic into roles when appropriate.
- Respect the control-plane vs data-plane split.
- If a playbook writes to the control-node filesystem, re-check whether `become: false` is required.
- If a playbook changes operator workflow, update the matching ops or user-guide doc.
