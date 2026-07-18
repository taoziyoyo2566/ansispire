# Boundaries

## Editing boundaries

Repository-file authorization comes from `.agents/rules/authorization.md`.
A change/fix/implementation request permits the necessary in-scope workspace
edits without per-file confirmation; a review, audit, explanation, or diagnosis
is read-only unless remediation is also requested.

Before editing, answer:

1. What files are in scope?
2. Why is this change needed?
3. What is explicitly out of scope?

- Do not mix control-plane changes and role/data-plane changes casually.
- Do not change inventory model, deployment flow, or plugin ownership without checking:
  - `ARCHITECTURE.md`
  - `TODO.md`
  - relevant active workstream docs in `docs/workstreams/`, or the topic's
    unmigrated evidence in `docs/reviews/`
- Do not silently change operator workflows documented in `docs/operations/` or `docs/user-guide/` without syncing those docs.
- Do not treat an investigation document as an implementation mandate unless current plans or TODO entries still point to it.
- Preserve historical records in investigation files; pre-0.0.1 archived material lives in the upstream `ansispire` repository history.

## Execution boundaries (remote hosts)

Triggering a playbook or Semaphore task **mutates real machines** — treat the
controller API token as a destructive capability, not a read credential.

- Mutating runs against **throwaway / test hosts** require either per-run
  confirmation or a complete standing test-host authorization block as defined
  in `.agents/rules/authorization.md`; plan approval without that block is not
  live authorization. Keep provider console access as fallback.
- Mutating runs against **managed fleet inventory** require explicit per-run user
  confirmation until a standing fleet-authorization policy exists.
- Read-only runs (`--check`, `--syntax-check`, audit-style playbooks with no
  state change) follow normal verification rules.
- If a run's blast radius is unclear (which hosts match the pattern?), resolve
  the inventory match list first — `ansible-inventory --graph` or the Semaphore
  inventory blob — before triggering.
- For live infrastructure operations that can change SSH, firewall, users,
  packages, services, or provider resources, apply the final go/no-go gate in
  `.agents/rules/execution-reflection.md` even when the implementation plan is
  already approved.
