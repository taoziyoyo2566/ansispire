# controller/AGENTS.md

Use this file when touching `controller/`.

- `../.agents/project/architecture.md`
- `../.agents/rules/boundaries.md`
- `../.agents/rules/testing.md`
- relevant feature maps under `../docs/reference/feature-map/`
- Keep controller-plane logic separate from role/data-plane implementation.
- For audit-plane changes, check whether `test-eda`, loop-smoke, or e2e coverage is required.
- For Semaphore bootstrap or API-surface changes, verify operator and feature-map docs stay aligned.
- `audit/AGENTS.md` for `controller/audit/`
