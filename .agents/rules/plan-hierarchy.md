# Plan Hierarchy and Approval Scope

Use this when a topic has more than one plan, when an approved direction gets a
more detailed execution plan, or when a TODO entry links both approved and
pending plan artifacts.

## Core rule

Plan approval is scoped. Do not flatten every plan into a single global
approved/pending state.

A parent plan can be approved for direction while a child plan is still pending
for execution details. That is valid and not a conflict by itself.

## Plan types

Use the narrowest type that matches the document:

| Type | Purpose | Typical approval scope |
|---|---|---|
| Direction plan | Product/architecture direction, boundaries, major decisions | direction |
| Execution plan | Work breakdown, phase gates, verification, closeout | implementation approach |
| Detail addendum | Additional task granularity for an approved parent plan | named details only |
| Decision record | One decision and its rationale | decision only |
| Runbook | Exact operator steps for a live or repeatable operation | operation procedure |

## Status metadata

When a plan depends on another plan, add metadata near the status block:

```text
> **Plan type**: Direction plan | Execution plan | Detail addendum | Decision record | Runbook
> **Approval scope**: direction | implementation approach | named details | live operation | closeout
> **Parent plan**: <path>
> **Blocks implementation**: yes | no | only <named phases/details>
```

Rules:

- `PENDING_APPROVAL` child/detail plans do not invalidate an `APPROVED` parent.
- A pending child blocks only the scope named in `Blocks implementation`.
- If `Blocks implementation` is omitted, treat it as `yes` only for that
  document's own details, not for the parent direction.
- A child plan that changes parent scope, approach, or verification must say so
  explicitly and either supersede the parent or request a parent-plan amendment.
- A child plan that only decomposes an approved parent should say
  `Does not supersede`.

## TODO representation

When linking multiple plan layers in `TODO.md`, express both scope and state:

```text
Direction: APPROVED (<parent-plan>)
Execution details: PENDING_APPROVAL (<child-plan>)
Current action: review detail plan before Phase N
```

Avoid writing a single status that makes the whole workstream look pending when
only the execution details are pending.

## Conflict handling

If two plan layers disagree:

1. Identify whether the conflict is direction, implementation, verification, or
   wording.
2. Preserve the approved parent as the direction source unless the user approves
   a superseding plan.
3. Add a dated note or new follow-up plan instead of silently editing history.
4. Update `TODO.md` so future readers know which layer is authoritative.
