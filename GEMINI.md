# GEMINI.md — Project Governance & Execution Rules

This file is the foundational mandate for all Gemini CLI sessions. It takes precedence over general defaults.

## 0. AI Behavioral Protocol (The Peer Rule)
- **Proactive Challenge**: AI MUST NOT blindly implement changes. Perform an Impact Analysis first.
- **Sync Guard (Consistency)**: Before marking any task as "Done", AI MUST verify:
    1. Does the change affect `SUMMARY.md` (Architecture)? If yes, sync it.
    2. Does the change affect `README.md` (Operational)? If yes, sync it.
    3. Is there a relevant `Feature Map`? Create/Update it.
    **Only after all three are confirmed can the task be closed in the ledger.**

## 1. Workload Classification & Branch Constraints

### The Task Ledger (Branch: `todo`)
- **SSOT**: The authoritative task list is `TODO.md` on the `todo` branch. 
- **Isolation**: `TODO.md` MUST NOT exist on `master` or other code branches.
- **Operation**: Use `git show todo:TODO.md` to read, and `git checkout todo -- TODO.md` to update progress.

### Branch Naming & Semantics
- Pattern: `<type>/<subsystem>-<target>`.
- **feat**: Requires Design RFC.
- **fix**: Requires RCA (Root Cause Analysis).
- **refactor**: No new features. Behavioral equivalence only.

## 2. Layered Context Governance (Lazy-loading)
1. **Design Truth**: `SUMMARY.md` (Global architecture - Read FIRST).
2. **Dynamic Truth**: `todo branch / TODO.md` (Task state - Read SECOND).
3. **Investigation Truth**: `docs/investigations/` (Empirical history - Always check `INDEX.md` first; lazy-load full reports ONLY when task relates to same subsystem or RCA).
4. **Logic Truth**: `docs/features/<name>/summary.md` (Module scope).
5. **Deep Implementation**: `details.md` or Code (Deep-dive on demand).

## 3. Engineering Standards
- **Control vs. Data**: Decouple Controller from Roles.
- **Vendor Integrity**: Note local patches to external roles in SUMMARY.md.
- **Investigation Protocol**: Any task involving "investigation", "analysis", or "RCA" MUST generate a report in `docs/investigations/IVG-<TASK_ID>-<SLUG>.md` using the project template. These files are strictly for empirical discovery and MUST NOT be placed in `docs/reviews/`.
- **Cross-AI Audit (Corrective Action)**: When an AI agent identifies structural violations or factual errors in an existing Investigation Report (IVG), it MUST NOT proceed with the implementation. It MUST:
    1. Document the violations and present a corrective action plan (Option A or B) to the user.
    2. **Obtain explicit user confirmation BEFORE executing any corrective action.**
    3. **Option A (Archive)**: Downgrade the IVG to a design note and move it to `docs/reviews/` if it lacks empirical evidence.
    4. **Option B (Rectify)**: Update the IVG to meet TEMPLATE.md standards before continuing.
- **Evidence-based Verification**: Every unit must provide terminal logs (lint/syntax/test).
- **Test Governance (TSVS)**: ALL functional, loopback, and integration tests MUST be documented using the `docs/test-specs/TEMPLATE.md` format. No task involving "testing" is considered "Done" without a corresponding PASS record in `docs/test-specs/`.
