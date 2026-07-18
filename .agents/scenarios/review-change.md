# Scenario: Review Change

Use this as the review router and common protocol. Do not force every change
through one monolithic review checklist.

## Select One Primary Review Type

Classify by the change's dominant intent and acceptance criteria, not only its
file path or branch prefix:

- new or extended user/system behavior, including an architecture plan:
  `.agents/scenarios/review-feature.md`
- correction of an observed defect:
  `.agents/scenarios/review-bugfix.md`
- internal restructuring intended to preserve behavior:
  `.agents/scenarios/review-refactor.md`
- deployment, infrastructure, remote-host, or external-state change:
  `.agents/scenarios/review-operations.md`
- dependency, build, CI, test-infrastructure, or tooling maintenance:
  `.agents/scenarios/review-maintenance.md`
- reader-facing documentation, artifact-lifecycle changes, or agent/governance
  behavior:
  `.agents/scenarios/review-docs-governance.md`

Choose exactly one primary type. Add a secondary scenario only when the diff has
a separately material second intent; do not run every checklist by default. If
the request is ambiguous, infer intent from the active plan, TODO, branch, and
diff before asking the user.

For a plan, RFC, or architecture proposal, choose the primary type from the
behavior it proposes: feature, bugfix, refactor, operations, or maintenance.
Use docs/governance as the primary type only when the reviewed outcome is the
documentation, artifact lifecycle, or governance behavior itself. Every plan
review still performs the bounded artifact checks for location, approval
metadata, links, history, and authority from
`.agents/scenarios/review-docs-governance.md`; that check does not create a
second primary type.

Then apply only the relevant cross-cutting lenses from
`.agents/rules/review-lenses.md`.

## Common Review Protocol

1. Freeze the comparison base and changed scope.
2. Identify the intended outcome, explicit non-goals, and acceptance evidence.
3. Run the selected primary scenario before line-by-line implementation review.
4. Review the actual diff, prioritizing correctness, regressions, missing
   verification, and maintainability in that order.
5. Classify findings with `.agents/rules/review-closure.md`.

## Evidence And Output

- use current repo truth as the baseline, not generic preference alone
- use the relevant feature map and governance docs; if the task is about AI collaboration itself, also use `.agents/project/agent-strategy.md`
- call out open assumptions explicitly
- lead with the primary-type assessment, then findings ordered by severity with file/line evidence, then verification and residual risk
- distinguish confirmed defects from design questions and optional improvements
- for review-only work, stop when the review-report completion standard is met
- when remediation was authorized, use the remediation closure standard and do
  not keep editing for polish alone
- keep summaries brief after the findings
