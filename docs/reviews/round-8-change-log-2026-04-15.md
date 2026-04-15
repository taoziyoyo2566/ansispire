# Round 8 Change Log — IAM, Credential Centralization, Lightweight Audit

**Date**: 2026-04-15
**Reference**: [`claude-review-round-8-2026-04-14.md`](./claude-review-round-8-2026-04-14.md)
**Level**: Architecture (§1.B) — introduces a new control-plane capability surface (RBAC + audit) on top of the Round 7 Semaphore bootstrap.
**Cost**: medium (≈2 h implementation + verification across two sessions)

---

## 1. Scope Recap

From the plan:

- **D1=a** — Python stdlib audit sink, not a Caddy access log. Keep structured payloads.
- **D2=b** — OIDC/LDAP deferred to Round 10; local users + Semaphore native roles this round.
- **D3=b** — Placeholder credentials imported at bootstrap; real SSH/vault material uploaded via UI per documented procedure.
- **D4=a** — Persistent volume + `logrotate` (7-day retention).
- **D5=b** — Teams collapsed to conceptual grouping because Semaphore OSS v2.10 has no `/api/teams` endpoint (documented in `role-matrix.md`).

Out-of-scope for this round (explicit): OIDC wiring, Loki shipping, JSONL tamper-evidence / signing, per-role API-key rotation.

---

## 2. File Change Manifest

| File | Change | Summary |
| --- | --- | --- |
| `controller/semaphore/bootstrap.yml` | modified | Extended the Round 7 bootstrap with 3 demo users, `round8-rbac-demo` project, role bindings, and two placeholder credentials. Uses `lookup('ansible.builtin.password', ...)` for persistent random passwords; user→id map built post-create for idempotent role bindings. |
| `controller/rbac/README.md` | new | Explains the demo, lists the 3 users, documents how to import real SSH keys / vault passwords through the UI, cleanup steps. |
| `controller/rbac/role-matrix.md` | new | 1:1 mapping from 4 demo roles to Semaphore native roles (owner / manager / task_runner / guest). Records the teams-API deviation. |
| `controller/rbac/smoke.sh` | new (+x) | 6 curl-driven assertions against the Semaphore REST API: guest GET 200 / guest POST 403, task_runner GET 200 / POST 403, owner GET /templates & /keys both 200. Cross-project scoping check for demo_audit. No ansible-playbook required on the host. |
| `controller/audit/docker-compose.yml` | new | `python:3.12-alpine` container, loopback bind `127.0.0.1:3010`, persistent named volume, hourly `logrotate` wrapper, stdlib-only runtime. |
| `controller/audit/sink.py` | new | ~80 lines of `http.server.ThreadingHTTPServer`. Endpoints: `GET /healthz` → `ok`, `POST /event` → 204, appends `{ts, remote, path, ua, payload}` JSON line. Non-JSON bodies preserved as strings so misconfigured senders do not silently drop coverage. |
| `controller/audit/logrotate.conf` | new | `daily`, `rotate 7`, `size 10M`, `compress`, `copytruncate`. |
| `controller/audit/README.md` | new | Architecture rationale (D1/D4), Semaphore→sink wiring options, smoke test, privacy/sensitivity notes (job output may contain vault-decrypted values under `-vv`). |
| `Makefile` | modified | Added `AUDIT_DIR`, `AUDIT_COMPOSE`, `AUDIT_CONTAINER` vars and 5 new targets: `controller-audit-up/down/tail/stats`, `controller-rbac-smoke`. |
| `.gitignore` | modified | Added `controller/rbac/users.yml` and `controller/audit/data/` — both are runtime-generated sensitive state. |

---

## 3. Intent Per Change

- **`bootstrap.yml` Round 8 block** — keep the Round 7 contract (idempotent, single-file) intact. Round 8 logic is appended, not refactored, so the existing smoke path is unaffected. The `when: ... | length == 0` guards on user / project / credential creation let a user re-run `make controller-bootstrap` freely.
- **Persistent-seed passwords** — `lookup('ansible.builtin.password', path=..., length=24)` writes to disk on first run and reads from disk thereafter. This is the minimum viable "persistent random secret" with no extra tooling; the file lives under `controller/rbac/` with mode 0700.
- **`users.yml` persistence** — makes the smoke test self-contained: a reviewer can reproduce the RBAC check from a single command after bootstrap finishes. File is gitignored and mode 0600.
- **`role-matrix.md`** — records the teams-API gap *as part of the artifact*, not a hidden workaround. A future Round 10 (OIDC) can re-introduce teams or map OIDC groups directly to Semaphore roles using the same matrix.
- **Audit sink stdlib-only** — avoids a Flask/FastAPI dependency on a learning-round container. ~50 MB image, one file, zero runtime deps.
- **Loopback-only bind** — the sink is explicitly not a production audit bus. Binding `127.0.0.1:3010` on the host prevents accidental exposure; the audit README documents the wiring options for getting Semaphore (in its own compose network) to reach the sink (`host.docker.internal`, socat relay, or a shared network in a later round).
- **`copytruncate` logrotate strategy** — the Python sink opens the log in append mode and does not re-exec on SIGHUP. `copytruncate` lets us rotate without signaling the sink; a small duplicate-write window is acceptable for a learning audit log.
- **Smoke test uses curl, not ansible** — host does not have `ansible-playbook`. Driving the REST API directly also gives a reviewer independent verification of the RBAC claims — not just "the playbook says the bindings are there".

---

## 4. What Was Explicitly NOT Done

- **OIDC / LDAP integration** — deferred to Round 10 per D2=b.
- **Shipping events to Loki** — deferred to Round 9.
- **Tamper-evident audit log** (append-only filesystem / JSONL signing) — listed as "future" in `controller/audit/README.md`; not required for a learning round.
- **Per-role API tokens** — bootstrap does not mint Semaphore API tokens. If a user wants programmatic access they log in via the cookie flow (same as the smoke test).
- **Teams API** — the v2.10 OSS endpoint returns 404. Rather than run a Semaphore Pro probe or build a mock, the demo collapses teams into a conceptual grouping documented in `role-matrix.md`.
- **EDA rulebook emitting audit events** — Round 8 landed the sink; wiring the rulebook to POST to it is a Round 9 topic.

---

## 5. Self-check Results

| Check | Result |
| --- | --- |
| YAML syntax: `bootstrap.yml`, `audit/docker-compose.yml` | **PASS** (`yaml.safe_load_all`) |
| Python compile: `sink.py` | **PASS** (`py_compile`) |
| CJK residual scan on 8 Round-8 files | **0 chars** across all |
| Audit sink end-to-end | **PASS** — `GET /healthz` 200, `POST /event` 204, JSONL line appears in `/var/log/semaphore/events.jsonl` |
| Bootstrap idempotency (via curl replay) | **PASS** — re-running login + user create + project create + role bind + key create with existing state produces 0 duplicates; keys list shows exactly `None`, `vault_prod_password`, `ssh_lab_key` |
| RBAC smoke test (`bash controller/rbac/smoke.sh`) | **ALL GREEN** — 6/6 assertions pass: guest GET 200 / POST 403, task_runner GET 200 / POST 403, owner GET /templates & /keys both 200 |
| SSH key creation regression | **FIXED** — Semaphore v2.10 rejects `"private_key": ""` with HTTP 400. Bootstrap now seeds an obviously-fake PEM placeholder (`PLACEHOLDER-REPLACE-VIA-UI`) and documents that the real key is imported via UI. |
| Cross-project scoping | **SKIP** — Round 7 `ansible-demo` project absent from this container (rebuilt). Re-running `make controller-bootstrap` would re-create it; smoke test handles absence gracefully. |
| Resource budget (host 8c16g) | audit-sink container idle ≈ 0.01 CPU / 8 MB RSS; compose stack negligible. |

---

## 6. Issues Encountered & Resolutions

- **`ssh_lab_key` HTTP 400 on initial run** → Semaphore v2.10 silently requires a non-empty `private_key` string. Fixed in `bootstrap.yml` with a PEM-shaped placeholder. Verified with a fresh curl call → 204. `controller/rbac/README.md` already tells users to replace via UI, so the placeholder never becomes a security concern.
- **`smoke.sh` unbound-variable under `set -u`** → `local user="$1" pw="$2" cookie="/tmp/sm-$user.cookies"` fails because bash evaluates RHS of multi-`local` statements without the just-declared names in scope. Split into separate `local` lines; smoke now passes.
- **`ansible-playbook` not on host** → blocked a full end-to-end playbook run. Mitigated by (a) curl-driven bootstrap replay to exercise the same API surface, (b) standalone `smoke.sh` so reviewers can verify RBAC independently of ansible.
- **Round 7 project absent** → the Round 7 `ansible-demo` project was not present in the current Semaphore container (likely rebuilt between rounds). Round 8 code is append-only in the same `bootstrap.yml`, so `make controller-bootstrap` re-creates R7 assets alongside R8 on the next clean run.

---

## 7. Follow-Up / Next Steps

### Immediately doable

- **(Claude)** Commit Round 8 work. Per CONTRIBUTING.md §5, split into logical commits:
  1. `feat(controller): add Round 8 RBAC bootstrap + smoke test`
  2. `feat(controller): add lightweight audit sink`
  3. `chore(make): add audit + rbac-smoke targets`
  4. `docs(reviews): Round 8 change log`
- **(Claude)** Update `memory/project_round_progress.md` — mark Round 8 landed with link to this change log.
- **(User)** Optional: import a real SSH key into `ssh_lab_key` via the Semaphore UI to exercise the documented flow in `controller/rbac/README.md`.

### Blocked

- **Round 7 `ansible-demo` project restoration** — requires `make controller-bootstrap` to run end-to-end, which requires `ansible-playbook` on the host or the EE image. Not a Round 8 defect; flag for Round 9.
- **Semaphore → audit sink wiring** — needs either `host.docker.internal` host-gateway flag on the Semaphore compose, or a shared network. Small config change; schedule with Round 9 rulebook work.

### Deferrable

- JSONL signing / append-only mount for tamper evidence — park until someone actually needs forensics-grade retention.
- Per-role API tokens — park until automation needs programmatic role-scoped access.

---

## 8. CLAUDE.md Updates (This Round)

Reviewed §7 rules R1–R9 against this round's user interactions:

- **R1 (plan-first)** — upheld; plan landed 2026-04-14, implementation started after acknowledgment.
- **R2 (architecture vs engineering)** — upheld; Round 8 declared architecture-level, audit sink and RBAC treated as control-plane additions.
- **R7 (local-ops autonomy)** — exercised for docker compose up/down, container exec, curl-driven API probe. No approval friction, matched the authorization.
- **R8 (explicit Next Steps)** — §7 above satisfies.
- **R9 (roadmap auto-continuation)** — N/A this round; Round 8 was an independent round following an "archived pending" signal, not a pre-approved phase sequence.

**No new rules added this round.** The teams-API deviation is a project-level artifact (`role-matrix.md`), not a governance rule.
