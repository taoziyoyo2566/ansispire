# Ansispire

Ansispire is an opinionated control plane on top of Ansible. It turns "scripts + SSH" into a system with a managed control plane (web UI, REST API, RBAC), an append-only audit plane, and an event-driven self-healing loop — without giving up the simplicity of plain Ansible roles for the data plane.

It is intended for teams managing a fleet of Linux servers who want one operational truth — where state lives, who changed what, when did it heal itself — instead of stitching that truth together after the fact.

On `feat/target-architecture`, the old local `vps_manager` control surface is intentionally removed. The retained VPS automation lives as plain Ansible content under [`playbooks/vps/`](./playbooks/vps/README.md) while the branch converges on Semaphore Inventory + Key Store + Task API as the control-plane truth.

---

## Capabilities

- **Self-healing**: events captured by the audit plane are matched against rules and dispatched to remediation playbooks via the control plane's REST API. No human in the loop for known faults.
- **Audit history**: control-plane events are relayed into a JSONL log whose writer appends records. Relay/reactor cursors support restart recovery, but the current store is not cryptographically tamper-evident and relay backfill is bounded.
- **Single source of truth for config**: ports, image tags, and inventory paths live in [`config/manifest.yml`](./config/manifest.yml) and propagate to every consumer (compose, Ansible vars, CI).
- **Tiered environment model**: `dev` (local loopback), `stag` (pre-prod parity), `prod` (live management + apps). One playbook, three inventories.
- **Two deployment paths**: Path A (Ansible role-based hub deploy onto a remote VPS) and Path B (docker-compose dev stack on your workstation). Same control plane image, same audit plane, different bootstrap.
- **Bearer-token machine identity**: the reactor talks to the control plane API with a scoped token minted by IaC bootstrap. The admin password never enters the reaction loop.
- **Semaphore-first VPS lifecycle content**: `playbooks/vps/` retains the onboarding / modify / audit / remove / docker_host / deploy_compose playbooks that the target architecture will drive from Semaphore Inventory + Key Store + Task API.

For the architecture-level picture, see [ARCHITECTURE.md](./ARCHITECTURE.md).

---

## Implementation status

_As of 2026-07-12. This table is the project-wide source of truth for "how far each piece is actually built"; branch-scoped detail lives in the [Saberu feature hub](./docs/feat-target-architecture/). Evidence levels are **not** interchangeable — real-VPS proof, Docker/CI E2E, and unit coverage are labelled distinctly._

| Piece | State | What backs it |
|---|---|---|
| Control plane — Semaphore + `bootstrap.yml` + Key Store + envs + `VPS Audit`/`VPS Onboard` templates | ✅ live | `make controller-up` / `controller-bootstrap` (idempotent IaC) |
| **VPS Audit** (read-only health: disk / mem / failed services / reboot) | ✅ real-VPS validated | Ubuntu 24 · Rocky 9 · Debian 13 |
| **VPS Onboard → managed cutover → re-audit `changed=0`** (the takeover loop) | ✅ 2/3 real-VPS | u24 + d13 end-to-end; RHEL pending (see below) |
| `make controller-vps-smoke` (managed-channel audit idempotency) | ✅ live PASS | asserts success + `changed=0` per host |
| **Modify** a managed host (packages / UFW / fail2ban / net tuning) | ~ playbook only | `playbooks/vps/modify.yml` — not wired to Semaphore, syntax-only |
| **Remove / de-register** (light unmanage — keeps user+keys) | ~ playbook only | `playbooks/vps/remove.yml` — not a decommission; not wired, syntax-only |
| **Offboard / true revert** (reopen 22, delete managed user) | ▱ backlog | not written — TASK-010 (`feat/vps-offboard`) |
| EDA audit + self-heal loop — `relay.py` → `sink.py` → `events.jsonl` → `reactor.py` → remediation | ✅ 46-test suite (L1–L5) | unit → component → disposable e2e + live loopback smoke |
| RBAC role boundary (`controller/rbac/`) | ✅ smoke-level | `make controller-rbac-smoke` |
| Data-plane roles (`common` / `webserver` / `database`) | ✅ Molecule | Ubuntu 22 + Debian 12; `infra_baseline` uncovered |
| RHEL full onboard (Rocky 9) | ~ blocked | first blocker: EPEL mirror reachability; later RHEL steps unverified |
| cf-worker Access Layer (Wizard / REST) | ⊘ deferred | built + probe-tested; not the current main line, incompatible with the transport-key reuse contract |
| DB-failover self-heal rule | ▱ placeholder | `enabled=false` (TASK-008) |

Legend: ✅ done / validated · ~ partial / blocked · ⊘ deferred · ▱ placeholder.

---

## Prerequisites

- **Control node** (where you run `ansible-playbook` and the optional dev compose stack): Linux (Ubuntu 22.04+ / Debian 12 recommended), Python 3.10+, Docker Engine + Compose plugin.
- **Managed nodes**: Python 3.9+; SSH reachable. Debian/Ubuntu Tier 1, RHEL family Tier 2. These two families are the complete supported set; other families are rejected by the baseline guard.
- **Ansible / collection versions**: pinned in [`requirements.txt`](./requirements.txt) and [`requirements.yml`](./requirements.yml). Do not deviate without rebuilding the [execution environment](./execution-environment.yml).

A one-shot setup verifies all of the above:

```bash
make setup    # creates .venv, installs deps, fetches Galaxy roles + collections
```

---

## Quickstart

The fastest path to "see it work" is the local docker-compose stack (Path B); no remote SSH needed.

```bash
# 1. Stand up the control plane on your workstation (port 3300)
cp controller/semaphore/.env.example controller/semaphore/.env
$EDITOR controller/semaphore/.env                       # set SEMAPHORE_ADMIN_PASSWORD
make controller-up                                       # docker compose up

# 2. IaC bootstrap (creates project / templates / mints API token)
make controller-bootstrap

# 3. Start the audit + reactor stack and verify the self-healing loop
make controller-audit-up
make test-eda-e2e                                        # disposable e2e on port 3320
```

Expected: `make test-eda-e2e` exits zero in ~60 s and leaves a Semaphore UI running at <http://localhost:3320> for inspection.

To deploy the same hub onto a remote VPS (Path A) instead, follow [`docs/user-guide/02-quickstart-eda.md`](./docs/user-guide/02-quickstart-eda.md).

**To take over and manage a real VPS** through Semaphore — onboard → SSH cutover to a managed port → re-audit `changed=0` — follow the step-by-step [**operator guide**](./docs/feat-target-architecture/operator-guide.md). That is the primary workflow this branch delivers; read [Caveats & gotchas](#caveats--gotchas) first (it is a takeover — it closes port 22).

---

## Caveats & gotchas

The hard-won ones — read these before operating the VPS lifecycle in anger.

- **Semaphore templates must bind `ANSIBLE_CONFIG`.** The task runner does *not* inherit the container's environment; each template must bind an Environment whose `env` sets `ANSIBLE_CONFIG=/workspace/controller/semaphore/ansible.cfg` (vault-free), or runs abort at config load on the host `.vault_pass`. `make controller-bootstrap` converges this — see [`controller/semaphore/README.md`](./controller/semaphore/README.md) "Template Authoring GOTCHA".
- **Onboard is a takeover — it closes port 22.** Only run it against a *recoverable* VPS (console/VNC or reinstall). The managed-login check runs *before* 22 is closed, so a failed onboard leaves `root@22` open and the host re-runnable. There is no auto-rollback (offboard is TASK-010, backlog).
- **RHEL needs EPEL reachable.** Onboard installs `fail2ban` from EPEL; an unreachable mirror hangs `dnf`. The RHEL full path is unverified past this blocker.
- **One fleet key does double duty.** The same keypair is the bootstrap transport *and* the managed user's login key. The **private** key lives only in the Semaphore Key Store (never in git, never handled by the agent); the **public** key must be trusted in the target's `authorized_keys`.
- **The audit store is append-only, not tamper-proof.** `events.jsonl` is an application-level append writer with restart cursors — not cryptographic non-repudiation or WORM storage, and relay backfill is bounded (~500 events/poll). Treat it as operational history, not a legal record.
- **`config/manifest.yml` is the single source of truth** for ports, image tags, and inventory paths — they propagate to compose, Ansible vars, and CI. Don't hardcode them elsewhere.

---

## Running tests

Two ways to invoke the same gates, choose by use case:

```bash
# Direct (fail-fast, single gate; for hot development):
make verify-quick           # commit-time syntax (~3 s)
make verify                 # push-time: lint + syntax + secrets + Python tests + dry-run (~30–60 s)
make verify-full            # release-time: verify + 4 molecule scenarios (~10–20 min)

# Structured (fail-collect, history-retaining; for pre-merge / pre-release):
./scripts/loopback_test_runner.sh           # standard mode (default, ~60 s)
./scripts/loopback_test_runner.sh quick     # ~10 s
./scripts/loopback_test_runner.sh ci-equiv  # ~10–20 min (local CI mirror: standard + molecule)
./scripts/loopback_test_runner.sh full      # ~15–25 min (ci-equiv + isolated L5 smoke)
./scripts/loopback_test_runner.sh exhaustive # ~20–30 min (full + disposable EDA e2e)
```

Both routes share the same Makefile targets and the same lint / molecule configs. Output of the runner lands in `test_results/run-<timestamp>/` with a `SUMMARY.md`, per-step logs, and an HTML coverage drilldown; `test_results/latest` points at the most recent run.

Full spec: [`docs/governance/loopback-runner.md`](./docs/governance/loopback-runner.md). Decision tree for "what should I run when I changed X": [`docs/governance/testing-governance.md §3`](./docs/governance/testing-governance.md).

---

## Document Map

| You want to... | Read |
|---|---|
| Understand the architecture in 5 minutes | [ARCHITECTURE.md](./ARCHITECTURE.md) |
| Operate or inspect the Saberu target architecture | [docs/feat-target-architecture/](./docs/feat-target-architecture/) |
| Inspect the retained VPS lifecycle content on this branch | [playbooks/vps/README.md](./playbooks/vps/README.md) |
| Install Ansispire on a clean machine | [docs/user-guide/01-installation.md](./docs/user-guide/01-installation.md) |
| Understand EDA self-healing end-to-end (rationale + failure modes) | [docs/user-guide/02-quickstart-eda.md](./docs/user-guide/02-quickstart-eda.md) |
| Look up a specific operational command (maintainer view) | [docs/operations/eda-core.md](./docs/operations/eda-core.md) · [docs/operations/hub-deployment.md](./docs/operations/hub-deployment.md) · [docs/operations/vps-lifecycle.md](./docs/operations/vps-lifecycle.md) |
| Understand the active target-architecture execution plan | [plan-semaphore-native-onboard-2026-06-10.md](./docs/reviews/feat-target-architecture/plan-semaphore-native-onboard-2026-06-10.md) · [execution addendum](./docs/reviews/feat-target-architecture/plan-saberu-vps-takeover-execution-2026-06-24.md) |
| Baseline a managed VPS (Debian / Ubuntu / Rocky / AlmaLinux) | `make target-deploy TARGET_NODE=<group\|alias>` — see [feature-map/multi-os-fleet.md](./docs/reference/feature-map/multi-os-fleet.md) |
| Choose which inventory / Make target for dev / stag / prod | [docs/operations/environments.md](./docs/operations/environments.md) |
| Know what's planned next | [TODO.md](./TODO.md) |
| Contribute code or docs | [docs/governance/contributing.md](./docs/governance/contributing.md) |
| Run the tests and understand the test pyramid | [docs/governance/testing-governance.md](./docs/governance/testing-governance.md) · [docs/reference/test-specs/](./docs/reference/test-specs/) |
| Review past incidents and decisions | [docs/reference/investigations/INDEX.md](./docs/reference/investigations/INDEX.md) |
| Read in 中文 | [docs/reference-cn/](./docs/reference-cn/) |

---

## Governance

This project follows a layered governance model. The relevant files:

- [AGENTS.md](./AGENTS.md) — Codex routing entry and path-local context loading
- [CLAUDE.md](./CLAUDE.md) — shared workflow baseline (task levels, sync discipline, branch lifecycle)
- [GEMINI.md](./GEMINI.md) — complementary Gemini / cross-agent guidance (context discipline, peer audit, codification)
- [docs/governance/ai-workflow.md](./docs/governance/ai-workflow.md) — repo-wide AI workflow model and how these layers fit together

Contributions must follow the workflow in [docs/governance/contributing.md](./docs/governance/contributing.md): scope-defined commits, mandatory diff self-check, evidence-backed test claims.

---

## Project meta

- [LICENSE](./LICENSE) — Apache-2.0
- [SECURITY.md](./SECURITY.md) — vulnerability reporting policy
- [CHANGELOG.md](./CHANGELOG.md) — release history
