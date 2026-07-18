# Execution-Time Revalidation and Reflection

Use this when executing an approved plan, especially when a phase touches live
infrastructure, external systems, credentials, or third-party APIs.

Authorization semantics, including standing test-host authorization, are
defined in `.agents/rules/authorization.md`.

## Core rule

Do not execute a plan mechanically after reality contradicts it.

At the start of each substantial phase, re-check the facts that the phase relies
on. If implementation proves the plan wrong, stop, classify the mismatch, and
update the plan, changelog, or rules before continuing.

## Phase-start revalidation

Before starting a phase, check:

- repo state still matches the plan's file/path assumptions;
- external docs/API behavior still supports the planned action when that action
  depends on current third-party behavior;
- environment capabilities are fresh per `~/workspace/.agents/rules/environment-truth.md`;
- operator decisions or credentials required by the phase are available;
- live target scope is known.

## Contradiction handling

When reality contradicts the plan:

1. Stop the current phase before making further changes.
2. Classify the cause:
   - stale external knowledge;
   - repo changed since planning;
   - missing runtime probe;
   - missing operator decision;
   - plan ambiguity;
   - rules gap.
3. Record the contradiction in the round changelog or a dated plan note.
4. Update the plan or add a follow-up addendum if scope, approach, or
   verification changes.
5. If the cause is a rules gap, add a rules-improvement note or update the
   relevant `.agents/rules/*.md` file in the same round when practical.

## Live infrastructure gate

Before triggering a task that can mutate real infrastructure, record a final
go/no-go check:

| Field | Required content |
|---|---|
| Target scope | exact host(s), inventory/group, and expected count |
| Operation | exact playbook/template/API call to run |
| Credential path | which credential is used and where it is stored, without revealing the secret |
| Expected impact | users, SSH, firewall, packages, services, files |
| Fallback owner | who can recover via console/reinstall/manual access |
| Evidence | task id, command output, or log path to capture |
| Authorization | per-run confirmation, or the path and bounded fields of a valid standing test-host authorization |

This gate is separate from ordinary plan approval. A plan covers repeated
test-host runs only when it contains the complete standing-authorization block
required by `.agents/rules/authorization.md`; otherwise obtain explicit
confirmation for the run. Managed-fleet mutation remains per-run.

## External resource ledger

When a phase creates or mutates resources outside git, record them in the
changelog or operator runbook:

| Resource | Required fields |
|---|---|
| Semaphore inventory | name, id, type, credential id, owner project |
| Semaphore key | name, id, secret storage type, rotation owner |
| Semaphore template | name, id, playbook, inventory id, environment id |
| API token | owner, scope, creation method, revocation/expiry policy |
| VPS | provider label, redacted IP/hostname, purpose, cleanup policy |

Do not commit secret values. Record identifiers and lifecycle only.

## Manual UI change handling

Manual UI changes are acceptable when secrets or live operator actions require
them, but they need evidence:

- record what was changed and by whom/which role;
- record resource ids or sanitized screenshots/logs when useful;
- backfill to IaC when the value is non-secret and should be reproducible;
- if it cannot be backfilled, add a drift note and owner.

## Closeout reflection

Every substantial live or cross-system round should end with a short reflection:

| Question | Expected answer |
|---|---|
| Did any plan claim prove false? | no / yes with link |
| Was the cause a plan gap or rules gap? | classification |
| Did we update docs/rules/TODO accordingly? | link or explicit no |
| What should the next executor re-check? | concrete item |
