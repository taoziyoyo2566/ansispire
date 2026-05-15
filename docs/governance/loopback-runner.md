# docs/governance/loopback-runner.md — Loopback Test Runner

> Local test orchestrator for Ansispire. Implements the gates defined in
> [`testing-governance.md §5`](testing-governance.md#5-质量闸口), plus an
> `exhaustive` deep-run mode, on top of the canonical `make` targets. It adds:
> result isolation, failure aggregation, trap-driven teardown, run history, and
> coverage thresholds.
>
> **TL;DR**: `./scripts/loopback_test_runner.sh [mode]` — default mode is `standard`.

---

## 1. What this is (and is not)

**Is**: a thin orchestrator over `make` targets. The Makefile is still the source of truth for *what each gate does*; this runner decides *which gates run in which order with which isolation*.

**Is not**: a replacement for `make verify` / `make verify-full`. Those targets remain the canonical entry points for ad-hoc local use. The runner is for **structured, comparable, history-retaining** test runs — e.g. "every push", "every release", or "before opening a PR".

**Why a separate tool exists at all**: `make verify` runs sequentially, prints to stdout, leaves no artifacts, and aborts on the first failure. That is correct for hot development. It is **not** suitable for: (a) deciding "is this branch shippable" before tagging, (b) producing an audit trail, (c) confirming a CI-equivalent run before pushing.

---

## 2. Modes

| Mode | Time | Gates it runs | Maps to |
|---|---|---|---|
| `quick` | ~10 s | syntax-check only | Save-point (commit) |
| `standard` *(default)* | ~60 s | quick + yamllint + ansible-lint + detect-secrets + Python L1/L2/L3 + dry-run | Push-before (push gate) |
| `ci-equiv` | ~10–20 min | standard + molecule × 4, no local L5 smoke | CI mirror |
| `full` | ~15–25 min | ci-equiv + isolated L5 control-plane smoke | Release-before |
| `exhaustive` | ~20–30 min | full + `test-eda-e2e` disposable docker stack | Deep pre-release run beyond §5 |

**Usage:**
```bash
./scripts/loopback_test_runner.sh                  # standard (default)
./scripts/loopback_test_runner.sh quick
./scripts/loopback_test_runner.sh ci-equiv
./scripts/loopback_test_runner.sh full
./scripts/loopback_test_runner.sh exhaustive
```

**Decision rule**: match the runner mode to the gate you are at (see [`testing-governance.md §3` decision tree](testing-governance.md#3-决策树什么改动跑什么测试)). When in doubt, `standard` before any push; `full` before any merge to `master`; `exhaustive` before a high-risk release.

---

## 3. Output layout

Every run produces a self-contained directory under `test_results/`:

```
test_results/
├── latest -> run-20260513-145555            # symlink to most recent
├── run-20260513-145555/
│   ├── orchestrator.log                     # phase-level timeline
│   ├── .status                              # tab-separated PASS/FAIL ledger
│   ├── SUMMARY.md                           # human-readable summary + failure tails
│   ├── bootstrap.log
│   ├── static/
│   │   ├── syntax.log
│   │   ├── yamllint.log
│   │   ├── ansible-lint.log
│   │   └── detect-secrets.log               # local baseline-diff gate
│   ├── eda/
│   │   ├── unit.log                         # L1 — reactor pure-Python
│   │   ├── contract.log                     # L2 — rules.json ↔ bootstrap.yml
│   │   ├── component.log                    # L3 — reactor → mock HTTP
│   │   ├── relay-unit.log                   # L1 — relay cursor/fetch/tick
│   │   ├── sink-unit.log                    # L1 — sink HTTP handler
│   │   └── filters-unit.log                 # L1 — custom Jinja filters
│   ├── coverage/
│   │   ├── report.txt                       # `coverage report -m`
│   │   ├── threshold.log                    # fail-under check
│   │   └── html/                            # HTML coverage report
│   ├── dry-run.log
│   ├── molecule/                            # ci-equiv / full / exhaustive only
│   │   ├── common.log
│   │   ├── webserver.log
│   │   ├── database.log
│   │   └── full-stack.log
│   ├── e2e/                                 # exhaustive only
│   │   └── test-eda-e2e.log
│   ├── smoke/                               # full / exhaustive only
│   │   ├── up.log
│   │   ├── wait.log
│   │   ├── bootstrap.log
│   │   ├── rbac.log
│   │   ├── audit-reload.log
│   │   └── loop.log
│   └── teardown.log
└── run-20260512-...                         # older runs (auto-pruned)
```

### `SUMMARY.md`
Auto-generated. Contains: mode, duration, pass/fail counts, full step ledger, **last 30 lines of every failed log inline**, and the coverage report. The first place to look after a failed run.

### History retention
The last `LOOPBACK_HISTORY_KEEP` (default 10) runs are kept. Older `run-*` directories are pruned at the end of every run. Set `LOOPBACK_HISTORY_KEEP=0` to disable pruning, or higher if you want a longer trail.

---

## 4. Environment overrides

| Variable | Default | Purpose |
|---|---|---|
| `MOLECULE_PARALLEL` | `0` | Set `1` to run the 4 molecule scenarios in parallel. Default is **serial** to match testing-governance §4.2; parallel is faster but ~4× memory pressure and harder to read interleaved logs. |
| `COVERAGE_MIN` | `70` | `coverage report --fail-under` threshold for target code, with `controller/audit/test_*.py` omitted from the report. |
| `SKIP_BOOTSTRAP` | `0` | Set `1` to reuse an existing `.venv` instead of running `scripts/bootstrap.sh`. Useful for back-to-back reruns; **not** safe across `requirements.txt` changes. |
| `LOOPBACK_INJECT_DUMMY_VAULT` | `0` | Set `1` to write a dummy vault password file inside the **isolation dir** (mktemp), exported as `ANSIBLE_VAULT_PASSWORD_FILE`. Use only if a role you're testing requires vault decryption. The runner never writes to `./.vault_pass` or `./inventory/local/vault.yml` in the working tree. |
| `LOOPBACK_HISTORY_KEEP` | `10` | Number of past `run-*` directories to retain. |
| `SEMAPHORE_READY_TIMEOUT` | `120` | Seconds to wait for `/api/ping` after the isolated smoke compose stack starts. Bump if your laptop is slower. |

---

## 5. Exit codes

| Code | Meaning |
|---|---|
| `0` | All steps passed. |
| `1` | At least one step failed. See `SUMMARY.md`. |
| `2` | Preflight or fatal setup error (python < 3.11, missing venv tool, docker unreachable for `ci-equiv` / `full` / `exhaustive`, bootstrap failed). |

---

## 6. Design properties

### 6.1 Fail-collect, not fail-fast
A failure in one step does **not** abort the run. All steps execute, and failures aggregate into `SUMMARY.md`. Rationale: a single test runner invocation should surface the full set of problems, not require N round-trips of "fix one, run again, fix the next."

This is **different** from `make verify`, which is fail-fast. Both are correct for their respective scenarios.

The one exception: bootstrap failure exits with rc=2 immediately — nothing else can run without a venv.

### 6.2 Trap-driven teardown
A bash `trap on_exit EXIT INT TERM` guarantees runner-owned docker stacks are torn down on every normal exit path — success, failure, Ctrl-C, even `set -e` abort. The teardown is idempotent and targets only the per-run compose project / e2e project.

### 6.3 Working-tree isolation
The runner **never writes credentials to tracked source paths**:
- No `.vault_pass` dropped at the repo root.
- No `inventory/local/vault.yml` overwritten.
- Dummy credentials (if requested) live in a `mktemp -d` directory wiped at exit.

Bootstrap still uses ignored runtime paths (`.venv/`, `collections/`, `test_results/`). Smoke credentials and env files live under the runner's `mktemp` isolation directory and are removed during teardown. Previous versions overwrote real credentials on every run; the v2.0 redesign closed that vulnerability.

### 6.4 Coverage threshold, not coverage theatre
Coverage is checked via `coverage report --fail-under=$COVERAGE_MIN` (default 70), not via `grep "100%"`. The report omits `controller/audit/test_*.py`, so the threshold is evaluated against implementation code rather than inflated by test files. The HTML report (`coverage/html/index.html`) is generated for drill-down.

### 6.5 Make targets as SSOT
The runner keeps the Makefile and `testing-governance.md` as the source of truth for gate semantics. Static gates and dry-run call named `make` targets directly; Python tests are invoked through `coverage run` so the runner can enforce a target-code coverage threshold while preserving the same test files as `make test-eda` / `make test-filters`.

Molecule and isolated smoke steps use direct tool invocations because the runner needs per-scenario logs and per-run disposable env files. Those direct invocations still mirror the canonical Makefile behavior; they do not introduce a second, incompatible gate definition.

---

## 7. Preflight gates

Before any test runs, the script checks:

1. **Not running as root** — local docker / venv assume normal user.
2. **`python3 >= 3.11`** — matches the project's pinned floor.
3. **Run from project root** — `Makefile` exists.
4. **Docker present and reachable** — only for `ci-equiv` / `full` / `exhaustive`, because `quick` and `standard` are docker-free.
5. **Available memory ≥ 6 GB** for `ci-equiv` / `full` / `exhaustive` modes — warning only (not fatal); 4 molecule scenarios + Semaphore + audit stack can swap on smaller hosts.
6. **Git tree status** — uncommitted changes are noted (informational), not blocked. You may want to test uncommitted work.

If a fatal preflight check fails, the script exits with rc=2 and still writes the partial `SUMMARY.md` under `test_results/run-<timestamp>/`.

---

## 8. Relationship to canonical Make targets

| Phase | Underlying make target(s) | Notes |
|---|---|---|
| Phase 0: preflight | — | runner-internal |
| Phase 1: bootstrap | `scripts/bootstrap.sh` | runs `make syntax` at the end as self-check |
| Phase 2: static | `make syntax`, `make yamllint`, `make ansible-lint`, `make detect-secrets` | static gates run in parallel after syntax |
| Phase 3: Python tests | `controller/audit/test_*.py` under `coverage run` | functionally equivalent to `make test-eda` + `make test-filters`, with coverage capture and test files omitted from the report |
| Phase 4: dry-run | `make dry-run` | |
| Phase 5: molecule | `molecule test -s <X>` for each scenario | direct call (not `make molecule-all`) so the runner can parallelize / capture per-scenario logs |
| Phase 6: EDA e2e | `make test-eda-e2e` with per-run `E2E_PROJECT` and random host ports | exhaustive only; teardown calls `controller/audit/e2e/run.sh down` for the same project |
| Phase 7: smoke | `docker compose` + `controller/semaphore/bootstrap.yml` + `controller/rbac/smoke.sh` + `controller/audit/loop-smoke.sh` | full / exhaustive only; uses isolated env, random host ports, and per-run container names |
| Phase 8: teardown | `docker compose down -v --remove-orphans` for runner-owned stacks | always runs (trap) |

---

## 9. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `FATAL: docker daemon not reachable` | `ci-equiv` / `full` / `exhaustive` needs Docker, and Docker desktop is not running or current user is not in `docker` group | Start docker; `sudo usermod -aG docker $USER` and re-login |
| `bootstrap failed; see ...` | network down, or `requirements.txt` floor not satisfied by host python | check `bootstrap.log`; usually pip can't reach PyPI |
| `Semaphore did not respond on /api/ping in 120s` | slow host, or port already bound | `lsof -i :3300`; bump `SEMAPHORE_READY_TIMEOUT=240` |
| `coverage --fail-under` fails but tests passed | coverage below threshold — that's the point | lower `COVERAGE_MIN=N`, or write more tests for the uncovered lines listed in `coverage/report.txt` |
| One molecule scenario hangs the whole run | ephemeral inventory from a prior failed run | see [testing-governance §9.1](testing-governance.md#91-何时必须清理); usually `rm -rf ~/.ansible/tmp/molecule.*` |
| Run leaves stale `ansispire-*-smoke-*` containers | runner crashed before trap fired (e.g. host OOM-killed) | remove only the specific `*-smoke-*` containers / network shown by `docker ps`; do not clean the dev stack by broad name pattern |
| `detect-secrets gate` fails on an untracked file | the gate scans tracked files plus untracked files not excluded by `.gitignore` | remove the secret, add a legitimate artifact to `.gitignore`, or regenerate `.secrets.baseline` for reviewed false positives |

---

## 10. CI parity

`./scripts/loopback_test_runner.sh ci-equiv` is intended to be **the most faithful local mirror** of what CI would run on the same commit. If your local `ci-equiv` is green but CI fails (or vice-versa), it's a divergence worth investigating — file an issue tagged `ci-divergence`. The two should converge.

CI itself does not invoke this script (it uses `.github/workflows/ci.yml` directly, with GitHub Actions' matrix parallelism for molecule). The script and CI are siblings, both consuming the canonical make targets.

---

## 11. Maintenance

Update this document **in the same round** that any of the following change:

| Change | Sync this doc's section |
|---|---|
| New phase / new gate | §2 mode table + §8 phase-to-make table |
| New env override | §4 |
| Output layout change | §3 |
| Make target rename | §8 |
| Default thresholds (`COVERAGE_MIN`, `LOOPBACK_HISTORY_KEEP`, `SEMAPHORE_READY_TIMEOUT`) | §4 |

When `testing-governance.md §3 / §5` adds a new gate or changes mode semantics, the runner's mode table must be re-aligned in the same round (or this doc cites a stale policy).

---

*Spec owner: see CODEOWNERS. Companion docs: [`testing-governance.md`](testing-governance.md), [`test-plan.md`](test-plan.md).*
