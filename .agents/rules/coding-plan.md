# Coding Task Plan

Use this for coding-related implementation tasks before editing code or executable configuration.
This rule does not apply to edits whose primary purpose is writing or updating agent rules, governance rules, plans, or review notes.

## Pre-plan investigation

Before writing the plan, investigate enough to avoid choosing the wrong direction. Do at least two evidence passes:

- **Direction pass**: current project architecture, active branch/topic, TODO/review docs, ownership boundaries, and whether the task belongs here.
- **Implementation pass**: current code shape, existing patterns, framework/tool best practice, and whether the proposed change would extend an anti-pattern.

At minimum:

1. Read the current repo truth for the touched surface:
   - `ARCHITECTURE.md`
   - relevant `docs/reference/feature-map/*.md`
   - relevant `docs/governance/*.md`
   - active plan / changelog under `docs/reviews/`, if one exists
   - current implementation
2. Check whether the requested change fits the project's current direction, branch topic, and ownership boundaries.
3. Check whether the implementation would layer onto an existing anti-pattern; if yes, surface that before planning the patch.
4. Check whether the framework/tool already has a native or recommended approach.
   Use project usage first, then official docs or external references when the answer depends on current framework behavior or best practice.
5. Check `.agents/rules/codex-capabilities.md` for a better execution method before defaulting to manual/basic implementation.
6. If the change creates, moves, or consumes secret material, read `.agents/rules/secrets-handling.md` and follow its placement conventions.
7. If a plan prerequisite rests on an environment capability claim (tool present, daemon up, credentials), probe it per `.agents/rules/environment-truth.md` — do not copy the claim from memory or older docs.
8. Record any uncertainty, blocked prerequisite, or direction risk before proposing edits.

Do not treat the user's initial wording as proof that the requested direction is correct.

## Plan form

- Small / narrow coding tasks may use an inline plan in the response.
- Larger, architectural, cross-surface, or multi-step coding tasks need a persistent plan under `docs/reviews/<kind>-<topic>/plan-<slug>-YYYY-MM-DD.md` before implementation (naming per `.agents/rules/file-naming.md`, structure per `.agents/rules/plan-structure.md`).
- If a persistent plan already exists, update or reference it instead of creating a parallel plan.

## Plan header

The plan must include:

- **Goal**: the concrete outcome the task is meant to achieve.
- **Scope**: files, components, and behavior included in this task.
- **Out of scope**: related work intentionally excluded.
- **Prerequisites**: branch state, existing docs/plans, tools, permissions, or runtime assumptions needed before implementation.
- **Capability fit**: Codex/tooling capabilities to use for efficiency or accuracy, or why none apply.
- **Expected effect**: what should be observably different when the task is done.
- **Acceptance checks**: how to compare final results against the original goal.

## Plan body

The plan body must include:

- **Implementation policy**: chosen approach and why it matches current project direction.
- **Risks / cautions**: conflicts, migrations, compatibility, security, or rollback concerns.
- **Specific modifications**: concrete files or surfaces expected to change.
- **Verification**: tests, linters, syntax checks, command checks, or manual inspection needed for this task.
- **Follow-up handling**: what becomes next-step, blocked, or deferrable if it does not fit this task.

## Execution discipline

- Use the plan as the baseline for judging completion.
- If investigation proves the plan direction wrong, stop and revise the plan before editing.
- If implementation must deviate materially from the plan, report the deviation and update the plan or changelog evidence.
- At closeout, compare the final diff and verification results against the plan's goal, expected effect, and acceptance checks.
