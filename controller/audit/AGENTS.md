# controller/audit/AGENTS.md

Use this file when touching `controller/audit/`.

- `../../.agents/project/architecture.md`
- `../../.agents/rules/boundaries.md`
- `../../.agents/rules/testing.md`
- `../../docs/reference/feature-map/audit-plane.md`
- `../../docs/reference/feature-map/eda-core.md`
- `relay.py`: event acquisition from Semaphore.
- `sink.py`: durable structured event intake.
- `reactor.py`: rules evaluation and remediation triggering.
- `test_rules_contract.py`: config contract guard for rules/template alignment.
- `e2e/run.sh`: whole-chain execution proof.
- Treat relay, sink, reactor, rules, and bootstrap template naming as one coupled surface.
- For rule or template-name changes, check contract tests before assuming runtime behavior is enough.
- For reactor behavior changes, consider unit, component, and e2e implications separately.
- Prefer explicit schema/contract validation over hidden naming conventions.
