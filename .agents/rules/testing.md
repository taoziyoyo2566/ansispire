# Testing Rules

Use `docs/governance/testing-governance.md` as the authoritative decision tree.

- Run the smallest test set that matches the touched surface.
- If you change code and skip tests, say so explicitly.
- For repo-wide or role/playbook changes, expect stronger verification than for docs-only changes.
- Docs-only changes: usually no test required, but link and consistency checks may still matter.
- Governance or workflow docs: ensure referenced commands and paths still exist.
- `roles/`, `playbooks/`, `controller/`, `plugins/`: read the matching row in `docs/governance/testing-governance.md §3`.
