# Documentation Sync

Use this when a change affects behavior, structure, or operator workflow.

Primary sync targets:

1. `ARCHITECTURE.md`
2. `README.md`
3. relevant `docs/reference/feature-map/<name>.md`
4. `CHANGELOG.md` `[Unreleased]`
5. `docs/reference/feature-map/INDEX.md`

- If you touched implementation but no sync was needed, be able to explain why.
- If you touched `roles/`, `playbooks/`, `controller/`, `extensions/eda/`, `inventory/`, `Makefile`, or `config/manifest.yml`, check whether `docs/reference/feature-map/INDEX.md` needs updating.
- For workflow/governance changes, also check `docs/governance/`.
