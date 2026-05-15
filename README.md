# Ansispire

Ansispire is an opinionated control plane on top of Ansible. It turns "scripts + SSH" into a system with a managed control plane (web UI, REST API, RBAC), an append-only audit plane, and an event-driven self-healing loop — without giving up the simplicity of plain Ansible roles for the data plane.

It is intended for teams managing a fleet of Linux servers who want one operational truth — where state lives, who changed what, when did it heal itself — instead of stitching that truth together after the fact.

---

## Capabilities

- **Self-healing**: events captured by the audit plane are matched against rules and dispatched to remediation playbooks via the control plane's REST API. No human in the loop for known faults.
- **Audit-grade history**: every control-plane action lands in an append-only JSONL log; the audit relay reconciles via cursor + pagination, so events are not lost across restarts.
- **Single source of truth for config**: ports, image tags, and inventory paths live in [`config/manifest.yml`](./config/manifest.yml) and propagate to every consumer (compose, Ansible vars, CI).
- **Tiered environment model**: `dev` (local loopback), `stag` (pre-prod parity), `prod` (live management + apps). One playbook, three inventories.
- **Two deployment paths**: Path A (Ansible role-based hub deploy onto a remote VPS) and Path B (docker-compose dev stack on your workstation). Same control plane image, same audit plane, different bootstrap.
- **Bearer-token machine identity**: the reactor talks to the control plane API with a scoped token minted by IaC bootstrap. The admin password never enters the reaction loop.
- **VPS lifecycle plugin**: `plugins/vps_manager/` consumes one-shot YAML tasks, onboards VPS hosts onto a non-22 SSH management port, archives tasks with redaction, and keeps a local VPS inventory for follow-up actions.

For the architecture-level picture, see [ARCHITECTURE.md](./ARCHITECTURE.md).

---

## Prerequisites

- **Control node** (where you run `ansible-playbook` and the optional dev compose stack): Linux (Ubuntu 22.04+ / Debian 12 recommended), Python 3.10+, Docker Engine + Compose plugin.
- **Managed nodes**: Python 3.9+; SSH reachable. Debian/Ubuntu Tier 1, RHEL family Tier 2, Alpine Tier 2.
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
| Onboard or manage VPS hosts from YAML tasks | [plugins/vps_manager/README.md](./plugins/vps_manager/README.md) |
| Install Ansispire on a clean machine | [docs/user-guide/01-installation.md](./docs/user-guide/01-installation.md) |
| Understand EDA self-healing end-to-end (rationale + failure modes) | [docs/user-guide/02-quickstart-eda.md](./docs/user-guide/02-quickstart-eda.md) |
| Look up a specific operational command (maintainer view) | [docs/operations/eda-core.md](./docs/operations/eda-core.md) · [docs/operations/hub-deployment.md](./docs/operations/hub-deployment.md) · [docs/operations/vps-manager.md](./docs/operations/vps-manager.md) |
| Choose which inventory / Make target for dev / stag / prod | [docs/operations/environments.md](./docs/operations/environments.md) |
| Know what's planned next | [TODO.md](./TODO.md) |
| Contribute code or docs | [docs/governance/contributing.md](./docs/governance/contributing.md) |
| Run the tests and understand the test pyramid | [docs/governance/testing-governance.md](./docs/governance/testing-governance.md) · [docs/reference/test-specs/](./docs/reference/test-specs/) |
| Review past incidents and decisions | [docs/reference/investigations/INDEX.md](./docs/reference/investigations/INDEX.md) |
| Read in 中文 | [docs/reference-cn/](./docs/reference-cn/) |

---

## Governance

This project follows a layered governance model. The relevant files:

- [CLAUDE.md](./CLAUDE.md) — workload classification (L0–L2), mandatory plan-first / changelog protocol
- [GEMINI.md](./GEMINI.md) — Gemini-specific operating directives
- [docs/governance/ai-workflow.md](./docs/governance/ai-workflow.md) — how AI collaborators should operate inside this repo

Contributions must follow the workflow in [docs/governance/contributing.md](./docs/governance/contributing.md): scope-defined commits, mandatory diff self-check, evidence-backed test claims.

---

## Project meta

- [LICENSE](./LICENSE) — Apache-2.0
- [SECURITY.md](./SECURITY.md) — vulnerability reporting policy
- [CHANGELOG.md](./CHANGELOG.md) — release history
