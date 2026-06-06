# CLAUDE.md — Shared Workflow Baseline for Claude Sessions

The Ansispire-specific mandate for every Claude session; takes precedence over default AI behavior. Inherits the cross-project methodology in `~/workspace/CLAUDE.md` — this file holds only what is Ansispire-specific, not the generic rules already resident there.

Resident context — keep it methodology-only (workspace W-R14 universality test):

> *"No matter what I'm doing, I should X."*

If a rule only fires for a specific surface, task type, or artefact, it belongs in the relevant governance / README / spec file, **not** here.

When guidance conflicts, prefer user instruction, deeper path-local `AGENTS.md`, and current repo truth over this file.

---

## 0. AI Behavioral Protocol (The Peer Rule)

<protocol>
- **Proactive Challenge**: do an Impact Analysis first; never blindly implement a change.
- **Chain of Thought**: for [L2] and [L1.5] tasks, use `<thinking>` blocks to weigh trade-offs before acting.
- **Sync Guard** (project truth sources — at task closure, update each one the change touched):
    1. `ARCHITECTURE.md` — global architecture
    2. `README.md` — operational entry / quickstart
    3. `docs/reference/feature-map/<name>.md` — per-feature scope
    4. `CHANGELOG.md` `[Unreleased]` — release notes (trigger criteria in the `CHANGELOG.md` header)
    5. `docs/reference/feature-map/INDEX.md` — aggregate inventory; **mandatory** when touching `roles/`, `playbooks/`, `controller/`, `extensions/eda/`, `inventory/`, `Makefile`, or `config/manifest.yml` (drift here = future agents re-derive the inventory each session)
</protocol>

(Whole-file refactor over bottom-append applies to this file too — see workspace `~/workspace/CLAUDE.md` §5.)

---

## 1. Workload Classification (L0–L2)

<classification>
| Level | Scope | Workflow |
| :--- | :--- | :--- |
| **🟢 [L0] Hygiene** | typos, comments, non-functional formatting | direct execution |
| **🟡 [L1] Engineering** | bug fix, single-role refactor | strategy → act → verify |
| **🔍 [L1.5] Investigation** | RCA, technical spike | investigation report (IVG) → recommendation |
| **🔴 [L2] Architecture** | new subsystem, API shift, NFR change | plan doc (mandatory) → user approval → implement → changelog |
</classification>

Long-form per-tier spec: `docs/governance/ai-workflow.md §1`.

---

## 2. Layered Context Governance (lazy-load in this order)

Use `AGENTS.md` / nested `AGENTS.md` as the routing layer, then load actual truth in this hierarchy:

1. **Design truth**: `ARCHITECTURE.md` (read FIRST).
2. **Dynamic truth**: `TODO.md` (sole task ledger; the former `todo` branch was retired 2026-06-05 — its history is preserved under tag `archive/todo-ledger-2026-06-05`).
3. **Investigation truth**: `docs/reference/investigations/INDEX.md` — if status is `Applied`, skip deep-reading; the rule already lives at the 「应用位置」column target.
4. **Logic truth**: `docs/reference/feature-map/<name>.md` (per module).
5. **Implementation**: source code or `details.md`.

---

## 3. Engineering Standards

- **Control vs. Data**: strict decoupling between `controller/` logic and execution `roles/`.
- **Evidence-based verification**: every change backed by terminal logs (lint / test / syntax). The what-to-run-when decision tree lives in `docs/governance/testing-governance.md §3`.

---

## 4. Branching & Lifecycle Rules

Every branch is created from a permitted base and merges to a permitted parent. `dev` is trunk during development; `master` ships at release boundaries. (Generic trunk-sync + new-branch hygiene lives in workspace `~/workspace/CLAUDE.md` §4; the lineage below is Ansispire-specific.)

| Branch type | Created from | Merges to |
| :--- | :--- | :--- |
| `feat/<topic>` | `dev` OR another `feat/<parent>` (stacked feature) | **`dev` only** |
| `fix/<topic>` | **`feat/<parent>` only** | back to that parent `feat/<parent>` |
| `chore/<topic>` / `refactor/<topic>` | as `fix/` (roll up via a `feat/`) | parent `feat/` |
| `hotfix/<topic>` | `master` (production emergency only) | `master` + cherry-pick to `dev` |

- **`fix/` NEVER merges directly to `dev`** — sub-fix work rolls up through its parent `feat/`, keeping `dev` history one-PR-per-topic.
- **`feat/` can stack on another `feat/`** when work logically depends on an uncompleted parent.
- **No direct commits to `dev` or `master`** — every change lands via PR.

**Archive on merge (do NOT delete branches)**: merged branches are historical evidence — preserve them via annotated tag `archive/<branch-name>-<merge-date>`, then remove the branch ref. Use **`scripts/archive_branch.sh <branch> <merge-target> <PR#>`** — the canonical W-R19/W-R20-safe implementation (atomic tag-create + TOCTOU-safe ref delete, trunk-protected, handles both `feat→dev` and `fix→parent`). Do NOT hand-run bare `git push origin :ref` or unguarded `git branch -D`. Branches created before 2026-05-20 are grandfathered — apply on their next merge.

---
*Project: Ansispire | Claude workflow baseline; combine with AGENTS routing and repo truth.*
