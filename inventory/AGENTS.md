# inventory/AGENTS.md

Use this file when touching `inventory/`.

- `../.agents/project/architecture.md`
- `../.agents/rules/boundaries.md`
- `../.agents/rules/testing.md`
- `../docs/reference/feature-map/INDEX.md`
- Treat inventory shape as architecture, not just data entry.
- Do not create a second source of truth for host identity, groups, or connection data without an explicit plan.
- Keep environment separation (`dev`, `stag`, `prod`, `vps_runner`, `examples`) intentional and documented.
- If changing group layout or inventory taxonomy, sync the feature map and operator docs.
