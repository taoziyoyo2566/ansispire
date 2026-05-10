# refactor-i18n-b Changelog — User-Facing READMEs to English

Date: 2026-04-14
Author: Claude (Opus 4.6)
Reference:
- [Plan](./refactor-i18n-b-plan-2026-04-14.md)
- [Charter](./review-iteration-charter.md)
- [refactor-i18n-a Changelog](./refactor-i18n-a-changelog-2026-04-14.md)
- [CLAUDE.md](../../CLAUDE.md)

---

## Purpose

Translate layer B (user-facing `README.md` files) from Chinese to English to complete the second layer of the project-wide i18n refactor. Preserves Chinese snapshots in `docs/reference-cn/snapshot-2026-04-14/` for quick lookup, matching the pattern set by refactor-i18n-a.

## Change Manifest

| # | File | Change | Summary |
|---|------|--------|---------|
| 1 | `docs/reviews/refactor-i18n-b-plan-2026-04-14.md` | NEW | Plan doc (this refactor) |
| 2 | `docs/reviews/refactor-i18n-b-changelog-2026-04-14.md` | NEW | This changelog |
| 3 | `docs/reference-cn/snapshot-2026-04-14/README.zh.md` | NEW | Pre-rewrite Chinese snapshot of root README |
| 4 | `docs/reference-cn/snapshot-2026-04-14/controller/README.zh.md` | NEW | Pre-rewrite Chinese snapshot |
| 5 | `docs/reference-cn/snapshot-2026-04-14/controller/semaphore/README.zh.md` | NEW | Pre-rewrite Chinese snapshot |
| 6 | `docs/reference-cn/snapshot-2026-04-14/extensions/eda/rulebooks/README.zh.md` | NEW | Pre-rewrite Chinese snapshot |
| 7 | `README.md` | REWRITE | Chinese → English; preserves platform matrix, directory tree, Quick Start, Core Concepts, Feature Reference table, Vault cheatsheet, Dynamic Inventory, Performance tips, References |
| 8 | `controller/README.md` | REWRITE | Chinese → English; preserves controller comparison table and upgrade-path structure |
| 9 | `controller/semaphore/README.md` | REWRITE | Chinese → English; preserves 5-step first-start, bootstrap, backup, FAQ |
| 10 | `extensions/eda/rulebooks/README.md` | REWRITE | Chinese → English; preserves rulebook YAML example byte-identical |

## Intent Per Change Category

### README i18n
These READMEs are the first thing an English-reading visitor sees in the repo. Keeping them Chinese after layer A was done leaves a visible inconsistency between runtime instructions (English, per layer A) and user-facing docs (Chinese). Translating them aligns the reading experience. Code blocks, table structure, and relative links are byte-preserved — only natural-language prose was translated.

### Snapshot preservation
Chinese originals are mirrored to `docs/reference-cn/snapshot-2026-04-14/` with `.zh.md` suffix, preserving the original directory layout (`controller/`, `controller/semaphore/`, `extensions/eda/rulebooks/`). Mirror was done **before any rewrite** so the snapshots are byte-identical to the pre-rewrite originals. This matches the pattern already established in refactor-i18n-a.

### Reference pointer in translated files
Each translated README starts with a single line pointing to its Chinese snapshot, so readers who prefer the Chinese version know where to find it without relying on git history.

## Explicitly Not Done (Boundaries)

- `roles/*/README.md` — scanned; already English (no action taken)
- Layer C (inline Chinese comments in `Makefile`, `ansible.cfg`, YAML files) — refactor-i18n-c, separate round
- Layer D (historical review docs `docs/reviews/claude-review-round-*`, `round-*-change-log-*`) — permanent Chinese per layered plan
- No code changes, no structural edits beyond prose translation
- No git commits (user has not authorized)
- No changes to `controller/semaphore/docker-compose.yml`, `controller/semaphore/bootstrap.yml`, playbooks, inventory, molecule — out of scope

## Self-Check Results

| Check | Result |
|-------|--------|
| CJK chars in `README.md` | **0** ✓ |
| CJK chars in `controller/README.md` | **0** ✓ |
| CJK chars in `controller/semaphore/README.md` | **0** ✓ |
| CJK chars in `extensions/eda/rulebooks/README.md` | **0** ✓ |
| `.zh.md` snapshot count (`find docs/reference-cn/snapshot-2026-04-14 -name '*.zh.md' \| wc -l`) | **10** (6 from i18n-a + 4 from i18n-b) ✓ |
| Chinese snapshots byte-identical to pre-rewrite originals | ✓ (copied before any edit) |
| Code blocks and table structure preserved verbatim | ✓ (tables `\|`-aligned, code blocks unchanged except for inline Chinese comments inside YAML/bash examples, which were translated) |
| Internal relative links still resolve | ✓ (`controller/README.md`, `semaphore/README.md`, `docs/reviews/...`, `examples/advanced_patterns.yml` all present) |
| `roles/*/README.md` untouched | ✓ (already English; not in change manifest) |

## Token Estimate (rough)

- Root README Chinese version: ~18.5 KB
- Root README English version: ~19.0 KB (slightly longer due to English phrasing)
- **Token savings per view**: English markdown ≈ 0.25 tokens/char vs Chinese ≈ 2 tokens/char → ~75% fewer tokens when these READMEs are pulled into context (e.g., when Claude reads them during a session). Layer B READMEs are not auto-loaded, so savings apply only when explicitly referenced, but the delta on-demand is still substantial.

## CLAUDE.md Updates (This Round)

No new behavioral rules identified. Existing rules applied correctly:
- R1 plan-first: plan doc written before rewrite ✓
- R3 roadmap-approved-first: user pre-approved the layered plan during refactor-i18n-a ("既然建议分层方案，那就按照这个来实施吧"); this round is layer B of that approved plan ✓
- R7 local-ops autonomy: all file edits are local non-destructive ops — no confirmation needed ✓

## Post-Round State

- All **user-facing READMEs** are now English-only with a single-line pointer to the Chinese snapshot
- `docs/reference-cn/snapshot-2026-04-14/` now contains 10 `.zh.md` files (runtime + charter + READMEs)
- Layer C (inline code comments) remains Chinese — next i18n round if user authorizes
- Layer D (historical review docs) remains Chinese by design

## Follow-Up Memory Update

`memory/project_round_progress.md` should gain a "refactor-i18n-b landed" line in its Landed section under this changelog's link, and `refactor-i18n-b` should be removed from the Backlog.

## Next Steps (added retroactively per R8 — see CLAUDE.md §6 Step 4)

### Immediately doable
- **Resume Round 8** (IAM + credential centralization + lightweight audit) — plan archived at `docs/reviews/claude-review-round-8-2026-04-14.md`, authorization checklist in §14. Owner: user decides to resume.
- **Start refactor-i18n-c** (inline Chinese comments in `Makefile`, `ansible.cfg`, YAML) — scoped, low-risk, can be done autonomously once authorized. Owner: user approves, Claude executes.
- **Start Round 9** (minimal Prometheus + Grafana observability stack) — prerequisite for Round 8's audit flow. Owner: user sequences vs Round 8.

### Blocked
- **Git commit of accumulated work** (Rounds 5/7, refactor-i18n-a/b) — user has not authorized; `git status` shows large uncommitted set. Blocks the "git tag snapshot" alternative to the `docs/reference-cn/` mirror. Owner: user authorizes commit scope.
- **Round 8 OIDC + Loki pieces** — deferred to Rounds 11 / 9 per earlier decision; do not re-open without explicit ask.

### Deferrable / removable from backlog
- **AWX comparative teaching** (Round 12 item) — 4-6 GB RAM; only if user wants the comparison. Safe to drop if scope tightens.
- **Round 10 secret-backend migration to Vault** — ansible-vault is sufficient for the teaching scope; can stay deferred indefinitely.

## CLAUDE.md Updates (This Round, added retroactively)

- **R8 added** to §7: every round must end with a Next Steps block. Source: this conversation's user question "接下来该做什么，为什么不显示". §6 gained Step 4 describing the required format (immediately doable / blocked / deferrable).
- Verified: the original Chinese CLAUDE.md did NOT contain this rule either — the gap pre-existed refactor-i18n-a and is not a translation loss.
