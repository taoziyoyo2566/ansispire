# Control Plane

This directory is the landing point for the "multi-server management control system" control plane in this project.
Currently it only ships a minimal Semaphore implementation; later rounds will introduce AWX, RBAC, audit, EDA, and more.

> Chinese reference snapshot: `../docs/reference-cn/snapshot-2026-04-14/controller/README.zh.md`

---

## Why a Control Plane?

Without a control plane, Ansible is "scripts + SSH":
- No audit of who triggered what on which machine
- Credentials scattered across each person's `.vault_pass`
- No way to wire into event-driven flows (alert → self-healing)
- No unified job history or scheduling

With a control plane:
- Jobs are centrally scheduled, recorded, and traceable
- Credentials / vault keys are centrally managed and not distributed to people
- REST API / Webhook is exposed for CI, EDA, and upstream orchestration
- RBAC can grant separate permissions on project / template / inventory

---

## Controller Comparison

| Dimension | **Semaphore** (default here) | AWX | AAP (commercial) |
|-----------|-----------------------------|-----|------------------|
| Deployment | One Docker Compose command | Only k3s/k8s + Operator | Only k8s + Operator |
| Minimum resources | ~200 MB RAM | 4-6 GB RAM | 8+ GB RAM |
| License | MIT | Apache 2.0 | Commercial subscription |
| Feature coverage | project / inventory / template / schedule / job history / API | Same + EDA + workflow + constructed inventory | AWX + enterprise support / certification / auth |
| Upgrade cost | Independent ecosystem; migrating to AWX requires rebuilding resource definitions | AWX ↔ AAP share lineage; data migrates smoothly | — |
| Fit for this project | **Learning / low-spec machines** — first choice | Advanced / closer to production | Enterprise procurement |

Under this project's 1 GB memory budget, Semaphore is the only reasonable choice.

---

## Directory Structure

```
controller/
├── README.md              # This file (control-plane overview)
└── semaphore/             # Minimal Semaphore implementation
    ├── docker-compose.yml # Service definition
    ├── .env.example       # Environment variable template
    ├── bootstrap.yml      # First-run API initialization
    └── README.md          # Semaphore usage doc
```

Planned future directories (not yet created):
```
controller/
├── awx/                   # Round 10+: comparative teaching with AWX on k3s
├── rbac/                  # Round 8: permission model examples
└── eda/                   # Round 10: Event-Driven Ansible integration
```

---

## Quick Start

```bash
# From the repository root
make controller-up           # Start Semaphore
make controller-logs         # Follow logs
# Open http://localhost:3000 in a browser
make controller-down         # Stop (data preserved)
```

See [`semaphore/README.md`](./semaphore/README.md) for detailed steps.

---

## Upgrade Path

### Short term (within this project)
- **Round 8**: Define RBAC examples in Semaphore (User / Team / Project permission)
- **Round 9**: Audit log integration (Semaphore webhook → this repo's `extensions/audit/`)
- **Round 10**: Wire in `ansible-rulebook`; use Semaphore templates as EDA actions

### Mid term (needs extra resources)
- **Round 11**: Minimal Prometheus + Grafana stack (separate docker-compose) monitoring Semaphore and managed hosts
- **Round 12**: Optionally introduce AWX on k3s for comparative teaching (needs 4-6 GB RAM; user decides whether to enable)

### Long term (beyond this project)
- For production, use AAP or AWX directly (out of scope for this project)

---

## Design Principles

1. **Control plane / data plane decoupled**: `controller/` is independent of `roles/` and `playbooks/`; it can start and stop on its own
2. **Repo mounted read-only**: the control plane does not modify code, only consumes the repo; code changes go through the git workflow
3. **Zero-breakage path to heavier solutions**: the inventory / playbook structure used in this round can be pulled into an AWX project as-is in the future
4. **Teaching readability > production completeness**: the goal is to help learners understand control-plane concepts, not to replace a production platform

---

## References

- [Semaphore documentation](https://docs.semaphoreui.com/)
- [Semaphore REST API](https://docs.semaphoreui.com/administration-guide/api/)
- [AWX on GitHub](https://github.com/ansible/awx)
- Round 6 architecture plan: `../docs/reviews/claude-review-round-6-2026-04-14.md`
- Round 7 implementation plan: `../docs/reviews/claude-review-round-7-2026-04-14.md`
