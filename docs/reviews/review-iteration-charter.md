# Review Iteration Charter

Date: 2026-04-09 (last updated 2026-04-14)
Applies to:
- All subsequent Round documents under `docs/reviews/`
- Continuing review and revision discussions between Codex / Claude and this repository

> Chinese reference snapshot: `docs/reference-cn/snapshot-2026-04-14/docs/reviews/review-iteration-charter.zh.md`

## Original Purpose

The original purpose of this repository is NOT "the most powerful, most comprehensive, most production-grade Ansible repo". It is:

1. A demo project suitable for learning and understanding Ansible.
2. Coverage of core features, common patterns, official recommended organization, and common community practice.
3. With educational value preserved, keep the default main path self-consistent, runnable, and verifiable.

In other words, the goal of subsequent iterations is:
- Improve educational correctness.
- Improve consistency and runnability of the default path.
- Reduce content that "looks like best practice but is broken or misleading".

It is NOT:
- Unbounded complexity in the name of "looking more production-grade".
- Sacrificing the default experience in the name of coverage.
- Turning the demo into an enterprise internal platform template without clear benefit.

## Review Priorities

Each round evaluates issues in this order:

1. Issues that fail outright.
2. Issues that mislead learners.
3. Default path inconsistent with documentation.
4. Incorrect security workflows.
5. Tooling / test chain not closed loop.
6. Low-priority optimizations, cosmetics, scalability.

## Platform Support Strategy

This repository is positioned as "a demo for learning Ansible", not a business project targeting a single Linux distribution.

Default rules:

1. Must NOT narrow platform support from "multi-distro learning scenarios" to a single distro or family without explicit user consent.
2. When code and support claims diverge, the preferred solution is NOT immediate deletion of a platform — propose a "support tiering" plan first.
3. Platform support must be expressed in 3 tiers to avoid conflating "referenceable", "adapted", and "tested".

Recommended tiering:

- **Tier 1**: Explicitly supported, continuously tested
  - At least one Debian-family platform
  - At least one RHEL-compatible platform
- **Tier 2**: Code skeleton / documentation exists but not yet in CI or Molecule
  - E.g. other Debian versions, extended AlmaLinux/Rocky versions
- **Tier 3**: For learning discussion only; default runnability not promised
  - E.g. minimal Linux, container-only images, distributions lacking Python / systemd

Default judgments:
- "Common enterprise platforms" should NOT be represented by Ubuntu/Debian alone.
- "Minimal Linux exists" does NOT imply it must be in the default main path.
- If a platform lacks testing, that is not a reason to delete it — it can be demoted to Tier 2 first.

## Fix-Conclusion Rules

Subsequent Round documents MUST NOT directly write "direction judgment correct" as "fixed".

Every issue must use one of these three status labels:

- Landed
- Partially landed
- Direction confirmed, not yet closed

Before labeling "Landed" the following FOUR conditions must all hold:

1. Code is modified.
2. Related documentation is synchronized.
3. Related support claims are synchronized.
4. No obvious self-consistency conflict.

If any one of the four is missing, "Landed" MUST NOT be claimed.

## Evidence Requirements

Before claiming an item is "fixed" or "support scope narrowed" in a round, minimal evidence cross-checking is required.

Check at least the following:

- Code implementation
- README / docs
- role meta / argument_specs
- preflight / runtime guard
- Test or verification path

Suggested as a short table:

| Item | Files checked | Conclusion |
|------|---------------|-----------|
| Platform support | ... | Synced / Not synced |
| Doc paths | ... | Synced / Not synced |
| EE/CI | ... | Self-consistent / Not |

## Mandatory Questions Before "Large Change" Directions

Before proposing a "large change" direction in any round, first answer:

1. Is this correcting an error, or redefining project scope?
2. If redefining scope, has explicit user authorization been obtained?
3. Does this change add clarity for "learning Ansible", or merely reduce maintenance cost?
4. Is there a gentler approach — e.g. "support tiering" instead of "delete support"?

## Fixed Boundaries

The default main path refers to:
- `README.md`
- `ansible.cfg`
- `requirements.yml`
- `inventory/production`
- `playbooks/site.yml`
- `playbooks/rolling_update.yml`
- `playbooks/vault_demo.yml`
- `roles/`
- `molecule/`
- `execution-environment.yml`
- `.github/workflows/ci.yml`

Educational extension examples refers to:
- `examples/`
- Custom plugin examples
- Demo files outside the default execution path

Default requirements:
- The default main path should be as runnable as possible.
- Educational extension examples may be more permissive but MUST be clearly labeled "example / non-default execution path".

## Mandatory Content at the Start of Every Round

The first section of every round document must state the following four items:

1. Original purpose
2. Scope of this round
3. Out of scope this round
4. Judgment criteria

Suggested template:

```md
## Original Purpose
This repository is for learning Ansible features and best practices; this round continues under "educational correctness, runnable default path, docs-implementation alignment".

## Scope of This Round
- ...

## Out of Scope
- ...

## Judgment Criteria
- Does it reduce misleading content?
- Does it make the default path more self-consistent?
- Does it introduce unnecessary complexity?
```

## Mandatory Questions at the End of Every Round

1. Is this round's modification closer to the original purpose?
2. Does it separate "educational examples" from "default path" more clearly?
3. Did it introduce new documentation drift?
4. Did it introduce new environmental dependencies?
5. Are there any unresolved prerequisite conflicts?

## Known High-Priority Open Items

- `roles/database/meta/argument_specs.yml` vs `roles/database/defaults/main.yml` required/default-value conflict
- Platform support claims in `roles/common/tasks/preflight.yml`, role meta, and README are not yet unified
- `README.md` has not synced `examples/advanced_patterns.yml`, new Molecule scenarios, CI, or EE changes
- `playbooks/rolling_update.yml` still hardcodes `lb01.example.com`
- `roles/common/templates/motd.j2` still depends on the project-root `filter_plugins/`
- `execution-environment.yml` is not yet fully self-consistent with actual dependency declarations

## Suggested Naming Conventions

Subsequent files should use:

- `codex-review-round-N-YYYY-MM-DD.md`
- `claude-review-round-N-YYYY-MM-DD.md`
- `round-N-change-log-YYYY-MM-DD.md`

---

## Mandatory Documentation Requirements (added 2026-04-14)

**Every round's changes must produce two file types — both required** (this rule is also written into the project-root `CLAUDE.md`):

### A. Plan / Review Document

Location: `docs/reviews/claude-review-round-N-YYYY-MM-DD.md`

Timing: Created **before or at the start of** changes (write the plan first, then execute).

Must contain:
1. Original purpose
2. Scope of this round
3. Out of scope
4. Judgment criteria
5. Architectural rationale for each change

### B. Change Log

Location: `docs/reviews/round-N-change-log-YYYY-MM-DD.md`

Timing: Created **after all changes are complete**.

Must contain:
- `Reference:` field linking to the corresponding plan doc
- Change manifest (table: file | change type | summary)
- Intent per change category
- What was explicitly NOT done (boundaries)
- Self-check results (syntax, consistency, critical-file presence)

### Landing Criteria

Before claiming a round is "done", ALL of the following must hold:
1. Code is modified and self-check passes
2. Plan doc created
3. Change log created, with bidirectional link to the plan doc
4. Self-check results in the change log contain no errors
