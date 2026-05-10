# CLAUDE.md — Project Governance & Execution Rules

This file governs every Claude session. It is the **foundational mandate** for Ansispire and takes precedence over default AI behavior.

---

## 0. AI Behavioral Protocol (The Peer Rule)

<protocol>
- **Proactive Challenge**: AI MUST NOT blindly implement changes. Perform an **Impact Analysis** first.
- **Sync Guard**: Before closing a task, AI MUST verify:
    1. Does the change affect `ARCHITECTURE.md` (Architecture)? If yes, sync.
    2. Does the change affect `README.md` (Operational)? If yes, sync.
    3. Update or create the relevant **Feature Map** in `docs/reference/feature-map/`.
    4. If the change is **user-visible** (CLI behavior, config defaults, public interface, breaking refactor, security policy), append to `CHANGELOG.md`'s `[Unreleased]` section in the same commit. Pure-internal refactors / tests / docs cleanup do NOT trigger CHANGELOG.
- **Chain of Thought**: For all [L2] and [L1.5] tasks, use `<thinking>` blocks to analyze trade-offs before acting.
</protocol>

---

## 1. Workload Classification (L0 - L2)

<classification>
| Level | Scope | Workflow |
| :--- | :--- | :--- |
| **🟢 [L0] Hygiene** | Typos, comments, non-functional formatting | Direct execution. |
| **🟡 [L1] Engineering** | Bug fixes, single-role refactor | Strategy -> Act -> Verification. |
| **🔍 [L1.5] Investigation** | Root Cause Analysis (RCA), Technical Spikes | **Mandatory**: Create `docs/reference/investigations/IVG-*.md`. |
| **🔴 [L2] Architecture** | New subsystems, API shifts, NFR changes | **Mandatory**: Design RFC in `docs/reviews/`. |
</classification>

---

## 2. Layered Context Governance (Lazy-loading)

To optimize context and cost, load information in this specific hierarchy:

1.  **Design Truth**: `ARCHITECTURE.md` (Global architecture - Read FIRST).
2.  **Dynamic Truth**: `todo` branch / `TODO.md` (Current tasks - Read SECOND).
3.  **Investigation Truth**: `docs/reference/investigations/INDEX.md` (Empirical history - **If status is `Applied`, skip deep-reading**; findings are already in the 「应用位置」column target. Only load the full IVG if status is `Active` and the task is related).
4.  **Logic Truth**: `docs/reference/feature-map/<name>.md` (Module scope).
5.  **Implementation**: Source code or `details.md`.

---

## 3. Engineering Standards

- **Control vs. Data**: Maintain strict decoupling between `controller/` logic and execution `roles/`.
- **Investigation Protocol**: Any RCA or analysis task MUST follow the `docs/reference/investigations/TEMPLATE.md` and be logged in `INDEX.md`. When findings are applied to CLAUDE.md, ARCHITECTURE.md, or other rule files, update INDEX.md status to `Applied` and fill in the 「应用位置」column so future agents can skip deep-reading.
- **Evidence-based Verification**: Every change must be backed by terminal logs (lint/test/syntax).
- **TSVS Mandatory**: No functional test is "Done" without a record in `docs/reference/test-specs/` using the project template.
- **Audience Alignment**: Documentation under `docs/` is organized by reader audience, not by artefact type. Before creating or editing a doc, identify the audience (end-user / maintainer / contributor / future agent) and place the file in the matching subdir. The current subdir layout is documented in `docs/README.md`. Do not mix audiences in one file.

---

## 4. Documentation Patterns

<patterns>
### Pattern A — Review work (feat / fix / refactor / explore)
Location: `docs/reviews/<kind>-<topic>/`
Content: `plan-YYYY-MM-DD.md` (before implementation) and `roundN-YYYY-MM-DD.changelog.md` (after each round). Per workspace W-R10 topic-first naming; round files live INSIDE the topic dir, never at top level.

### Pattern B — Empirical Investigation
Location: `docs/reference/investigations/IVG-<TASK_ID>-<SLUG>.md`
Note: Always register in `docs/reference/investigations/INDEX.md`. When findings are applied to a rule file, mark the row `Applied` and fill the 「应用位置」column so future agents skip deep-reading.
</patterns>

---

## 5. Feedback & Evolution

This file is self-evolving. Extract feedback from every round to refine these rules. **Do not append — refactor globally.**

---
*Project: Ansispire | Optimized for Claude with XML & Thinking*
