# Architecture Routing

Read `ARCHITECTURE.md` first for architecture-sensitive work.

Then route by surface:

- `controller/` or `extensions/eda/`
  - `docs/reference/feature-map/audit-plane.md`
  - `docs/reference/feature-map/eda-core.md`
  - `docs/reference/feature-map/eda-remediation.md`

- `roles/`, `playbooks/`, `inventory/`, `Makefile`, `config/manifest.yml`
  - `docs/reference/feature-map/INDEX.md`
  - relevant feature map under `docs/reference/feature-map/`

- `playbooks/vps/`
  - `docs/reference/feature-map/vps-lifecycle.md`
  - `docs/operations/vps-lifecycle.md`

- review, plan, or branch-governance work
  - `TODO.md`
  - `docs/governance/contributing.md`
  - `docs/reviews/`

- Keep control-plane logic separate from role/data-plane logic.
- Treat `config/manifest.yml` as SSOT for project-managed ports and image versions.
