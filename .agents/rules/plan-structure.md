# Plan Structure Rules

Applies to new or materially rewritten [L2] plan documents under `docs/reviews/`.
Historical plans are not required to be backfilled unless they are being edited.

"Materially rewritten" means scope, implementation approach, or verification criteria changed.
Wording-only edits do not trigger this rule.

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
> **Supersedes**: <path to older plan if this replaces one, else omit>
```

Status lifecycle:

- `DRAFT`: authoring in progress; not yet presented for approval.
- `PENDING_APPROVAL`: presented to the user, waiting explicit approval.
- `APPROVED`: explicitly approved; implementation may begin. Add `> **Approved**: YYYY-MM-DD` on the next line so future readers can tell which version was approved.
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

---

### §3 Scope

Two explicit lists:

- **In scope** - what this plan changes or delivers.
- **Out of scope** - what this plan explicitly does not touch.

If open decisions must be resolved before implementation starts, list each with owner and trigger/deadline.

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

---

## Naming

Follow `.agents/rules/file-naming.md`:

```
plan-<slug>-YYYY-MM-DD.md
```

`slug` describes what the plan does (not which branch it lives on).
