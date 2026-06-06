# plugins/AGENTS.md

Use this file when touching `plugins/`.

- `../.agents/project/architecture.md`
- `../.agents/rules/boundaries.md`
- `../.agents/rules/testing.md`
- `../docs/reference/feature-map/vps-manager.md`
- Plugin code should stay a thin shell around the underlying Ansible or control-plane behavior.
- Do not reintroduce custom state, callback, or inventory layers if the toolchain already provides them.
- Keep plugin docs and feature maps in sync with behavior changes.
