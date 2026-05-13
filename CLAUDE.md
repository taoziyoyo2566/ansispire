# CLAUDE.md — Project Governance & Execution Rules

This file governs every Claude session. It is the **foundational mandate** for Ansispire and takes precedence over default AI behavior.

Resident context — every line is loaded into every session. Add a rule here only if it passes the universality test (workspace W-R14):

> *"No matter what I'm doing, I should X."*

If the rule only fires for a specific surface, task type, or artefact, it belongs in the relevant governance / README / spec file, **not** here.

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
- **Chain of Thought**: For all [L2] and [L1.5] tasks, use `<thinking>` blocks to analyze trade-offs before acting.
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
*Project: Ansispire | Optimized for Claude with XML & Thinking*
