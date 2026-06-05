# CLAUDE.md — Shared Workflow Baseline for Claude Sessions

This file is the project-level workflow baseline for Claude sessions in Ansispire.
It complements:

- `AGENTS.md` and nested `AGENTS.md` for routing and path-local guidance
- `GEMINI.md` for complementary Gemini / cross-agent guidance
- repo docs and code for the current operational truth

Resident context — every line is loaded into every Claude session. Add a rule here only if it passes the universality test (workspace W-R14):

> *"No matter what I'm doing, I should X."*

If the rule only fires for a specific surface, task type, or artefact, it belongs in the relevant governance / README / spec / `AGENTS.md`, **not** here.

When guidance conflicts, prefer user instruction, deeper path-local `AGENTS.md`, and current repo truth over this file.

---

## 0. AI Behavioral Protocol (The Peer Rule)

<protocol>
- **Proactive Challenge**: AI MUST NOT blindly implement changes. Perform an **Impact Analysis** first.
- **Sync Guard**: At task closure, sync each truth source the change touched:
    1. `ARCHITECTURE.md` — global architecture
    2. `README.md` — operational entry / quickstart
    3. `docs/reference/feature-map/<name>.md` — per-feature scope
    4. `CHANGELOG.md` `[Unreleased]` — release notes (trigger criteria documented in `CHANGELOG.md` header)
    5. `docs/reference/feature-map/INDEX.md` — aggregate functional inventory; **mandatory** when touching `roles/`, `playbooks/`, `controller/`, `extensions/eda/`, `inventory/`, `Makefile`, or `config/manifest.yml` (drift here = future agents re-derive the inventory each session)
- **Trade-off Capture**: For all [L2] and [L1.5] tasks, record the key trade-offs in the plan doc / IVG / review note. Do not rely only on implicit reasoning.
- **Refactor globally, do not append**: when editing any rule / config file (this one included), rewrite for whole-file coherence rather than tacking on at the bottom.
</protocol>

---

## 1. Workload Classification (L0 – L2)

<classification>
| Level | Scope | At-a-glance workflow |
| :--- | :--- | :--- |
| **🟢 [L0] Hygiene** | Typos, comments, non-functional formatting | Direct execution |
| **🟡 [L1] Engineering** | Bug fixes, single-role refactor | Strategy → Act → Verification |
| **🔍 [L1.5] Investigation** | Root Cause Analysis (RCA), Technical Spikes | Investigation report (IVG) → recommendation |
| **🔴 [L2] Architecture** | New subsystems, API shifts, NFR changes | Plan doc (mandatory) → user approval → implement → changelog |
</classification>

Long-form workflow spec per tier: `docs/governance/ai-workflow.md §1`.

---

## 2. Layered Context Governance (Lazy-loading)

Use `AGENTS.md` / nested `AGENTS.md` as the routing layer, then load actual truth in this hierarchy:

1.  **Design truth**: `ARCHITECTURE.md` (read FIRST).
2.  **Dynamic truth**: `TODO.md` (sole task ledger; the former `todo` branch was retired 2026-06-05 — its history is preserved under tag `archive/todo-ledger-2026-06-05`).
3.  **Investigation truth**: `docs/reference/investigations/INDEX.md` — if status is `Applied`, skip deep-reading; the rule already lives at the 「应用位置」column target.
4.  **Logic truth**: `docs/reference/feature-map/<name>.md` (per module).
5.  **Implementation**: source code or `details.md`.

---

## 3. Engineering Standards

- **Control vs. Data**: Maintain strict decoupling between `controller/` logic and execution `roles/`.
- **Evidence-based Verification**: Every change must be backed by terminal logs (lint / test / syntax). The decision tree for *what to run when* lives in `docs/governance/testing-governance.md §3`.

---

## 4. Branching & Lifecycle Rules

Branch types form a strict hierarchy. Every new branch MUST be created from a permitted base and MUST merge back to a permitted parent. `dev` is trunk during the development phase; `master` ships at release boundaries.

| Branch type | Created from | Merges to |
| :--- | :--- | :--- |
| `feat/<topic>` | `dev` OR another `feat/<parent>` (stacked feature) | **`dev` only** |
| `fix/<topic>` | **`feat/<parent>` only** | back to that parent `feat/<parent>` |
| `chore/<topic>` / `refactor/<topic>` | same rules as `fix/` (must roll up via a `feat/`) | parent `feat/` |
| `hotfix/<topic>` | `master` (production emergency only) | `master` + cherry-pick to `dev` |

- **`fix/` NEVER merges directly to `dev`.** Sub-fix work rolls up through its parent `feat/`, then the `feat/` merges to `dev`. This keeps `dev` history readable as one PR per topic.
- **`feat/` can stack on another `feat/`** when work logically depends on an uncompleted parent.
- **No direct commits to `dev` or `master`.** Every change lands via PR.

### Archive on merge (do NOT delete branches)

Merged branches are **historical evidence** — preserve them via annotated tag, then remove the branch ref. The two recipes below differ in hardcoded prefix and merge target; **pick by branch type, do NOT copy across types**.

**Recipe A — `feat/<topic>` merged to `dev`** (trunk-bound):

```bash
TIP=$(git rev-parse origin/feat/<topic>)         # tip of the merged feat branch
git tag -a archive/feat-<topic>-YYYY-MM-DD "$TIP" \
    -m "Merged to dev via PR #<N> on YYYY-MM-DD"
git push origin archive/feat-<topic>-YYYY-MM-DD  # publish the tag
git push origin :feat/<topic>                    # delete remote branch ref
git branch -D feat/<topic>                       # local cleanup (safe — tag holds the commits)
```

**Recipe B — `fix/<sub-topic>` (or `chore/`/`refactor/`) merged to parent `feat/<parent>`**:

```bash
TIP=$(git rev-parse origin/fix/<sub-topic>)      # tip of the merged fix branch
git tag -a archive/fix-<sub-topic>-YYYY-MM-DD "$TIP" \
    -m "Merged to feat/<parent> via PR #<N> on YYYY-MM-DD"
git push origin archive/fix-<sub-topic>-YYYY-MM-DD
git push origin :fix/<sub-topic>                 # delete the fix branch, NOT the parent feat
git branch -D fix/<sub-topic>
```

- Tag namespace `archive/<original-branch-name>-<merge-date>` keeps the branch listing clean while making history searchable via `git tag -l 'archive/*'`.
- The merge commit + archive tag together form the durable record; the branch ref itself is redundant.
- Existing branches that pre-date this rule (created before 2026-05-20) are grandfathered — apply the new rule on their next merge, not retroactively.

---
*Project: Ansispire | Claude workflow baseline; combine with AGENTS routing and repo truth.*
