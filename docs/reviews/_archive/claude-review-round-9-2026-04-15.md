# Round 9 Review / Plan — Close the Control-Plane Loop

**Date**: 2026-04-15
**Level**: Architecture (§1.B) — wires three existing subsystems (Semaphore, EDA rulebook, audit sink) into a live end-to-end event path; no new subsystems added.
**Cost estimate**: medium (≈2 h implementation + verification)
**Authorization needed**: yes — roadmap-approved-first (R3); this round changes the original backlog framing.

> Chinese reference snapshot: will be created at landing time under
> `docs/reference-cn/snapshot-<date>/docs/reviews/` if the round introduces
> long-lived conceptual docs worth snapshotting (likely not — this round
> is mostly wiring).

---

## 1. System Intent Clarification (§1.A)

- **Kind of system**: ② architecture — control-plane/data-plane integration. Round 7 built Semaphore; Round 8 built audit sink + RBAC; Round 9 **connects** them.
- **Boundaries**: everything stays on the 8c16g host. No external services, no network egress, no credential material on disk beyond what Round 8 already placed.
- **NFR priority**: correctness (events reach the sink reliably) > observability (we can see when wiring breaks) > footprint. Availability / scalability not in scope for a learning loop.
- **Authorization scope**: container restart, compose file edits, EDA rulebook additions, smoke scripts. **Out of scope without fresh approval**: host networking changes (`iptables`, firewall), installing system packages on the host, any `docker system prune`/`docker volume rm`.

---

## 2. Current-State Gap Analysis

What exists after Round 8:

| Capability | State | Gap |
| --- | --- | --- |
| Semaphore control plane (R7) | running on `:3001`, RBAC demo loaded | cannot POST webhooks to audit sink — different compose, no route |
| Audit sink (R8) | listening `127.0.0.1:3010`, accepts any JSON, JSONL works | receives **only** manual curl; no real events |
| EDA rulebook stub (R5) | `extensions/eda/rulebooks/` scaffolding | never wired to an actual event source; never POSTs anywhere |
| RBAC smoke (R8) | 6/6 green via curl | no event produced in the sink — RBAC actions are invisible |
| Round 7 `ansible-demo` project | **absent** from current Semaphore container | R8 container rebuild wiped it; will re-appear on next `make controller-bootstrap` |

**Architectural gap**: control-plane actions (template runs, role changes, logins) leave **no trace** in the audit sink. The subsystems exist but the edges between them do not. For a "management control system" (project positioning §8), that is a correctness defect, not a nice-to-have.

---

## 3. Scope Decision

Two scope options were on the table:

- **Option A** — observability stack (Prometheus + Grafana + Loki). Original Round 9 backlog entry.
- **Option B** — close the loop: wire Semaphore→sink, EDA→sink, add a minimal integration smoke. **Recommended.**

**Chosen: Option B.** Rationale:

1. Option A adds three new containers (Prometheus, Grafana, Loki) to a host that already runs Semaphore, audit sink, reality_core, jellyfin, open-webui, ollama. Node-exporter-style metrics are useful, but they measure the *process*, not the *audit trail* — and the audit trail is already half-built.
2. The existing audit sink is **unused** as of end-of-R8. Stacking more observability on top of an unused primary would be cart-before-horse.
3. Option B produces a demonstrably-working control loop by the end of the round. Option A produces dashboards that, without an upstream, show nothing.
4. Loki is explicitly scheduled under Round 9 in the R8 plan doc; pulling it forward without a working JSONL pipeline is premature.

**What Option A turns into**: a **Round 10** plan. Shipping audit JSONL → Loki becomes trivial once the JSONL pipeline is live; adding Prometheus/Grafana on a well-defined loop is then straightforward.

---

## 4. Phased Roadmap

### Phase 1 — Semaphore → audit sink (the missing edge)

1. Unify network: add the audit sink to the Semaphore compose network (external network or `networks:` section) so the sink becomes resolvable as `audit-sink:3010` from inside the Semaphore container.
   - Alternative considered: `host.docker.internal` via `--add-host host-gateway`. Rejected — requires host-level flag coordination and leaks loopback semantics into the compose file.
2. Document the webhook URL that Semaphore users should paste (`http://audit-sink:3010/event`).
3. Smoke: trigger a template run from Semaphore UI, observe a line appear in `events.jsonl` within 2 s.

### Phase 2 — EDA rulebook → audit sink

1. Flesh out one rulebook that listens on an HTTP source and emits an audit event on match.
2. Wire it into `ansible-rulebook` via a tiny `docker-compose.yml` (or the existing EE image if lighter).
3. Smoke: curl the EDA source, observe both the EDA action's log AND a new JSONL line in the sink.

### Phase 3 — Integration smoke + Makefile target

1. Add `make controller-loop-smoke` — a one-shot script that:
   - Starts Semaphore + audit sink + EDA (if not already up)
   - Triggers a template run via API
   - Greps `events.jsonl` for the expected event type
   - Exits non-zero on miss
2. This is the Round 9 equivalent of `controller-rbac-smoke`: a reviewer can verify the loop with one command.

### Phase 4 — Change log + memory update

1. Write `docs/reviews/round-9-change-log-YYYY-MM-DD.md` per §2.B.
2. Update `memory/project_round_progress.md`: mark Round 9 landed, push observability stack to Round 10.

---

## 5. Judgment Criteria (what "done" means)

- `make controller-audit-up && make controller-up` + template run → JSONL gains a Semaphore-emitted line.
- `make controller-loop-smoke` → exits 0.
- No credential material, no host firewall change, no new container beyond what Phase 2 needs.
- CJK residual on all new files = 0.
- Change log landed.

---

## 6. Risks / Unknowns

- **Semaphore webhook format unknown at time of planning**. If Semaphore v2.10 OSS does not ship a stable webhook-on-task-event integration, Phase 1 degrades to a polling relay (a tiny sidecar that polls `/api/tasks/last` and POSTs deltas). That is still Round 9 scope.
- **EDA rulebook runtime weight**. `ansible-rulebook` needs a Python env with `ansible-rulebook`, `aiohttp`, and the decision-environment collection. If container size exceeds ~300 MB we will defer EDA to a later round and land Round 9 with Phase 1 + Phase 3 only — state this explicitly in the change log rather than silently shrinking scope.
- **Round 7 project restoration**. `make controller-bootstrap` needs to be run end-to-end once during this round to re-create the `ansible-demo` project (currently absent). Confirmed safe; no data loss risk.

---

## 7. Out of Scope (explicit)

- Prometheus / Grafana dashboards (Round 10).
- Shipping JSONL to Loki (Round 10).
- Tamper-evident log signing (future).
- Multi-node EDA (future).
- Replacing `ansible-vault` with HashiCorp Vault (Round 11 per backlog).
- OIDC / LDAP login (Round 11 per backlog).

---

## 8. Authorization Checklist (please confirm)

- [ ] Scope: Option B (close-the-loop), as described in §4.
- [ ] Level: architecture — allowed to touch `controller/semaphore/docker-compose.yml`, `controller/audit/docker-compose.yml`, add EDA runtime compose, extend Makefile.
- [ ] Autonomy: R7 continues to apply (start/stop containers, run smoke, read-only inspection). **Require fresh approval for**: any change to host networking, sudo-level operations, mounting host paths beyond the existing workspace read-only mount.
- [ ] If Phase 2 (EDA runtime) turns out to be too heavy, I deliver Phase 1 + Phase 3 only and note it explicitly — do not silently expand to "replace EDA with a Python script".

Reply "approved" (or redirect to Option A) before I start implementing.

---

## 9. Ordered Task Draft (for post-approval TaskCreate)

1. Probe Semaphore v2.10 webhook capability (REST API + UI screenshot).
2. Unify compose network between Semaphore and audit sink.
3. Wire one working webhook: Semaphore → `audit-sink:3010/event`.
4. Verify via manual template run; assert JSONL gain.
5. Scaffold EDA rulebook container (compose-based).
6. Add one rule: HTTP source → POST audit.
7. Verify EDA edge end-to-end.
8. Write `make controller-loop-smoke`.
9. Self-check (CJK, YAML/Python syntax, idempotency).
10. Write Round 9 change log + memory update.

Phases 1+3 only (if Phase 2 deferred): drops 5–7, keeps 1–4, 8–10.
