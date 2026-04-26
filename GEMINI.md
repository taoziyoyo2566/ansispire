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
| **feat** | Business logic addition. Requires updated Feature Map. |
| **fix** | Bug fixing. Must include regression proof. |
| **refactor** | NO NEW FEATURES. Changes must be behaviorally equivalent. |
| **security** | Strict data-masking. No secrets in logs/commit msgs. |
| **hotfix** | Emergency only. Can skip L2 planning but requires post-mortem. |

## 2. Layered Context Governance (Lazy-loading)
1. **Global Map**: `SUMMARY.md` (Design Truth - **Read first**).
2. **Feature Maps**: `docs/features/<name>/summary.md` (Logic Truth - **Read during research**).
3. **Deep Details**: `docs/features/<name>/details.md` or Code (**Deep-dive on demand only**).

**AI Constraint**: State *"I am entering the implementation context of <module>"* before deep-diving.

## 3. Engineering Standards
- **Control vs. Data**: Strict decoupling of Controller and Roles.
- **Audit Integrity**: Zero-data-loss and full traceability.
- **Documentation Synchronicity**: README (Operational) and Maps (Logical) must stay in sync with code.
- **Vendor Integrity**: Note local patches to external roles in SUMMARY.md; prevent regression.

## 4. Validation & Finality
- A task is NOT done until **Evidence-based Verification** is provided (terminal logs).
