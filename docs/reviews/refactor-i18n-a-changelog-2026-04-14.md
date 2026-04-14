# refactor-i18n-a Changelog — Runtime Files to English

Date: 2026-04-14
Author: Claude (Opus 4.6)
Reference:
- [Plan](./refactor-i18n-a-plan-2026-04-14.md)
- [Charter](./review-iteration-charter.md)
- [CLAUDE.md](../../CLAUDE.md)

---

## Purpose

Convert layer A (runtime-loaded) and layer E (charter) project documents from Chinese to English to reduce per-session token cost. Preserve Chinese snapshots in `docs/reference-cn/` for human reference. Layers B, C, D out of scope.

## Change Manifest

| # | File | Change | Summary |
|---|------|--------|---------|
| 1 | `docs/reviews/refactor-i18n-a-plan-2026-04-14.md` | NEW | Plan doc (this refactor) |
| 2 | `docs/reviews/refactor-i18n-a-changelog-2026-04-14.md` | NEW | This changelog |
| 3 | `docs/reference-cn/README.md` | NEW | Explains the purpose and layout of the Chinese snapshot directory |
| 4 | `docs/reference-cn/snapshot-2026-04-14/CLAUDE.zh.md` | NEW | Pre-rewrite Chinese snapshot of CLAUDE.md |
| 5 | `docs/reference-cn/snapshot-2026-04-14/memory/project_real_scope.zh.md` | NEW | Chinese snapshot |
| 6 | `docs/reference-cn/snapshot-2026-04-14/memory/feedback_architect_mode.zh.md` | NEW | Chinese snapshot |
| 7 | `docs/reference-cn/snapshot-2026-04-14/memory/feedback_local_ops_autonomy.zh.md` | NEW | Chinese snapshot |
| 8 | `docs/reference-cn/snapshot-2026-04-14/memory/project_round_progress.zh.md` | NEW | Chinese snapshot |
| 9 | `docs/reference-cn/snapshot-2026-04-14/docs/reviews/review-iteration-charter.zh.md` | NEW | Chinese snapshot |
| 10 | `CLAUDE.md` | REWRITE | Chinese → English; 8 sections, rules R1–R7 preserved |
| 11 | `memory/project_real_scope.md` | REWRITE | Chinese → English |
| 12 | `memory/feedback_architect_mode.md` | REWRITE | Chinese → English |
| 13 | `memory/feedback_local_ops_autonomy.md` | REWRITE | Chinese → English |
| 14 | `memory/project_round_progress.md` | REWRITE | Chinese residual cleaned; adds refactor-i18n-a landed entry, adds Round 8 archived entry, adds refactor-i18n-b/c to backlog |
| 15 | `docs/reviews/review-iteration-charter.md` | REWRITE | Chinese → English; date annotated 2026-04-14 |
| 16 | Session `4817f33f-….jsonl` | DELETE | Empty fork, 1.9 KB, only contained `/exit` |
| 17 | Session `9987d1c2-….jsonl` | DELETE | Empty fork, 1.9 KB, only contained `/exit` |

## Intent Per Change Category

### Runtime i18n
CLAUDE.md and memory/*.md are loaded into every Claude session. Chinese text in these files costs roughly 2–3× the tokens of equivalent English (BPE splits Chinese aggressively). Rewriting them in English reduces per-session token overhead without sacrificing rule fidelity — all R1–R7 numbers, §1–§8 structure, and cross-references are preserved byte-identical in meaning.

### Snapshot preservation
The user wants a Chinese reference "for quick lookup". Directory mirror (`docs/reference-cn/snapshot-2026-04-14/`) is the chosen form because it is browsable without git tooling. A git tag snapshot was considered but deferred — tags point to commits, and the working tree currently has a large set of uncommitted changes from Rounds 5/7/8 which the user has not yet authorized committing.

### Charter i18n
The charter is referenced from CLAUDE.md §8 and is consulted whenever Claude needs to recall review rules. It isn't auto-loaded, but rewriting it in English maintains tone consistency with CLAUDE.md and reduces cognitive friction when Claude reads both in the same session.

### Fork cleanup
Two 1.9 KB session files (`4817f33f-…`, `9987d1c2-…`) contained only a `permission-mode` marker and `/exit` — zero work. Removing them declutters the `/resume` list.

## Explicitly Not Done (Boundaries)

- Layer B (root `README.md`, `controller/*/README.md`, `roles/*/README.md`) — belongs to refactor-i18n-b, separate round
- Layer C (inline Chinese comments in `Makefile`, `ansible.cfg`, YAML files) — refactor-i18n-c, separate round
- Layer D (historical review docs: `docs/reviews/claude-review-round-*`, `round-*-change-log-*`) — **permanent Chinese** per plan §3
- Git tag snapshot — deferred; requires committing currently unstaged changes, which user has not authorized
- Translation of `docs/reviews/claude-review-round-8-2026-04-14.md` — D layer, no-op
- No changes to `controller/`, `roles/`, `playbooks/`, `inventory/`, `molecule/` — out of scope

## Self-Check Results

| Check | Result |
|-------|--------|
| Mirror snapshot file count (`find docs/reference-cn/snapshot-2026-04-14 -name '*.zh.md' \| wc -l`) | **6** ✓ |
| Rules R1–R7 in CLAUDE.md (`grep -c '^- \*\*R[1-7]'`) | **7** ✓ |
| Top-level sections §1–§8 in CLAUDE.md (`grep -c '^## [0-9]\. '`) | **8** ✓ |
| Residual CJK chars in runtime files (grep Han range across 9 files) | **0** ✓ |
| Session files remaining (was 5, expect 3) | **3** ✓ |
| Chinese snapshots are byte-identical to originals (pre-rewrite) | ✓ (copied before any edit) |

## Token Estimate (rough)

- CLAUDE.md Chinese version: 7634 bytes (~2500 chars, BPE estimate ~3000–4000 tokens)
- CLAUDE.md English version: 8396 bytes (~8400 chars, BPE estimate ~2000–2100 tokens)
- **Savings per session load**: approximately **1000–2000 tokens** on CLAUDE.md alone, plus additional savings on memory files (~500–1500 tokens total). Actual numbers depend on tokenizer — not independently benchmarked this round.

## CLAUDE.md Updates (This Round)

No new behavioral rules identified. The user feedback this round was a refactor directive, not a behavior correction. Existing R1–R7 all applied correctly:
- R1 plan-first: plan doc written and shared before implementation ✓
- R3 roadmap-approved-first: layered plan presented and explicitly approved ✓
- R7 local-ops autonomy: deleting orphan session files is file-level cleanup, not destructive system state; but because it deletes user data, I asked first — **this matches the "still require approval" spirit** but stretches R7's boundary. Recording this as an observation for future refinement rather than a rule change.

## Post-Round State

- Current `CLAUDE.md` is English-only and shorter on tokens
- `memory/` has 7 English files (3 were pre-existing English; 4 were Chinese→English this round)
- `docs/reviews/review-iteration-charter.md` is English-only
- `docs/reference-cn/snapshot-2026-04-14/` preserves all 6 Chinese originals with a README explaining intent
- Two orphan fork sessions removed from `/resume` list
- Next i18n rounds available: refactor-i18n-b (READMEs), refactor-i18n-c (code comments) — both await user authorization
