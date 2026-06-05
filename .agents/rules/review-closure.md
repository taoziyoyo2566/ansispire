# Review Closure

Use this for review or audit tasks, especially agent-governance audits.

## Must-Fix vs Optional

- `P0`
  - contradictory instructions that can route an agent to the wrong behavior
  - broken paths, impossible commands, or invalid references
  - branch / plan guidance that can cause work to land on the wrong topic branch

- `P1`
  - materially stale or misleading guidance
  - missing rule needed for the task to complete correctly
  - verification claims not backed by actual checks

- `P2`
  - clarity improvements
  - useful but non-blocking structure cleanup
  - future-useful additions not required by the current scope

## Closure Standard

A review is complete when all of the following are true:

1. The scope is frozen.
   - exact branch, files, and review question are named
2. No open `P0` or `P1` findings remain in scope.
3. Any remaining `P2` items are explicitly marked as:
   - optional refinement
   - future enhancement
   - out of scope
4. The appropriate verification for the touched surface has passed.
   - docs / governance only: path, command, and cross-reference checks; `git diff --check`
   - scripts touched: syntax check for the changed script
   - code touched: follow `docs/governance/testing-governance.md`
5. The close-out states:
   - what was fixed
   - what was deferred
   - why the audit is done now

## Stop Rules

- Do not open another edit loop for wording polish alone.
- Default cadence is:
  - one broad audit
  - one implementation pass
  - one targeted re-audit
- Go beyond that cadence only if:
  - scope changed
  - new evidence appeared
  - a previous assumption was proven wrong
- If two consecutive audit passes produce no new `P0` or `P1` findings, stop.
