# Ansispire AI-Native Workflow Guide

This document explains how to effectively collaborate with AI agents (like Gemini CLI) in the Ansispire project. We use a **Tiered Governance Model** to balance architectural integrity with development velocity.

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
  3. Verification via `molecule` or `tox`.
  4. AI summarizes results in the chat.

### 🔍 [L1.5] Investigation (Empirical)
- **Scope**: Root Cause Analysis (RCA), performance spikes, compatibility research, or feasibility studies.
- **Workflow**:
  1. AI creates `docs/investigations/IVG-<TASK_ID>-<SLUG>.md` based on `TEMPLATE.md`.
  2. Document all hypotheses, experiments, and terminal logs in the file.
  3. **Lazy-loading**: These reports are loaded in future turns ONLY if they are relevant to the current bug or subsystem.
  4. Final conclusion must provide a clear recommendation (e.g., "Implement Fix X" or "Task is unfeasible").

### 🔴 [L2] Strict (Architecture)
- **Scope**: New subsystems, cross-component interface changes, `controller/` logic, RBAC/Audit shifts, or NFR changes.
- **Workflow**:
  1. **Mandatory Plan**: AI uses `enter_plan_mode` to create a plan in `docs/reviews/feat-<topic>/plan-YYYY-MM-DD.md`.
  2. **User Approval**: Implementation starts ONLY after the user approves the plan.
  3. **Evidence-based Changelog**: A final changelog must be created with actual terminal output proving successful validation.

---

## 2. Evidence-Based Verification

In Ansispire, "it should work" is not enough. All non-trivial changes must be backed by **Evidence**. 

When an AI completes a task, it must provide:
- **Linting Results**: `make lint` or `ansible-lint`.
- **Functional Proof**: `molecule test` output or a successful `ansible-playbook --check` run.
- **Syntax Check**: `ansible-playbook --syntax-check`.

---

## 3. Core AI Directives (from GEMINI.md)

1. **Refactor Globally, Do Not Append**: When adding rules or configs, the AI should rewrite the file to improve its overall structure rather than just appending at the bottom.
2. **Context Efficiency**: We use `.geminiignore` to keep the context focused. Do not ask the AI to read files explicitly excluded unless necessary for the current task.
3. **Control vs. Data**: AI must ensure that `controller/` logic remains decoupled from execution `roles/`.

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

## 6. How to Invoke Specialized Sub-Agents

- For deep codebase analysis or mapping variable precedence: 
  > *"Analyze the variable precedence for the database role using codebase_investigator."*
- For batch refactoring (e.g., adding a license header to all files):
  > *"Use the generalist agent to add license headers to all .py files in the project."*

---

For the full authoritative rules, see [`GEMINI.md`](../GEMINI.md).
