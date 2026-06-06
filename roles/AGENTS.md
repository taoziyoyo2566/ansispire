# roles/AGENTS.md

Use this file when touching `roles/`.

- `../.agents/project/architecture.md`
- `../.agents/rules/boundaries.md`
- `../.agents/rules/testing.md`
- `../docs/reference/feature-map/INDEX.md`
- Keep roles idempotent and data-plane focused.
- Do not let controller-specific logic leak into role tasks.
- For environment-sensitive mutations, follow the sensing rules captured in `../docs/governance/operational-truths.md`.
- If a role change affects operator behavior or supported surfaces, sync the relevant feature map and docs.
