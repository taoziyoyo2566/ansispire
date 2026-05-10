# Refactor i18n-a — Runtime Files to English

Date: 2026-04-14
Author: Claude (Opus 4.6)
Reference:
- User authorization (2026-04-14): accept layered i18n strategy
- [CLAUDE.md](../../CLAUDE.md) — target file
- [Review Iteration Charter](./review-iteration-charter.md) — target file

---

## 1. Purpose

Convert **runtime-loaded project documents** (Claude Code loads these every session) from Chinese to English to reduce token cost without lowering fidelity. Keep a Chinese snapshot for human reference.

Rationale: Chinese in these files costs ~2× the tokens of equivalent English. Layered estimate saves ~3k tokens per session on auto-load.

## 2. Scope

| Layer | Files | Action |
|-------|-------|--------|
| **A (runtime)** | `CLAUDE.md` | Rewrite in English |
| **A (runtime)** | `memory/project_real_scope.md` | Rewrite in English |
| **A (runtime)** | `memory/feedback_architect_mode.md` | Rewrite in English |
| **A (runtime)** | `memory/feedback_local_ops_autonomy.md` | Rewrite in English |
| **A (runtime)** | `memory/project_round_progress.md` | Clean residual Chinese (mostly English already) |
| **E (charter)** | `docs/reviews/review-iteration-charter.md` | Rewrite in English |

Already English (no-op): `memory/MEMORY.md`, `memory/user_profile.md`, `memory/feedback_work_style.md`.

## 3. Not in this round

- Layer B (READMEs) — separate round `refactor-i18n-b`
- Layer C (inline code comments) — separate round `refactor-i18n-c`
- Layer D (historical review docs `docs/reviews/claude-review-round-*`, `round-*-change-log-*`) — **keep Chinese** permanently
- Git tag snapshot — deferred; requires commit authorization which user has not yet granted
- Translation of `docs/reviews/claude-review-round-8-*` — D-layer, no-op

## 4. Level declaration

**Engineering / refactor**. No behavioral change; pure documentation format. Review dimensions:
- Semantic equivalence: no rule content lost in translation
- Rule numbering (R1–R7): preserved identically
- Cross-references: section numbers and anchors stay stable
- Claude's actual interpretation: English must yield the same decisions as Chinese

## 5. Backup strategy

Directory mirror only (git tag deferred):

```
docs/reference-cn/
└── snapshot-2026-04-14/
    ├── CLAUDE.zh.md
    ├── memory/
    │   ├── project_real_scope.zh.md
    │   ├── feedback_architect_mode.zh.md
    │   ├── feedback_local_ops_autonomy.zh.md
    │   └── project_round_progress.zh.md
    └── docs/reviews/
        └── review-iteration-charter.zh.md
```

## 6. Task list

1. Write this plan doc (R1)
2. Create mirror directory + copy all Chinese originals (R1)
3. Rewrite `CLAUDE.md` in English
4. Rewrite 3 Chinese memory files in English (same filenames; MEMORY.md index unchanged)
5. Clean Chinese residual in `project_round_progress.md`
6. Rewrite `review-iteration-charter.md` in English
7. Delete two empty fork sessions (`4817f33f...`, `9987d1c2...`)
8. Self-check + changelog

## 7. Judgment criteria

- All R1–R7 rule numbers present in new CLAUDE.md, identical semantics
- All `project_*.md` / `feedback_*.md` memory frontmatter (name/description/type) unchanged
- Cross-reference from CLAUDE.md Section 8 to charter still resolves
- Mirror files are byte-identical to originals before rewrite
- `.zh.md` suffix used to distinguish mirrored files

## 8. Self-check items (post-implementation)

- [ ] `find docs/reference-cn/snapshot-2026-04-14 -name '*.zh.md' | wc -l` returns 6
- [ ] `grep -c '^- \*\*R[1-7]' CLAUDE.md` returns 7
- [ ] `grep -c '^## ' CLAUDE.md` returns 8 (sections 1–8)
- [ ] `wc -l CLAUDE.md memory/*.md` vs pre-rewrite line count (expect ≤ 85% of Chinese version)
- [ ] Two orphan fork sessions removed

## 9. Cost estimate

- Small–medium (<1 h for this layer)
- Single round; no split needed.

## 10. Authorization

User authorized the layered approach on 2026-04-14 ("既然建议分层方案，那就按照这个来实施吧"). Layer A execution proceeds under that authorization.
