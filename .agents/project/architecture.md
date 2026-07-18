# Architecture Routing

Read `ARCHITECTURE.md` first for architecture-sensitive work.

Then route by surface:

- `controller/` or `extensions/eda/`
  - `docs/reference/feature-map/audit-plane.md`
  - `docs/reference/feature-map/eda-core.md`
  - `docs/reference/feature-map/eda-remediation.md`

- `roles/`, `playbooks/`, `inventory/`, `Makefile`, or `config/manifest.yml`
  - `docs/reference/feature-map/INDEX.md`
  - relevant feature map under `docs/reference/feature-map/`

- `plugins/`
  - `docs/reference/feature-map/vps-manager.md`

- document, review, plan, or branch-governance work
  - `TODO.md`
  - `.agents/rules/file-naming.md`
  - `docs/governance/contributing.md`
  - `docs/AGENTS.md`
  - use `docs/workstreams/` for approval/review/round evidence after
    classifying the artifact
  - treat `docs/reviews/` as the legacy workstream root

- Keep control-plane logic separate from role/data-plane logic.
- Treat `config/manifest.yml` as SSOT for project-managed ports and image versions.
