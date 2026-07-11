# Architecture Diagrams (PlantUML source)

Canonical, version-controlled diagrams of the Ansispire / Saberu system. Source is
PlantUML (`.puml`) so diffs are reviewable and diagrams travel with the code.
Design truth remains [`ARCHITECTURE.md`](../../ARCHITECTURE.md); these render it.

> **Two views** — pick the one you need:
> - **This directory = TARGET (as-designed)**: the full intended architecture,
>   including deferred/planned pieces (cf-worker Access Layer, DB-failover, etc.).
> - **[`current-state/`](current-state/) = AS-BUILT**: only what is proven working
>   on real machines today. Use this to see "what actually runs now."

| File | Kind | Shows |
|---|---|---|
| [`01-system-components.puml`](01-system-components.puml) | Component / collaboration | All components across the Control / Access / Data / Audit-Reaction planes, who talks to whom, and the responsibility split (control vs data). |
| [`02-vps-lifecycle-sequence.puml`](02-vps-lifecycle-sequence.puml) | Sequence | Processing order + data flow of the Saberu takeover loop: **VPS Onboard → SSH cutover → managed-channel re-audit (`changed=0`)**, incl. where the Key Store key is reused and where the managed validation happens. |
| [`03-audit-selfheal-dataflow.puml`](03-audit-selfheal-dataflow.puml) | Activity / data flow | The audit + self-healing loop: Semaphore events → `relay.py` → `sink.py` → `events.jsonl` → `reactor.py` (rules match / cooldown / Bearer) → remediation template. |

## Render

These are **source files** — render them with your PlantUML:

- **IDE**: open a `.puml` in VS Code (PlantUML extension) / JetBrains and preview.
- **CLI** (needs Java + plantuml.jar):
  ```bash
  plantuml docs/architecture/*.puml            # → PNG next to each source
  plantuml -tsvg docs/architecture/*.puml      # → SVG
  ```
- **Server**: point a local PlantUML server at this directory.

> Note: rendered images (`*.png` / `*.svg`) are intentionally **not** committed —
> the `.puml` source is the reviewable artifact. Render locally as needed.

## Keeping them true

Update the relevant `.puml` in the **same round** as a change that alters a
component boundary, a data-flow edge, or the lifecycle order (CLAUDE.md §0 Sync
Guard — treat these like `ARCHITECTURE.md`). Legends note the two invariants:
strict control/data decoupling, and the vault-free template-binds-ANSIBLE_CONFIG rule.
