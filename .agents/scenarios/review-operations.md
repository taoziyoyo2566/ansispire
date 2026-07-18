# Scenario: Review Operations

Use this for deployment, infrastructure, remote-host, or external-state changes.

Review:

1. exact target scope, owner, prerequisites, and blast radius;
2. idempotency, ordering, partial failure, concurrency, and timeout behavior;
3. credential path and trust boundaries without exposing secrets;
4. observability and evidence that distinguishes success from partial success;
5. rollback/recovery steps and the owner who can execute them;
6. environment revalidation and the live go/no-go gate from
   `.agents/rules/execution-reflection.md`.

Ordinary plan approval does not authorize a live mutation. Verify either
per-run confirmation or a complete standing test-host authorization under
`.agents/rules/authorization.md`, and never treat a dry-run or syntax check as
live functional evidence. Managed-fleet mutation remains per-run.
