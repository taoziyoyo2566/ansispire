# plugins/AGENTS.md

Use this file when touching `plugins/`.

- `../.agents/project/architecture.md`
- `../.agents/rules/boundaries.md`
- `../.agents/rules/testing.md`
- Plugin code should stay a thin shell around the underlying Ansible or control-plane behavior.
- Do not reintroduce custom state, callback, or inventory layers if the toolchain already provides them.
- On `feat/target-architecture`, do not rebuild the removed local VPS control surface under `plugins/`; prefer `playbooks/vps/` plus Semaphore-side integration unless the active plan changes.
- Keep plugin docs and feature maps in sync with behavior changes.
