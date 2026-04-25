# GEMINI.md — Project Governance & Execution Rules

This file is the foundational mandate for all Gemini CLI sessions operating within the `ansispire` workspace. It takes precedence over general AI defaults and supersedes historical `CLAUDE.md` paradigms.

## 0. Project Positioning: The Ansispire Control System
**Ansispire** is an **Ansible-based multi-server management control system** (Control Plane + Data Plane). It is NOT a generic development template.
- **Architectural Depth > Surface Coverage**: Prioritize controller High Availability (HA), RBAC, audit trails, and multi-tenancy over simple configuration tasks.
- **Control vs. Data**: Maintain strict separation between management logic (`controller/`, plugins) and execution logic (`roles/`).

---

## 1. Tiered Governance Gates (Blast Radius)

Before writing any code, determine the **Impact Level (L0-L2)**. This replaces the rigid "Plan-First for everything" approach to eliminate unnecessary overhead on small tasks while protecting the architecture.

### [L2] Strict / Architecture Level
*Trigger*: New subsystems, cross-component boundaries, `controller/` logic, RBAC/Audit changes, new roles, or changes affecting NFRs (scalability, consistency).
*Workflow*: 
1. **Mandatory Planning**: You MUST use the `enter_plan_mode` tool.
2. **Artifact**: Create a plan document in `docs/reviews/feat-<topic>/plan-YYYY-MM-DD.md`.
3. **Approval**: Wait for user sign-off.
4. **Execution**: Proceed with changes.
5. **Validation**: Produce an evidence-based changelog (see §3).

### [L1] Standard / Engineering Level
*Trigger*: Single-role refactoring, bug fixes within a component, configuration structure updates.
*Workflow*:
1. **Strategy**: Output a concise 1-2 sentence strategy in the chat.
2. **Execution**: Execute surgically. No separate plan document is required unless requested.
3. **Validation**: Run relevant local tests (`molecule test`, `tox`) and summarize results in chat.

### [L0] Fast-track / Hygiene
*Trigger*: Documentation typos, comments, non-logical config tweaks (e.g., `.gitignore`), simple formatting.
*Workflow*: Execute directly and transparently. No plan or formal changelog required.

---

## 2. The RS-EV Execution Lifecycle

For all L1 and L2 tasks, adhere to the **Research -> Strategy -> Execution -> Validation** loop:

- **Research**: Do not assume codebase structure. Use `grep_search` and `glob` extensively. For complex dependencies (especially L2 tasks), invoke the `codebase_investigator` sub-agent. For bugs, empirically reproduce the failure first.
- **Strategy**: Define the plan according to the Tiered Governance (L0/L1/L2).
- **Execution**: Apply surgical changes. **Refactor Globally, Do Not Append**: When modifying configurations (e.g., tox, lint rules) or this very file, review the entire file to deduplicate and improve structure rather than just appending new lines at the bottom.
- **Documentation Synchronicity**: Every infrastructure or workflow change MUST be accompanied by a corresponding update to `README.md` and `docs/AI_WORKFLOW.md` in the same turn. Never leave the documentation in a legacy state.
- **Validation**: Validation is the only path to finality. You must execute project-specific checks (e.g., `tox`, `molecule test -s <scenario>`).

---

## 3. Semantic Validation & Evidence-Based Changelogs

For L2 tasks (and complex L1 tasks), the final deliverable is a **Changelog** (`docs/reviews/feat-<topic>/phase<N>-YYYY-MM-DD.changelog.md`).

*Historical Defect Fixed*: Changelogs must no longer be AI "self-promises" (e.g., "I checked syntax and it looks good").
*New Mandate*: Changelogs MUST contain an **Evidence Block**. You must paste the actual terminal output (or a truncated summary of success) from `tox`, `molecule`, or `ansible-playbook --syntax-check` proving the code functions as intended.

---

## 4. Context & Rule Consolidation (Self-Evolution)

At the end of a session, if the user provides structural feedback or corrections:
1. **Do not append endless rules**: Analyze if the feedback points to a broader architectural principle.
2. **Update GEMINI.md**: Consolidate the learning into the relevant section of this file (e.g., modifying the L1/L2 definitions or adding a core principle).
3. **Keep it lean**: This file must remain under 200 lines to ensure high signal-to-noise ratio.
4. **Next Steps**: Always end the session by providing the user with a concise "Next Steps" block (Immediately Doable / Blocked / Deferrable).

---

## 5. Ansispire Specific Architectural Rules

*   **Audit Integrity**: Any modification to `callback_plugins/human_log.py`, `controller/audit/`, or execution environments must explicitly address how it impacts the audit trail.
*   **Sub-agent Delegation**: 
    *   Use `codebase_investigator` for mapping out Ansible variable precedence issues or complex role dependencies.
    *   Use `generalist` for batch operations (e.g., applying a new linting rule across all `roles/`).
