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

Decision records, investigations, review reports, runbooks, and round
changelogs are companion artifacts, not plan types:

| Artifact | Purpose | Route |
|---|---|---|
| Decision record | Preserve a bounded decision, authority, and rationale | `decision-<slug>-YYYY-MM-DD.md` in the topic evidence directory |
| Current design | State the accepted invariant now | owning stable architecture/domain/governance document |
| Investigation/probe | Test an unknown and preserve evidence | `investigation-<slug>.md` in the topic directory; global IVG only when cross-topic |
| Review report | Record findings against a bounded change | `review-<slug>-YYYY-MM-DD.md` in the topic evidence directory |
| Runbook | Provide repeatable operator steps and recovery | `docs/operations/` |
| Round changelog | Record what actually landed and passed | `round<N>-YYYY-MM-DD.changelog.md` |

Do not turn one of these artifacts into a child plan just to attach it to the
hierarchy. Link it using `Related plan` or from the relevant phase/evidence row.
When a decision affects current design, preserve the decision record and promote
the active conclusion to the stable document.

## Status metadata

Every new approval artifact includes `Plan type`, `Approval scope`, and
`Blocks implementation`. When it depends on another plan, also include
`Parent plan`:

```text
> **Plan type**: Direction plan | Execution plan | Detail addendum
> **Approval scope**: direction | implementation approach | named details
> **Parent plan**: <path>
> **Blocks implementation**: yes | no | only <named phases/details>
```

Rules:

- `PENDING_APPROVAL` child/detail plans do not invalidate an `APPROVED` parent.
- A pending child blocks only the scope named in `Blocks implementation`.
- For a historical plan that omits `Blocks implementation`, treat it as `yes`
  only for that document's own details, not for the parent direction.
- A child plan that changes parent scope, approach, or verification must say so
  explicitly and either supersede the parent or request a parent-plan amendment.
- A child plan that only decomposes an approved parent should say
  `Does not supersede`.
- A phase already covered by an approved plan does not need another plan unless
  it introduces a separately approvable scope, approach, or risk decision.
- Probe output stays with its owning function unless it is genuinely
  cross-topic. Accepted contracts and shared operator procedures should be
  linked from the plan and stored in their stable canonical locations.

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
3. Add a dated companion artifact, or a typed follow-up plan/addendum when the
   approval scope changes, instead of silently editing history.
4. Update `TODO.md` so future readers know which layer is authoritative.
