# Ansispire AI-Native Workflow Guide

This document explains how AI collaborators used in this repo (Codex, Claude, Gemini, etc.) should work inside Ansispire. We use a **Tiered Governance Model** to balance architectural integrity with development velocity.

---

## 0. Governance Layers

Ansispire may use several AI guidance layers together:

- `AGENTS.md` and nested `AGENTS.md` — routing, local context loading, and path-specific guidance
- `CLAUDE.md` — shared workflow baseline (task classification, sync discipline, branch lifecycle)
- `GEMINI.md` — complementary Gemini / cross-agent guidance (context discipline, peer-audit, codification)
- repo docs and code — current operational truth

When they conflict or drift, prefer the active architecture, governance docs, feature maps, review plans, and code truth.

---

## 1. The Governance Model (L0 - L2)

We classify every task by its **Blast Radius** to determine the required level of planning and verification.

### 🟢 [L0] Fast-track (Hygiene)
- **Scope**: Documentation typos, code comments, `.gitignore` updates, or non-functional formatting.
- **Workflow**: The AI executes directly. No plan or changelog required.

### 🟡 [L1] Standard (Engineering)
- **Scope**: Bug fixes within a single component, refactoring a single Ansible role, or updating non-critical configurations.
- **Workflow**:
  1. AI states a 1-2 sentence **Strategy** in the chat.
  2. Implementation.
  3. Verification via the minimum required targets from `docs/governance/testing-governance.md`.
  4. AI summarizes results in the chat.

### 🔍 [L1.5] Investigation (Empirical)
- **Scope**: Root Cause Analysis (RCA), performance spikes, compatibility research, or feasibility studies.
- **Workflow**:
  1. AI creates `docs/reference/investigations/IVG-<TASK_ID>-<SLUG>.md` based on `TEMPLATE.md`.
  2. Document all hypotheses, experiments, and terminal logs in the file.
  3. **Lazy-loading**: These reports are loaded in future turns ONLY if they are relevant to the current bug or subsystem.
  4. Final conclusion must provide a clear recommendation (e.g., "Implement Fix X" or "Task is unfeasible").

### 🔴 [L2] Strict (Architecture)
- **Scope**: New subsystems, cross-component interface changes, `controller/` logic, RBAC/Audit shifts, or NFR changes.
- **Workflow**:
  1. **Mandatory Plan**: AI creates a plan in `docs/reviews/feat-<topic>/plan-YYYY-MM-DD.md`.
  2. **User Approval**: Implementation starts ONLY after the user approves the plan.
  3. **Evidence-based Changelog**: A final changelog must be created with actual terminal output proving successful validation.

---

## 2. Evidence-Based Verification

In Ansispire, "it should work" is not enough. All non-trivial changes must be backed by **Evidence**.

When an AI completes a task, it must provide:
- **Verification target(s)**: `make verify`, `make verify-quick`, or the narrower surface-specific gate required by `testing-governance.md`.
- **Functional proof**: the surface-appropriate runtime evidence (`molecule test`, `make controller-loop-smoke`, `make vps-lifecycle-syntax`, `ansible-playbook --check`, etc.).
- **Explicit gaps**: anything not run must be called out, not implied away.

---

## 3. Core AI Directives (from repo AI governance)

1. **Refactor Globally, Do Not Append**: When adding rules or configs, the AI should rewrite the file to improve its overall structure rather than just appending at the bottom.
2. **Context Efficiency**: Use routing docs and ignore files (such as `.geminiignore`) to keep the context focused. Do not force broad reads unless they are needed for the task at hand.
3. **Control vs. Data**: AI must ensure that `controller/` logic remains decoupled from execution `roles/`.
4. **Reality Check Existing Implementations**: Before adding functionality on top of an existing implementation, verify that the current implementation itself is not already off-pattern or architecturally stale.

---

## 4. Audit Integrity & Reliability

As Ansispire is a management control system, **Audit Integrity** is a top priority.

- **Zero-Loss Relay**: The audit relay now supports pagination. When modifying `controller/audit/`, ensure the cursor management logic remains atomic.
- **Evidence of Traceability**: For [L2] tasks affecting the control plane, the "Evidence Block" in your changelog should ideally include a snippet from the audit sink showing the action was captured.

---

## 5. Extending Automation (EDA)

You can add new autonomous behaviors by modifying `extensions/eda/rules.json`.

- **Event Matching**: Use simple key-value pairs in the `condition` block to match Semaphore events.
- **Safe Execution**: Prefer webhook notifications for visibility. When using `shell` actions, ensure the command is idempotent and properly logged.

---

## 6. Focused Agents and Review Passes

- For deep codebase analysis, variable-precedence mapping, or independent review, use the strongest focused analysis / review capability available in the current AI surface.
- For large but mechanically repetitive edits, use a broad execution agent only when the boundaries are already clear.
- If a specialized pass materially changes the implementation direction, capture that decision in the plan / changelog / review notes so the next agent can reconstruct it.

---

## 7. Audit Closure Standard

Review and audit work must not become an infinite refinement loop.

Treat the audit as complete when:
- the review scope is explicit
- no open correctness-routing or materially misleading findings remain in scope
- remaining items are optional and explicitly deferred
- the verification appropriate to the touched surface has passed

Default audit cadence:
- one broad audit
- one implementation pass
- one targeted re-audit

Go beyond that cadence only when scope changes, new evidence appears, or a previous assumption is proven wrong. If two consecutive passes produce no new must-fix findings, stop.

---

For repo-level AI governance inputs, see [`AGENTS.md`](../../AGENTS.md), [`CLAUDE.md`](../../CLAUDE.md), and [`GEMINI.md`](../../GEMINI.md).
When they conflict or drift from current repo reality, prefer the active architecture, governance, feature-map, review-plan, and code truth.
