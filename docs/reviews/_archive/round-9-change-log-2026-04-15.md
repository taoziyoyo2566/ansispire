# Round 9 Change Log — Closing the Control-Plane Loop

**Date**: 2026-04-15
**Reference**: [`claude-review-round-9-2026-04-15.md`](./claude-review-round-9-2026-04-15.md)
**Level**: Architecture — wires three existing subsystems (Semaphore, audit sink, shared network) into a live end-to-end event path.
**Outcome**: Phase 1 + Phase 3 + Phase 4 landed. Phase 2 (EDA) deferred to Round 10 per pre-committed §6 rule (image weight 602.9 MB > 300 MB budget).

---

## 1. Scope Recap vs Plan

| Plan Phase | Status | Notes |
| --- | --- | --- |
| 1. Semaphore → audit sink | **DONE** | Polling relay, not webhook — rationale §3 below |
| 2. EDA rulebook → audit sink | **DEFERRED to Round 10** | `quay.io/ansible/ansible-rulebook:latest` measured 602.9 MB, blew the 300 MB budget from plan §6. Pre-committed rule fired: defer, document, continue. |
| 3. Integration smoke + make target | **DONE** | `make controller-loop-smoke` — 1–2 s delivery end-to-end |
| 4. Change log + memory | **DONE** | this file + `memory/project_round_progress.md` |

---

## 2. File Change Manifest

| File | Change | Summary |
| --- | --- | --- |
| `controller/semaphore/docker-compose.yml` | modified | Joins external `controller-net` with alias `semaphore`. Keeps the per-compose default network for internal use. |
| `controller/audit/docker-compose.yml` | modified | Joins `controller-net` (alias `audit-sink`). Fixes healthcheck to `127.0.0.1` (sink binds IPv4-only, wget defaults to `::1`). Adds `audit-relay` sidecar with `depends_on: audit-sink healthy`. |
| `controller/audit/relay.py` | new | ~130 lines of stdlib-only polling relay. Logs in to Semaphore, polls `/api/events`, forwards new entries to `audit-sink:3010/event`, persists a cursor to a named volume. Handles session-expiry 401 with transparent re-login. |
| `controller/audit/loop-smoke.sh` | new (+x) | Round 9 smoke: login → fire action (dummy key create) → poll JSONL for marker → clean up. 20 s timeout; asserts 0 on hit. |
| `Makefile` | modified | New phony `controller-net` + `controller-loop-smoke`; `controller-up` and `controller-audit-up` now depend on `controller-net` (auto-creates the network on first use). `AUDIT_COMPOSE` now reads `controller/semaphore/.env` so the relay gets `SEMAPHORE_ADMIN_PASSWORD` without duplicating the secret. |

---

## 3. Design Decisions

### Polling relay, not outbound webhook

The plan flagged webhooks as the primary path. Probing Semaphore v2.10 proved the opposite:

- `/api/project/{pid}/integrations` — **inbound** webhooks (external systems POST to Semaphore to trigger template runs). Not for emitting events.
- `/api/events` and `/api/project/{pid}/events` — **structured audit stream**, newest-first, captures user_id / project_id / object_type / description / created / username. This *is* the outbound audit surface.

Polling `/api/events` beats webhooks here:

1. No Semaphore-side config churn. A user doesn't need to paste the sink URL into three per-project webhook settings.
2. Richer payload. The event objects include `object_type` and `description` fields Semaphore already built for the UI; webhooks would serialize a subset.
3. Multi-consumer safe. A second relay can run without Semaphore knowing or collision risk.
4. Failure mode is explicit: cursor doesn't advance → we know exactly where we stopped.

Trade-off acknowledged: a 5 s poll interval means up to 5 s audit lag. For a learning control plane this is acceptable; for production use one would switch to NATS or a streaming log.

### Unified `controller-net`, not host.docker.internal

`host.docker.internal` would have required a `--add-host` flag on the Semaphore compose and leaks loopback semantics into the compose file. External docker network is symmetric, documented, and lets Phase 2 (EDA) or Round 10 (Loki) join the same network without re-plumbing either existing stack.

Makefile auto-creates the network — `controller-up` and `controller-audit-up` both declare `controller-net` as a prerequisite and `docker network inspect || docker network create` is idempotent.

### Healthcheck bug discovered during verification

The R8 healthcheck used `http://localhost:3010/healthz`. `localhost` inside the alpine container resolves to both 127.0.0.1 and ::1; `wget` tried ::1 first, which the IPv4-only Python `ThreadingHTTPServer` rejects. Result: R8 containers reported "unhealthy" despite working fine. Fix is one line (`127.0.0.1`), same file. Noted as a follow-up in the original R8 changelog would have been nice; now corrected.

---

## 4. Self-check Results

| Check | Result |
| --- | --- |
| YAML syntax: both compose files | **PASS** (`yaml.safe_load_all`) |
| Python compile: `relay.py` | **PASS** (`py_compile`) |
| Bash syntax: `loop-smoke.sh` | **PASS** (`bash -n`) |
| CJK residual on 5 modified/new files | **0 chars** across all |
| `make controller-audit-up` idempotency | **PASS** — second run reports "Running / Waiting / Healthy", no recreate |
| `make controller-loop-smoke` cold run | **ALL GREEN, 2 s delivery** |
| `make controller-loop-smoke` warm run | **ALL GREEN, 1 s delivery** |
| Container footprint (relay added) | +~30 MB RSS, negligible CPU |
| Disk impact (EDA image pulled then removed) | net 0 — image rm'd after measurement |

---

## 5. What Was Explicitly NOT Done

- **EDA rulebook runtime** — deferred to Round 10 per plan §6. The `ansible-rulebook` image is 600 MB; a learning round deserves a slim custom image or a different runtime. Building that is its own round.
- **Observability stack** (Prometheus / Grafana / Loki) — still Round 10 candidate. The JSONL pipeline is now live, which is the correct sequencing per plan §3.
- **Webhook-emitter sidecar** as a second path — not needed once polling proved sufficient. Can revisit if Semaphore adds a native outbound webhook.
- **Semaphore → Slack / Teams notifications** — not in Round 9 scope; was only mentioned in a Round 6 plan doc.
- **Tamper-evidence / signed JSONL** — still future work.

---

## 6. Issues Encountered & Resolutions

- **IPv6 healthcheck mismatch**: `wget http://localhost/` resolved to `::1` inside alpine, sink binds IPv4. Caused R8 healthcheck to false-fail. Fixed by pinning to `127.0.0.1`.
- **`depends_on: condition: service_healthy`** blocked the relay start while the old healthcheck was broken. Exposed the healthcheck bug cleanly — a good outcome from a strict dependency model.
- **EDA image size**: 602.9 MB. Pre-committed rule in plan §6 fired. Took the documented fork: defer Phase 2, don't silently shrink scope.

---

## 7. Follow-Up / Next Steps

### Immediately doable

- **(Claude)** Commit Round 9 work in 4 logical commits per CONTRIBUTING.md §5:
  1. `feat(controller): unify compose network + fix audit healthcheck`
  2. `feat(controller): add Semaphore→audit polling relay`
  3. `chore(make): add controller-net + controller-loop-smoke targets`
  4. `docs(reviews): Round 9 plan + change log`
- **(Claude)** Update `memory/project_round_progress.md` — Round 9 landed, push EDA + observability to Round 10.

### Deferred (Round 10 candidate scope)

- **Slim EDA image**: build a custom `python:3.12-slim` + `ansible-rulebook` pip install, target <200 MB. Then wire the rule `HTTP source → POST audit-sink:3010/event`.
- **Ship JSONL to Loki**: tiny Promtail/Vector container reading the named volume. Dashboards in Grafana follow.
- **Task-level events in relay**: currently relay captures the `/api/events` admin audit stream. Template run start/stop lifecycle events live in `/api/project/{pid}/tasks` and are not yet in the feed — if audit completeness matters for a future round, extend the relay to poll both endpoints.

### Blocked / pending user

- **Task #22**: manual SSH key import via UI. Still pending; non-blocking for Round 10.

---

## 8. CLAUDE.md Updates (This Round)

Reviewed §7 rules R1–R9 against this round:

- **R1** (plan-first) — upheld; plan at `claude-review-round-9-2026-04-15.md` approved before any implementation.
- **R2** (architecture vs engineering) — upheld; Round 9 declared architecture, all changes touched the control-plane topology, not role contents.
- **R4** (clarify scope before starting) — upheld via plan §1.A; Option A/B both explored and Option B (close-the-loop) explicitly chosen.
- **R7** (local-ops autonomy) — exercised for compose up/down, docker image pull + rmi, curl probes. No approvals needed, matched the scope.
- **R8** (explicit Next Steps) — §7 above.
- **R9** (roadmap auto-continuation) — relevant here: plan pre-approved Phases 1→4; after Phase 1 landed I continued to Phase 2 in the same session; after Phase 2 tripped the §6 budget rule I continued to Phase 3 without pausing, because the deferral was *pre-committed* (not a scope change requiring re-approval). Correct application of the rule.

**One new observation worth folding into the rule set on the next iteration** (not a new rule yet — want to see if it recurs):

> When a self-imposed plan threshold fires (e.g. image size > budget), apply the pre-committed rule *and* continue the round. Do not stop to re-ask; the stop-condition is "budget exceeded AND no documented fallback", not "budget exceeded".

Saving for Round 10; will codify as a new rule only if the pattern repeats.
