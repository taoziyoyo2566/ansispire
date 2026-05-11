# CLAUDE.md — Project Governance & Execution Rules

This file governs every Claude session. It is the **foundational mandate** for Ansispire and takes precedence over default AI behavior.

Resident context — every line is loaded into every session, so every rule must pass the universality test in §4 before it lands here.

---

## 0. AI Behavioral Protocol (The Peer Rule)

<protocol>
- **Proactive Challenge**: AI MUST NOT blindly implement changes. Perform an **Impact Analysis** first.
- **Sync Guard**: At task closure, sync each truth source the change touched:
    1. `ARCHITECTURE.md` — global architecture
    2. `README.md` — operational entry / quickstart
    3. `docs/reference/feature-map/<name>.md` — per-feature scope
    4. `CHANGELOG.md` `[Unreleased]` — release notes (trigger criteria documented in `CHANGELOG.md` header)
- **Chain of Thought**: For all [L2] and [L1.5] tasks, use `<thinking>` blocks to analyze trade-offs before acting.
</protocol>

---

## 1. Workload Classification (L0 – L2)

<classification>
| Level | Scope | Workflow |
| :--- | :--- | :--- |
| **🟢 [L0] Hygiene** | Typos, comments, non-functional formatting | Direct execution. |
| **🟡 [L1] Engineering** | Bug fixes, single-role refactor | Strategy → Act → Verification. |
| **🔍 [L1.5] Investigation** | Root Cause Analysis (RCA), Technical Spikes | Long-form: `docs/governance/ai-workflow.md §1`. |
| **🔴 [L2] Architecture** | New subsystems, API shifts, NFR changes | Long-form: `docs/governance/ai-workflow.md §1`. |
</classification>

---

## 2. Layered Context Governance (Lazy-loading)

To optimize context and cost, load information in this hierarchy:

1.  **Design truth**: `ARCHITECTURE.md` (read FIRST).
2.  **Dynamic truth**: `TODO.md` / `todo` branch.
3.  **Investigation truth**: `docs/reference/investigations/INDEX.md` — if status is `Applied`, skip deep-reading; the rule already lives at the 「应用位置」column target.
4.  **Logic truth**: `docs/reference/feature-map/<name>.md` (per module).
5.  **Implementation**: source code or `details.md`.

---

## 3. Engineering Standards

- **Control vs. Data**: Maintain strict decoupling between `controller/` logic and execution `roles/`.
- **Evidence-based Verification**: Every change must be backed by terminal logs (lint / test / syntax). The decision tree for *what to run when* lives in `docs/governance/testing-governance.md §3`.

---

## 4. Feedback & Evolution

This file is self-evolving — extract feedback every round and refactor **globally** (W-R9 / R11: do not append).

**Audit principle (workspace W-R14)**: before adding any rule here, run the test —

> *"No matter what I'm doing, I should X."*

If the rule only fires for a specific surface, task type, or artefact, it belongs in the relevant governance / README / spec file, **not** in this resident-context file. Situational rules accumulate token cost on every session for every future task; only universal methodology earns its place here.

---
*Project: Ansispire | Optimized for Claude with XML & Thinking*
