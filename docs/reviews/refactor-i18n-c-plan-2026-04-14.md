---
name: refactor-i18n-c Plan — Inline Code Comments to English
description: Translate inline Chinese comments and short prose in source files (Makefile, ansible.cfg, YAML, Python, Jinja) to English
type: plan
date: 2026-04-14
---

# refactor-i18n-c Plan — Inline Code Comments to English

Date: 2026-04-14
Author: Claude (Opus 4.6)
Reference:
- [Charter](./review-iteration-charter.md)
- [refactor-i18n-a changelog](./refactor-i18n-a-changelog-2026-04-14.md)
- [refactor-i18n-b changelog](./refactor-i18n-b-changelog-2026-04-14.md)

## Level Declaration

Engineering layer — inline prose / comment translation. No behavior, interface, or structural code changes.

## Purpose

Complete the layered i18n plan (layer A runtime + B READMEs done; this is layer C). Translates inline Chinese comments and docstrings in source files so the codebase is uniformly English without loss of teaching intent.

## Scope Inventory

Scanned 2026-04-14: 74 files contain CJK characters outside `docs/reference-cn/`, `docs/reviews/`, and `memory/`. Breakdown:

### In scope (layer C)

| Batch | Files | Approx. files |
|-------|-------|---------------|
| **C1** top-level config | `Makefile`, `ansible.cfg`, `requirements.yml`, `execution-environment.yml`, `pyproject.toml`, `tox.ini`, `.editorconfig`, `.yamllint`, `.pre-commit-config.yaml` | 9 |
| **C2** playbooks | `playbooks/site.yml`, `playbooks/rolling_update.yml`, `playbooks/vault_demo.yml`, `playbooks/advanced_patterns.yml` | 4 |
| **C3** roles/common | tasks/ (5), handlers/, defaults/, vars/main + vars/os/*, meta/ (2), templates/motd.j2 | ~12 |
| **C4** roles/webserver + roles/database | tasks, handlers, defaults, vars, meta, templates | ~15 |
| **C5** Python plugins | `library/app_config.py`, `filter_plugins/custom_filters.py`, `lookup_plugins/config_value.py`, `callback_plugins/human_log.py`, `inventory/dynamic/custom_inventory.py` | 5 |
| **C6** inventory data | `inventory/production/hosts.ini`, group_vars/ (4), host_vars/, dynamic/*.yml (4), `inventory/staging/*` | ~12 |
| **C7** molecule | `molecule/common/*`, `molecule/webserver/*`, `molecule/full-stack/*` | ~8 |
| **C8** controller | `controller/semaphore/docker-compose.yml`, `bootstrap.yml`, `.env.example` | 3 |
| **C9** heavy teaching files | `examples/advanced_patterns.yml` (859 CJK, heavy teaching inline comments) | 1 |
| **C10** user-facing doc | `docs/CONTRIBUTING.md` (831 CJK — technically layer-B extension, folding in here) | 1 |

Total: ~70 files.

### Out of scope / skipped

- `inventory/production/group_vars/all/vault.yml` — local, gitignored, real secrets; user-owned
- `tudo.txt` — looks like a stray scratch file (user session snippet); will flag to user for cleanup rather than translate
- `docs/reviews/*` — layer D, permanent Chinese by design
- `docs/reference-cn/*` — the Chinese snapshot mirror itself

### Boundary notes
- **No data-value translation**: only comments and docstrings are rewritten. Chinese values inside strings that are *content* (e.g., motd banners, example vhost content, test data) are kept unless they are clearly comment-like.
- **Example files** (`vault.example.yml`, `secrets_external.example.yml`): translate comment lines and key descriptions; keep example placeholder values stable.
- **Templates** (`*.j2`): translate Jinja `{# #}` comments and surrounding prose; keep template variable names and HTML/config syntax intact.

## Backup Strategy

Code files are not snapshotted to `docs/reference-cn/` — git history is authoritative for code. Only docs were snapshotted in layers A and B because they were user-facing reference material. For code comments, the git diff on restore is a sufficient record, and mirroring 70 code files would bloat the snapshot directory.

## Task Execution Order

Execute in C1 → C10 order. After each batch: verify YAML/Python syntax (no parse regression), note CJK residual count, continue. Commit all at round-end (awaiting user authorization per existing policy).

## Judgment Criteria

- Every comment conveys the same teaching intent in English
- No code logic, variable names, module names, or tag names changed
- YAML remains parseable; Python remains importable (syntax check, not runtime)
- Post-round CJK count across in-scope files: 0 (excluding the skipped list)

## Cost Budget

**Medium-to-large** (~70 file edits). Execution will be batched; user can pause between batches if desired.

## R9 Applicability

This round continues the user-approved layered i18n roadmap (a → b → c). Per R9, no fresh per-phase approval needed; scope boundaries documented here for transparency.

## Self-Check Plan

```bash
# YAML syntax
python -c "import yaml, pathlib; [yaml.safe_load(p.read_text()) for p in pathlib.Path('.').rglob('*.yml') if 'reference-cn' not in str(p) and 'reviews' not in str(p)]"

# CJK residual (expect ~0 in in-scope files after landing)
python -c "... (scan script from this plan)"
```
