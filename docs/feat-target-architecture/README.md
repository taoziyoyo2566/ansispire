# feat/target-architecture — Saberu Semaphore-native VPS Takeover

The deliverable hub for what this branch implements: **standardize / harden / manage
personal VPS through Semaphore** (Inventory + Key Store + Task API + UI as the near-term
control plane), instead of the retired local `vps_manager` surface.

## Start here

| I want to… | Go to |
|---|---|
| **operate it** — take a VPS from bootstrap → managed → audited | **[`operator-guide.md`](operator-guide.md)** ← step by step |
| see how it fits together | [`../architecture/`](../architecture/) — the system architecture ([target](../architecture/) vs [as-built](../architecture/as-built/)) |
| know why/what landed (evidence) | [`../reviews/feat-target-architecture/`](../reviews/feat-target-architecture/) — plans + `round10`–`round12` changelogs |
| the verification spec | `docs/reference/test-specs/vps-onboard-managed-audit-e2e.md` |

## Status (as of 2026-07-12)

| Piece | State |
|---|---|
| Control plane (Semaphore) + `bootstrap.yml` + Key Store + envs + `VPS Audit`/`VPS Onboard` | ✅ live |
| **VPS Audit** (read-only health) | ✅ real-VPS validated (Ubuntu 24 / Rocky 9 / Debian 13) |
| **VPS Onboard** → managed cutover → re-audit `changed=0` | ✅ **2/3 real-VPS validated** (u24 + d13) |
| `make controller-vps-smoke` (managed audit idempotency) | ✅ live PASS |
| RHEL full onboard (r9) | ~ blocked on that VPS's EPEL mirror reachability (infra, not code) |
| cf-worker Access Layer (Wizard/REST) | ⊘ built + probe-tested, **deferred** — not the current main line |
| DB-failover self-heal rule | ▱ placeholder (`enabled=false`, TASK-008) |
| Offboard / revert | backlog (TASK-010) |

Legend: ✅ done/validated · ~ partial/blocked · ⊘ deferred · ▱ placeholder.

## How this dir relates to `docs/reviews/feat-target-architecture/`

- **Here** = the *product* of the branch — how it works and how to run it (stable,
  reader-facing: operator guide + diagrams).
- **`docs/reviews/feat-target-architecture/`** = the *process* — dated plans,
  round changelogs, decisions, design notes (append-only history).
