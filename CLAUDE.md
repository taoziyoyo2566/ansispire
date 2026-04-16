# CLAUDE.md — Project-Level Instructions

This file governs every Claude session running in this directory. It takes precedence over default behavior.
This file is **self-evolving** — every round must run the "Feedback Consolidation Loop" (see §6).

> Chinese reference snapshot: `docs/reference-cn/snapshot-2026-04-14/CLAUDE.zh.md`

---

## 1. Pre-execution Checklist (complete BEFORE any non-trivial work)

Before writing code, creating tasks, or editing files, answer the following in order:

### A. System Intent Clarification
- What **kind of system** does this work target?
  - ① engineering improvement (template/tool) · ② architecture design (system) · ③ bug fix · ④ spike / exploration
- Where are the **boundaries**? (external dependencies, integration points, ownership)
- Priority of **non-functional requirements** (NFR)? (correctness vs availability vs scalability vs cost)
- What is the **scope of authorization** for this round? Anything beyond it requires alignment.

**If the user input does not make these explicit, you MUST ask clarifying questions in your first paragraph — do not assume.**

### B. Level Declaration
Every round must declare which level it belongs to and apply the matching review dimensions:

| Level | Trigger | Review dimensions |
|-------|---------|-------------------|
| **Architecture** | New subsystem, cross-component boundary change, NFR shift, external interface | control-plane/data-plane, RBAC, observability, consistency, scalability, audit |
| **Engineering** | Configuration, tooling, scaffolding, single-component refactor | correctness, maintainability, community alignment, safe defaults |
| **Fix** | Known bug or inconsistency | minimal change scope, regression risk |
| **Exploration** | Option comparison, feasibility validation | reproducible conclusions, evidence list |

**Do not treat architecture-level problems as engineering-level work** — this has been a recurring drift in this project.

### C. Cost Budget
- Estimate: small (<30 min) / medium (<2 h) / large (multi-round)
- Large work: deliver a blueprint/roadmap for user review BEFORE creating TaskList
- Split large work across rounds to avoid exhausting usage limits

---

## 2. Plan-First (Mandatory Documentation)

**Every piece of work must produce two artifacts — both are required:**

### A. Plan / Review Document
- Path: see §5 for naming rules (depends on work type)
- Timing: **before** implementation starts
- **No implementation until the user approves the plan**
- Must contain:
  - Purpose / scope / out-of-scope / judgment criteria
  - Level declaration (architecture / engineering / fix / exploration)
  - Current-state assessment (architecture level: include gap analysis)
  - Decision rationale (why, per change)
  - Phased roadmap (required at architecture level)

### B. Change Log
- Path: see §5 for naming rules (depends on work type)
- Timing: **after** all changes land
- Must contain:
  - `Reference:` bidirectional link to the plan doc
  - File change manifest (table: file | change type | summary)
  - Intent per change
  - What was explicitly NOT done (boundaries)
  - Self-check results (syntax, consistency, critical-file presence)

**Landing criteria**: plan doc + change log + self-check all pass — only then may a unit of work be declared "done"

---

## 3. Execution Rules

### Task Management
- Use TaskCreate / TaskUpdate to manage the task list
- Mark `in_progress` before starting a task; mark `completed` immediately when done
- Run independent tasks in parallel (multiple tool calls in one message)

### Self-Check Loop (after every change)
1. Implement → 2. Syntax/logic verification → 3. Architectural self-review → 4. Record in changelog

### Pacing
- After 5+ consecutive tasks, slow down deliberately
- After hitting a usage limit, do NOT auto-resume — wait for user confirmation
- Split large work across rounds

---

## 4. Scope Boundaries

- **No unauthorized scope expansion**: if you discover extra issues, list them under "next-round suggestions" — do not address them this round
- **Roadmap-approved-first**: any plan with 3+ tasks needs user sign-off (especially architecture work)
- **Report deviations immediately**: if the original plan turns out to be infeasible, stop and report — do not self-adjust silently

---

## 5. Document Naming and Location

Three naming patterns. Choose based on work type. Requirements are always the same: plan doc before changes, changelog after.

### Pattern A — Feature / Architecture work (multi-phase)

Use when: a feature or system change spans multiple implementation sessions.
Group all related docs under one topic directory so history is readable in one place.

```
docs/reviews/
  feat-<topic>/
    plan-YYYY-MM-DD.md             # exploration / architecture plan (before any implementation)
    phase1-YYYY-MM-DD.changelog.md # after phase 1 lands
    phase2-YYYY-MM-DD.changelog.md # after phase 2 lands
    ...
```

Topic name: short, kebab-case, describes the capability (e.g. `test-infra`, `ha-failover`, `event-driven`).

### Pattern B — Configuration-only maintenance

Use when: small, self-contained config hygiene (e.g. `.claude/settings.local.json`, `tox.ini` tweaks) that should not be conflated with the system roadmap.

```
docs/reviews/
  claude-config-<topic>-YYYY-MM-DD.review.md
  claude-config-<topic>-YYYY-MM-DD.changelog.md
```

### Pattern C — Legacy (rounds 1–9, read-only)

Round-numbered files in `docs/reviews/` from before 2026-04-16. Do not create new files in this pattern. Reference them for history; do not rename them.

```
docs/reviews/
  claude-review-round-N-YYYY-MM-DD.md   # legacy plan
  round-N-change-log-YYYY-MM-DD.md      # legacy changelog
  review-iteration-charter.md           # overall rules
```

**Decision rule**: if the work has a topic name and will produce more than one file over time → Pattern A. If it is config hygiene → Pattern B. Never create new Pattern C files.

---

## 6. Feedback Consolidation Loop (CLAUDE.md self-evolution)

**Every round must run these 4 steps before closing:**

### Step 1 — Extract feedback patterns from this round
Watch for these signals:
- User **corrections** ("no", "stop", "wrong")
- User **additional asks** ("also", "besides", "and")
- User **clarifying hidden intent** ("actually what I want is", "what I mean is")
- User **questioning direction** ("is it enough?", "complete?", "what's missing?")

### Step 2 — Classify into consolidable rules
For each piece of feedback, ask:
- Is it a **one-off** or a **recurring pattern**?
- If recurring, which section of CLAUDE.md should it live in?
- Does an existing rule already cover it? If yes, the issue is non-compliance — reinforce self-check; if no, add a new rule.

### Step 3 — Update CLAUDE.md and record in the change log
- New rules go directly into the relevant section of CLAUDE.md
- Add a "CLAUDE.md updates (this round)" subsection at the end of the change log
- The first thing every new session does is re-read CLAUDE.md

**"Noticing but not consolidating" is forbidden** — the user already paid the conversation cost to raise the issue; failing to consolidate means forcing them to pay it again.

### Step 4 — Present Next Steps to the user
Every round must end with an explicit, user-facing **Next Steps** block that answers:
- **Immediately doable** (ordered by priority, with owner: user vs Claude)
- **Blocked** (authorization needed, external dependency, decision pending)
- **Deferrable / removable** from backlog

Format: a short list (3-6 items). Mirror the same block into the change log's "Follow-Up / Next Steps" section so it persists into memory for the next session.

**"Silent backlog" is forbidden** — users must not have to ask "what's next?" after a round closes. If the user has to prompt for it, that is a defect in this step.

---

## 7. Known Feedback Rules (time-ordered accumulation)

> Rules distilled from past sessions. Numbering accumulates — do not delete old rules (unless replaced by a new rule, and note the replacement here).

- **R1 (2026-04-14)**: Plan-first; no implementation until the plan is approved. Source: after Round 5, user requested retroactive changelog.
- **R2 (2026-04-14)**: Do not conflate architecture and engineering levels. Source: Round 5 — user pointed out the "multi-server management control system" perspective did not match my engineering-only deliverables.
- **R3 (2026-04-14)**: Roadmap-approved-first for large work. Source: Round 5 — I planned 14 tasks unilaterally without roadmap-level user confirmation.
- **R4 (2026-04-14)**: Clarify system type / boundaries / NFR before starting. Source: Round 5 — initially read as "template", actual intent was "management control system".
- **R5 (2026-04-14)**: CLAUDE.md self-evolves every round; feedback must be consolidated. Source: user explicitly asked "extract conversation feedback to improve CLAUDE.md".
- **R6 (2026-04-14)**: Announce cost and limits up front. Source: the previous round hit the 5-hour limit and reacted only after the fact.
- **R7 (2026-04-14)**: Local operations with no destructive impact (start/stop containers, create/destroy docker instances, read-only verification, local port binding) do NOT need per-action approval — execute directly and log the action. Host budget is 8c16g; use resources freely. **Still require approval**: host-config changes, installing system packages, firewall/network rule changes, outbound network requests, any destructive cleanup (`rm -rf`, `docker volume rm`, `docker system prune`, `docker compose down -v`), anything involving keys/certs landing on disk. Source: user explicitly authorized Round 7 autonomous verification.
- **R8 (2026-04-14)**: Every round closes with an explicit **Next Steps** block for the user (immediately doable / blocked / deferrable). See §6 Step 4. Source: after refactor-i18n-b the user asked "接下来该做什么，为什么不显示" — a silent backlog forced the user to prompt; this rule eliminates that cost.
- **R9 (2026-04-14)**: **Roadmap auto-continuation.** When a multi-phase plan has been pre-approved (e.g., layered i18n a/b/c, or a roadmap with N ordered phases) and phase N has landed, phase N+1 must continue in the SAME response — do not stop and wait for the user to say "next". Exceptions that DO require a fresh pause: (a) the next phase crosses an authorization boundary not covered by the original approval; (b) the next phase is architecture-level and the approval only covered engineering-level phases; (c) the user has explicitly paused the roadmap ("暂且归档"). When in doubt whether authorization still covers the next phase, state the reasoning and ask — do not stop silently. Source: after refactor-i18n-b landed, I stopped instead of continuing to i18n-c even though the user had pre-approved the layered plan; user pointed out "做完了一个，就没有下文了".
- **R10 (2026-04-15)**: When modifying repo configuration files (e.g. `.claude/settings.local.json`, `tox.ini`, CI config), explicitly verify the change is appropriate for the intent, does not conflict with existing rules/allow entries, and is the simplest improvement that reduces future maintenance. Source: user requested that config edits include a suitability/conflict/improvement check.
- **R11 (2026-04-15)**: **Do not append on approval — refactor globally.** When a new permission, allow-entry, or rule is being added to any config/instruction file (`.claude/settings.local.json`, `tox.ini`, CI configs, and `CLAUDE.md` itself), do NOT simply append the new entry at the bottom. Instead: (a) read the whole file, (b) identify redundant / outdated / conflicting / malformed entries, (c) land a single coherent edit that both introduces the new capability and improves the file's overall structure (dedup, grouping, sorting, removing dead entries, consolidating wildcards). Why: ad-hoc appending accumulates cruft and drifts the file away from its design; global review keeps it maintainable. How to apply: on each approval request — local permission, lint rule, CI step, CLAUDE.md rule — treat it as a whole-file editing opportunity, not a one-line insert. Source: user reinforced 2026-04-15 — "对于后续需要请求新的 approve，如果同意，不要直接在里面添加新的，而是从全局考虑如何改进这个文件。对于其他配置文件，以及 claude.md 也适用".
- **R12 (2026-04-16)**: **Topic-first document naming.** Round-numbered filenames (`round-N-...`) scatter related docs across unrelated files and make feature history unreadable. New work must use Pattern A (`feat-<topic>/` directory) or Pattern B (`claude-config-<topic>-...`) from §5. Round numbers are retired from filenames; they remain valid as conversational reference only. Why: a multi-phase feature (e.g. test-infra) spanning 4 implementation sessions should produce 5 files all inside `feat-test-infra/`, not 5 files named after arbitrary round numbers. How to apply: when starting any new work, pick the naming pattern from §5 before creating any file. Source: user 2026-04-16 — "当前同一个task，要分好几个round，这样不利于查看历史修改内容".

---

## 8. Project Background

**Project name**: Ansispire (renamed 2026-04-16 from `ansible-demo`).

The **actual positioning** (clarified 2026-04-14):

> **Ansispire** is an **Ansible-based multi-server management control system** — not a generic development template.

Implications:
- Not just "a set of roles", but a full system with a **control plane + data plane**
- Must consider: controller HA, RBAC, audit, observability, event-driven automation, multi-tenancy, DR, CI/CD integration, service catalog, etc.
- Educational value is preserved, but **architectural depth takes priority over surface coverage**.

Full rules: `docs/reviews/review-iteration-charter.md`
