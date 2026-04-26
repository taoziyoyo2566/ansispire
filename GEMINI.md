# GEMINI.md — Project Governance & Execution Rules

This file is the foundational mandate for all Gemini CLI sessions. It takes precedence over general defaults.

## 0. AI Behavioral Protocol (The Peer Rule)
- **Proactive Challenge**: AI MUST NOT blindly implement architectural or process changes suggested by the user. 
- **Impact Analysis**: AI must first output a concise "Impact & Trade-off Analysis" (ROI, Maintenance Cost, Potential Conflicts). 
- **Confirmation**: AI only updates governance files after the user provides secondary confirmation based on the analysis.

## 1. Workload Classification & Branch Constraints

### Branch Naming & Semantics
Changes MUST occur in purpose-driven branches: `<type>/<subsystem>-<target>`.

| Type | Semantic Constraints |
| :--- | :--- |
| **feat** | **Design RFC Mandate**: Before implementation, AI must provide a design covering Goal, Proposed Logic, and Trade-offs. |
| **fix** | **RCA Mandate**: Before fixing, AI must output a Root Cause Analysis and regression proof plan. |
| **refactor** | NO NEW FEATURES. Changes must be behaviorally equivalent. |
| **security** | Strict data-masking. No secrets in logs/commit msgs. |
| **hotfix** | Emergency only. Can skip RFC planning but requires post-mortem. |

### Master Stability & Handover
- `master` branch contains only roadmap and done tasks in `TODO.md`.
- **Session Entry Protocol**: Every new session MUST run `git branch` to discover active `feat/` or `refactor/` branches. If a branch exists for a pending task, AI MUST switch to it and resume the Design RFC process.

## 2. Layered Context Governance (Lazy-loading)
1. **Global Map**: `SUMMARY.md` (Design Truth - **Read first**).
2. **Roadmap**: `TODO.md` (What's next - **Read second**).
3. **Feature Maps**: `docs/features/<name>/summary.md` (Logic Truth - **Read during research**).
4. **Deep Details**: `docs/features/<name>/details.md` (Deep-dive on demand only).

## 3. Engineering Standards
- **Control vs. Data**: Strict decoupling of Controller and Roles.
- **Audit Integrity**: Zero-data-loss and full traceability.
- **Documentation Synchronicity**: Update README and Feature Maps in the same turn as code changes.
- **Vendor Integrity**: Note local patches to external roles in SUMMARY.md; prevent regression.

## 4. Validation & Finality
- A task is NOT done until **Evidence-based Verification** is provided (terminal logs).
