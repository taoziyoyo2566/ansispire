---
name: refactor-i18n-b Plan — User-Facing READMEs to English
description: Concise plan for translating layer B (user-facing README files) from Chinese to English
type: plan
date: 2026-04-14
---

# refactor-i18n-b Plan — User-Facing READMEs to English

Date: 2026-04-14
Author: Claude (Opus 4.6)
Reference:
- [Charter](./review-iteration-charter.md)
- [Round 7 change log](./round-7-change-log-2026-04-14.md)
- [refactor-i18n-a changelog](./refactor-i18n-a-changelog-2026-04-14.md)

## Level Declaration

Engineering layer — pure documentation rewrite, no code or behavior changes.

## Purpose

Layer B of the project-wide i18n refactor: translate user-facing `README.md` files from Chinese to English to improve consistency with layer A (runtime files + charter, already English) and to make the repo usable by an English-reading audience. Preserve Chinese snapshots in `docs/reference-cn/snapshot-2026-04-14/` for quick lookup, matching the pattern set by refactor-i18n-a.

## Scope of This Round

Translate these 4 files to English (Chinese → English rewrite, structure byte-preserved):

1. `README.md` (project root, 459 lines)
2. `controller/README.md` (106 lines)
3. `controller/semaphore/README.md` (125 lines)
4. `extensions/eda/rulebooks/README.md` (80 lines)

Mirror Chinese originals with `.zh.md` suffix into `docs/reference-cn/snapshot-2026-04-14/` preserving directory layout.

## Out of Scope

- `roles/*/README.md` — already English (scanned; no action)
- Layer C (inline Chinese comments in Makefile / ansible.cfg / YAML) — deferred to refactor-i18n-c
- Layer D (historical review docs) — permanent Chinese per layered plan
- No code changes, no structural edits: preserve all tables, code blocks, relative links, anchor targets, and cross-references byte-identical in meaning
- No git commits (user has not authorized)

## Judgment Criteria

- Does the translated README convey the same technical intent as the Chinese original?
- Are all code blocks, tables, and relative links preserved verbatim (only natural-language prose translated)?
- Is the Chinese snapshot byte-identical to the pre-rewrite original?
- After rewrite, do the 4 runtime README files contain zero CJK characters?

## Backup Strategy

Before rewriting any file, copy the original to the mirror location:

```
docs/reference-cn/snapshot-2026-04-14/
├── README.zh.md                            ← root README
├── controller/
│   ├── README.zh.md                        ← controller/README.md
│   └── semaphore/README.zh.md              ← controller/semaphore/README.md
└── extensions/eda/rulebooks/README.zh.md   ← extensions/eda/rulebooks/README.md
```

Mirror already executed before translation (verified: 4 `.zh.md` files present alongside the 6 from i18n-a, total 10 `.zh.md` files in the snapshot).

## Task List

1. Write this plan doc ✓
2. Mirror 4 Chinese originals to `docs/reference-cn/snapshot-2026-04-14/` ✓ (done before rewrite)
3. Rewrite `README.md` (root) in English
4. Rewrite `controller/README.md` in English
5. Rewrite `controller/semaphore/README.md` in English
6. Rewrite `extensions/eda/rulebooks/README.md` in English
7. Self-check: 0 CJK in 4 translated files; 4 `.zh.md` snapshots identical to pre-rewrite originals; internal relative links still resolve
8. Write `refactor-i18n-b-changelog-2026-04-14.md`

## Self-Check Commands

```bash
# 0 CJK chars in translated files
python -c "import re, pathlib; files = ['README.md', 'controller/README.md', 'controller/semaphore/README.md', 'extensions/eda/rulebooks/README.md']; [print(f, sum(1 for c in pathlib.Path(f).read_text() if '\u4e00' <= c <= '\u9fff')) for f in files]"

# Snapshot count (should be 10: 6 from i18n-a + 4 from i18n-b)
find docs/reference-cn/snapshot-2026-04-14 -name '*.zh.md' | wc -l
```

## CLAUDE.md Impact

None expected. This round applies existing rules R1 (plan-first), R3 (roadmap-approved-first — user pre-approved the layered plan during i18n-a). No new behavioral rules anticipated.
