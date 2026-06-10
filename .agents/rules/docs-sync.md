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
- If you added, renamed, or removed a **test target or test surface** (Make target, smoke script, TSVS), sync `docs/governance/testing-governance.md` (§3 decision tree row + §4 command table) and `docs/reference/test-specs/INDEX.md` in the same change — an unregistered test target is invisible to the decision tree and will not be run.
- For workflow/governance changes, also check `docs/governance/`.
