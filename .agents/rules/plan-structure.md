# Plan Structure Rules

Applies only to genuine approval-gated [L2] direction plans, execution plans,
and detail addenda in the topic evidence directory resolved by
`.agents/rules/file-naming.md`. New topics use `docs/workstreams/`; an
unmigrated legacy topic remains wholly under `docs/reviews/`.

Historical plans retain their filenames in either root and are not required to
adopt this section shape unless their approval scope is being materially
replaced.

Do not use this structure for an investigation/probe, stable design, decision
record, review report, runbook, task ledger, or round changelog. Route those
artifacts with `.agents/rules/file-naming.md`; a topic-owned investigation stays
inside the same functional bundle. A document that neither requests approval
nor blocks a named implementation scope is not a plan.

"Materially rewritten" means scope, implementation approach, or verification criteria changed.
Wording-only edits do not trigger this rule.

Also read:

- `.agents/rules/authorization.md` for the distinction between plan approval,
  task authorization, Git/external actions, and live-operation confirmation.
- `.agents/rules/plan-hierarchy.md` when a plan has a parent, child, or addendum
  relationship.
- `.agents/rules/evidence-backed-planning.md` when external knowledge, current
  best practice, third-party APIs/tools, security guidance, or live
  infrastructure behavior influences the plan.
- `.agents/rules/execution-reflection.md` when the plan will later be executed
  against live infrastructure or external systems.

A reader who has never seen the codebase should be able to understand:
- what broke or is missing
- why it matters now
- what will change
- how success is verified
- what follow-up work is unlocked

---

## Required sections (in order)

### §0 Status block (frontmatter)

A metadata block at the very top, before any prose:

```
> **Status**: DRAFT | PENDING_APPROVAL | APPROVED | COMPLETED | SUPERSEDED
> **Created**: YYYY-MM-DD
> **Branch**: <kind>/<topic>
> **Classification**: [L2] Architecture
> **Plan type**: Direction plan | Execution plan | Detail addendum
> **Approval scope**: direction | implementation approach | named details
> **Blocks implementation**: yes | no | only <named phases/details>
> **Supersedes**: <path to older plan if this replaces one, else omit>
```

`Plan type`, `Approval scope`, and `Blocks implementation` are mandatory for
every new approval artifact. Add relationship metadata when applicable:

```
> **Parent plan**: <path>
> **Does not supersede**: <scope or parent>
```

Status lifecycle:

- `DRAFT`: authoring in progress; not yet presented for approval.
- `PENDING_APPROVAL`: presented to the user, waiting explicit approval.
- `APPROVED`: the declared `Approval scope` is explicitly approved. Work may
  begin only when `Blocks implementation`, parent/child dependencies, phase
  gates, task authorization, and any separate Git/external/live authorization
  allow that work. Add
  `> **Approved**: YYYY-MM-DD` on the next line so future readers can tell which
  version was approved.
- `COMPLETED`: all phases passed and post-completion checklist done; add `> **Completed**: YYYY-MM-DD` on the next line.
- `SUPERSEDED`: replaced by a newer plan; include a link to the replacement.

Allowed transitions:

| From | To | Trigger |
|---|---|---|
| DRAFT | PENDING_APPROVAL | Plan is presented for approval |
| PENDING_APPROVAL | DRAFT | User requests changes before approving |
| PENDING_APPROVAL | APPROVED | User explicitly confirms approval; record `> **Approved**: YYYY-MM-DD` |
| APPROVED | COMPLETED | All phases passed and §7 checklist done |
| APPROVED | APPROVED | Minor correction that does not change scope, approach, or verification criteria; add `> **Updated**: YYYY-MM-DD — <one-line summary>` immediately after the status block. If the correction changes any of those three, create a new plan instead. |
| DRAFT | SUPERSEDED | Newer plan replaces this draft before approval |
| COMPLETED | COMPLETED | Metadata-only correction (e.g. wrong completion date, broken link); add `> **Updated**: YYYY-MM-DD — <one-line summary>` immediately after the Completed line. If the correction touches scope, steps, or verification criteria the plan was already executed under, create a new plan instead. |
| PENDING_APPROVAL / APPROVED / COMPLETED | SUPERSEDED | Newer plan replaces this plan; link to replacement |

---

### §1 Why this plan exists

Answer three questions in plain language:

1. **What is wrong or missing?** - observable symptom or gap.
2. **Why does it matter?** - consequence if unresolved.
3. **What triggered this plan now?** - concrete event or decision.

Keep this concise: if someone reads only §1 they should still know whether this plan is relevant.

---

### §2 Current state

A factual snapshot of what exists now, before changes:

- code / config currently in place
- confirmed working behavior
- confirmed broken or missing behavior
- constraints (versions, env requirements, blockers)

Distinguish clearly between **confirmed facts** and **assumptions**. If not runtime-verified, say so.
If a claim depends on external knowledge, classify it per
`.agents/rules/evidence-backed-planning.md` as a verified external fact,
assumption, research item, runtime probe, or operator decision.

---

### §3 Scope

Two explicit lists:

- **In scope** - what this plan changes or delivers.
- **Out of scope** - what this plan explicitly does not touch.

If open decisions must be resolved before implementation starts, list each with owner and trigger/deadline.
If unknowns are intentionally deferred to implementation, name the phase/gate
where each unknown will be closed.

---

### §4 Implementation plan

Use either format below. Both are valid.

Format A:

```
#### Phase N - <name>

**Goal**: one sentence.
**Pre-condition**: what must be true before this phase starts.
**Steps**: numbered, actionable, specific enough to hand to another person.
**Gate**: explicit user confirmation or automated check required before proceeding.
**Deliverables**: files or artifacts produced by this phase.
```

Format B:

```
#### WU-N - <name>

**Goal**: one sentence.
**Pre-condition**: what must be true before this work unit starts.
**Steps**: numbered, actionable, specific enough to hand to another person.
**Gate**: explicit user confirmation or automated check required before proceeding.
**Deliverables**: files or artifacts produced by this work unit.
```

Rules:

- An [L2] plan must include at least one pre-implementation gate that requires explicit user approval.
- Steps must name specific files, commands, or APIs; avoid vague verbs without object.
- If a phase depends on a runtime probe whose outcome is unknown, the phase must include an explicit decision table: one row per possible outcome, each row naming the next action. Example:

  | Probe result | Next action |
  |---|---|
  | API returns expected field | proceed to Phase N+1 |
  | Field missing | update IVG with finding, reassess design before continuing |

- Phases/WUs should be independently committable.
- Phases that execute live infrastructure changes must include or reference the
  live infrastructure gate in `.agents/rules/execution-reflection.md`.

---

### §5 Verification

Define done criteria per phase/WU:

| Phase/WU | Verification method | Pass condition | Evidence artifact |
|---|---|---|---|
| 1 | command or manual check | exact expected output or state | log, screenshot, changelog link |
| 2 | ... | ... | ... |

- Prefer commands over manual UI checks when possible.
- If live environment is required but may be unavailable, provide fallback verification.
- "It should work" is not a verification method.
- Evidence artifact must be committed to the repo before the phase is considered closed, recorded in `round<N>-YYYY-MM-DD.changelog.md`. Sensitive output (real IPs, hostnames, credentials-adjacent strings) must be redacted to placeholders before committing — a sanitized excerpt with a note "sensitive fields redacted" is sufficient.
- Verification claims that rely on tool output must name the observable source:
  command output, API response, task id/status, Ansible recap, log path, or
  screenshot.

---

### §6 Risks and fallbacks

| Risk | Likelihood | Impact | Mitigation | Fallback |
|---|---|---|---|---|
| ... | low/med/high | low/med/high | preventive action | what to do if risk materializes |

List only risks that could materially change implementation approach.

---

### §7 Post-completion checklist

After all phases/WUs pass, explicitly list:

- docs to update (specific files + what changes)
- investigations to close (if any IVG status changes)
- `TODO.md` updates
- changelog to write (`round<N>-YYYY-MM-DD.changelog.md`)
- advance this plan's `§0 Status` to `COMPLETED` and add `> **Completed**: YYYY-MM-DD` on the next line
- next work unlocked by this plan
- reflection outcome if implementation contradicted the plan or exposed a rules
  gap, per `.agents/rules/execution-reflection.md`

---

## Anti-patterns to avoid

- **Status block missing or permanently DRAFT** - plan cannot be executed safely.
- **`PENDING_APPROVAL` defined but never used** - approval state becomes ambiguous.
- **§2 mixes facts and assumptions without labeling** - future readers treat assumptions as truth.
- **No explicit out-of-scope list** - scope creep is likely.
- **No gate before implementation** - violates [L2] approval discipline.
- **Verification says only "check UI"** without concrete expected signal.
- **Risks section empty** - no failure-mode thinking recorded.
- **Phase with unknown runtime outcome has no decision table** - executor is blocked with no guidance on what to do next.
- **Plan completed but §0 still shows APPROVED** - future readers cannot tell if the plan was ever executed.
- **PENDING_APPROVAL revised in place without reverting to DRAFT** - approval state becomes ambiguous; user may approve a version they did not review.
- **Contradicting a previously closed decision without declaring it** - if the plan reverses a decision recorded in a design doc or TODO, it must name that decision and state that it supersedes it; silent reversal leaves two conflicting truths.
- **Flat approval semantics** - treating a pending child/detail plan as if it
  invalidates an approved parent direction, or treating an approved direction as
  if it authorizes every live/destructive run.
- **Unverified external knowledge** - encoding current third-party behavior,
  security practice, or API details from memory when they should be checked
  against primary sources.
- **Hidden unknowns** - leaving "implementation will investigate later" as prose
  without naming the close phase and fallback if the investigation contradicts
  the plan.
- **Plan-shaped artifact inflation** - creating another plan for a probe,
  runbook, stable contract, review finding, or already-approved phase instead of
  routing that artifact to its functional owner or stable canonical location.

---

## Naming

Resolve the topic evidence directory with `.agents/rules/file-naming.md` and use
the prefix matching the plan type for newly created files:

```
direction-<slug>-YYYY-MM-DD.md
execution-<slug>-YYYY-MM-DD.md
addendum-<slug>-YYYY-MM-DD.md
```

`slug` describes what the plan does (not which branch it lives on). Historical
`plan-*.md` filenames remain valid and should not be renamed only for
consistency.
