# Stage 1 Closeout — Ansible Multi-Server Management Control System

**Date**: 2026-04-15
**Scope**: Rounds 1–9 consolidated retrospective.
**Purpose**: Mark the first architectural stage "done enough to rest on". Capture what was built, what was *not* built (explicit), and what the next stage opens with.

> Chinese reference snapshot: `docs/reference-cn/snapshot-2026-04-14/` covers R5-era governance docs; no snapshot update needed for this closeout (it is English-only retrospective prose, not long-lived conceptual content).

---

## 1. The positioning shift that shaped everything

The single most important event in Stage 1 was a mid-stage re-positioning (recorded 2026-04-14, CLAUDE.md §8):

> **From**: "a generic Ansible development template"
> **To**:   "an Ansible-based multi-server management control system"

Every round from R5 forward was evaluated against the new positioning. This is why Rounds 7→9 focused on a control plane, RBAC, and an audit loop rather than more roles or more Molecule scenarios.

---

## 2. What got built (by stage slice)

### 2.1 Engineering foundation (R1–R5)

| Concern | Artifact | State |
| --- | --- | --- |
| Role scaffolding | `roles/common`, `roles/webserver`, `roles/database` | Production-shaped, Molecule-tested |
| Playbook entrypoints | `playbooks/site.yml`, `rolling_update.yml`, `advanced_patterns.yml`, `vault_demo.yml` | 4 distinct patterns demonstrated |
| CI/lint | `.github/workflows/`, `ansible-lint`, `yamllint`, `pre-commit`, `detect-secrets` | All gates green |
| Testing | Molecule scenarios: `common`, `webserver`, `database`, plus `common-full-stack` (R5) | 4 scenarios |
| Python packaging | `pyproject.toml`, `tox.ini`, `uv` support | R5 addition |
| EE | `execution-environment.yml`, `ansible-navigator.yml` | Build recipe in place, image not pre-built |
| Dev tooling | `Makefile` (24 targets now), `dependabot.yml`, `.editorconfig` | R5 addition |

Artifacts: `docs/reviews/round-{2,3,4,5}-change-log-2026-04-09/14.md`.

### 2.2 Control plane (R7)

| Concern | Artifact | State |
| --- | --- | --- |
| Controller choice | Semaphore v2.10.34 OSS, SQLite (bolt) backend | Runs in ~200 MB RAM |
| Deployment | `controller/semaphore/docker-compose.yml` | Loopback + controller-net (R9) |
| First-run setup | `controller/semaphore/bootstrap.yml` (ansible-playbook) | Idempotent; project+inventory+repo+template in one go |
| Runtime smoke | `ansible-demo-semaphore` container `healthy`, port 3001/host | Verified end-to-end in R7 |

Architectural claim: a single operator can boot the whole control plane from zero → runnable template in <3 minutes with three make targets.

### 2.3 RBAC + credentials (R8)

| Concern | Artifact | State |
| --- | --- | --- |
| Role matrix | `controller/rbac/role-matrix.md` — owner / manager / task_runner / guest | 1:1 to Semaphore native roles |
| Demo users | `demo_platform`, `demo_dev`, `demo_audit` — random passwords via `ansible.builtin.password` | Gitignored `users.yml`, idempotent seeds |
| Credential placeholders | `ssh_lab_key` (SSH), `vault_prod_password` (login/password) | Import via UI *or* API — symmetric |
| Enforcement proof | `bash controller/rbac/smoke.sh` → 6/6 assertions | Guest POST 403, task_runner POST 403, owner GET 200 |
| API-gap handling | `/api/teams` missing in OSS v2.10 → teams collapsed to conceptual grouping | Documented in `role-matrix.md` §"API deviation" |

### 2.4 Audit loop (R8 sink + R9 wiring)

| Concern | Artifact | State |
| --- | --- | --- |
| Sink | `controller/audit/sink.py` — stdlib-only Python HTTP server | ~50 MB image |
| Persistence | Named volume + `logrotate` (7-day / 10 MB) | Container restart-safe |
| Semaphore→sink relay | `controller/audit/relay.py` — polls `/api/events`, forwards on cursor advance | 5 s poll, 1–2 s end-to-end latency |
| Unified network | External `controller-net`, auto-created by `make controller-net` | Symmetric, no `host.docker.internal` |
| End-to-end proof | `make controller-loop-smoke` → ALL GREEN, 1–2 s | Asserts login → action → JSONL line |

### 2.5 Governance (cross-cutting)

| Artifact | State |
| --- | --- |
| `CLAUDE.md` — project-level rules | Self-evolving §7 (R1–R9); 9 rules accumulated |
| `docs/reviews/review-iteration-charter.md` | Overall review protocol |
| Plan-doc → change-log pair for every landed round | R5, R7, R8, R9 (+ i18n a/b/c) |
| i18n | Runtime docs + user READMEs + inline comments all English; Chinese snapshots in `docs/reference-cn/` |

---

## 3. Key architectural decisions (with why)

1. **Semaphore over AWX / Rundeck** — fits the 1 GB RAM budget; SQLite backend means zero external dependencies for learning; upgrade path to PostgreSQL documented.
2. **Polling relay over outbound webhooks** — Semaphore OSS v2.10 has no outbound webhook emitter, but `/api/events` is the structured audit stream already powering the UI. Polling is simpler, richer, and multi-consumer safe.
3. **External docker network, not host-gateway** — symmetric, reviewable, lets future stacks (Loki, EDA) join without re-plumbing.
4. **Stdlib-only audit sink + relay** — a learning round does not deserve a Flask/FastAPI dep. `http.server` + `urllib` is ~130 lines each; no framework rot.
5. **Placeholder credentials with PEM-shaped dummy** — discovered Semaphore rejects `"private_key": ""` with HTTP 400; placeholder carries a sentinel `PLACEHOLDER-REPLACE-VIA-UI` so the failure mode is loud and obvious.
6. **Teams collapsed to direct user-role bindings** — Semaphore OSS has no `/api/teams`; recorded in `role-matrix.md` so a future OIDC round can re-inflate without matrix changes.
7. **Separate compose files per subsystem** — Semaphore, audit sink, (future) EDA, (future) observability each in their own compose file, joined by `controller-net`. Start-order is enforced by `depends_on: condition: service_healthy`, not by a monolithic compose.

---

## 4. Boundaries — what Stage 1 explicitly did *not* do

- **OIDC / LDAP / SSO** — local users only. Planned for Round 12.
- **Real secret backend** — ansible-vault + Semaphore Key Store only. HashiCorp Vault migration planned for Round 11.
- **Outbound notifications** — no Slack, Teams, email, ITSM. Only the audit JSONL. Round 12 candidate.
- **Multi-tenancy** — single-project demo. Round 13.
- **Disaster recovery** — no backup/restore playbook. Round 13.
- **Observability metrics** — Prometheus / Grafana / Loki deferred to Round 10.
- **EDA runtime** — image weight (602.9 MB) blew the R9 budget; slim image is Round 10 work.
- **Tamper-evident audit log** — append-only FS / signed JSONL still "future".

These are not deficiencies; they are the deliberately-unstarted scope for Stage 2.

---

## 5. Smoke tests inventory (how to verify Stage 1 still works)

```bash
make controller-net              # idempotent, creates shared network
make controller-up               # Semaphore on :3001
make controller-audit-up         # sink + polling relay on controller-net
make controller-bootstrap        # projects, users, role bindings, credentials
make controller-rbac-smoke       # 6/6 RBAC assertions
make controller-loop-smoke       # end-to-end Semaphore → JSONL (≤2 s)
```

Any new work that breaks either smoke must stop and fix before progressing.

---

## 6. Known sharp edges (document so next session doesn't re-discover)

| Edge | Where | Mitigation |
| --- | --- | --- |
| `localhost` resolves to `::1` inside alpine; Python `http.server` is IPv4-only | audit-sink healthcheck | Pin to `127.0.0.1`. Applied in R9. |
| Semaphore rejects empty `"private_key"` with HTTP 400 | bootstrap SSH key creation | Use PEM-shaped placeholder. Applied in R8. |
| `bash local var1=$1 var2=$var1` under `set -u` fails | smoke scripts | Split into separate `local` lines. Applied in R8. |
| `cd` persists across `Bash` tool calls but file-system paths may not | interactive investigation | Prefix with `cd /home/netcup/workspace/ansible-demo`. Operator habit, not codeable. |
| `/api/teams` returns 404 on Semaphore OSS | RBAC modeling | Collapse to conceptual grouping; document in matrix. |
| `/api/integrations` is inbound-only | outbound webhook design | Poll `/api/events` instead. |

---

## 7. Metrics (rough)

- **Commits on master**: 20
- **Review artifacts**: 31 markdown files under `docs/reviews/`, ~4,800 lines of plan + change log prose
- **CLAUDE.md rules accumulated**: 9 (R1–R9)
- **Smoke tests**: 2 make-driven (`rbac-smoke`, `loop-smoke`) + 3 Molecule scenarios
- **Running containers at end of stage**: 2 (semaphore, audit-sink) + 1 sidecar (audit-relay). Idle RSS ~230 MB total.

---

## 8. Ready-state for Stage 2

Stage 2 opens with these **assumptions already true**:

- Control plane is running, RBAC-enforced, and audit-logged.
- Any new subsystem can reach the audit sink on `audit-sink:3010` by joining `controller-net`.
- The bootstrap playbook is idempotent; re-running it produces no duplicates and never overwrites user-imported credentials.
- The governance loop (plan → change-log → memory) has been exercised 4 times successfully.
- All runtime prose is English; Chinese reference snapshots live under `docs/reference-cn/`.

Stage 2 **should not** revisit these items unless a defect is found.

---

## 9. Stage 2 entry tasks (for whoever picks this up next)

1. **Round 10 plan** — slim EDA runtime + Loki JSONL shipping. Task #32 already tracks this. Begin with `docs/reviews/claude-review-round-10-YYYY-MM-DD.md`.
2. **Round 11 plan** — secret management upgrade to HashiCorp Vault backend.
3. **Round 12 plan** — OIDC / outbound notifications.
4. **Round 13 plan** — multi-tenancy + DR playbooks.

Everything above Round 10 is open — no pre-approval, no fixed scope. The roadmap here is a *direction*, not a contract.

---

## 10. A note on pacing

Stage 1 produced a coherent architecture in 9 rounds without burning out the usage budget or drifting into scope creep. The single biggest lever for this was **plan-first** (R1): every round cost one plan doc up front, and every plan doc prevented at least one direction error. The second-biggest lever was **pre-committed fallback rules** (plan §6 style): R9 Phase 2 deferral fired cleanly because the rule was written *before* the measurement, not after. Keep both for Stage 2.

Rest on this stage. Pick Stage 2 up when the next question is clear.
