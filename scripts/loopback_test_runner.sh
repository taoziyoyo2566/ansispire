#!/usr/bin/env bash
# Ansispire Loopback Test Runner v2.0
#
# Thin orchestrator over the canonical Make targets defined in
# docs/governance/testing-governance.md §3-§5. Modes map to the
# common gates: quick = save-point, standard = push, ci-equiv = CI mirror,
# full = release, exhaustive = release plus disposable e2e.
#
# Design:
#   - Never rewrites gate logic — uses canonical `make` targets for static /
#     dry-run gates and direct tool calls only where per-step isolation or
#     coverage capture requires it.
#   - fail-collect (not fail-fast): a single failure does NOT abort the
#     run; all failures are aggregated into SUMMARY.md.
#   - trap-driven teardown: runner-owned control-plane and audit stacks are
#     torn down on any exit (success, failure, ctrl-c).
#   - Isolation: never writes credentials to the working tree (no .vault_pass /
#     inventory/local/vault.yml dropped into the repo). Optional dummy vault
#     password file lives in $WORKDIR (mktemp). Runtime output is confined to
#     ignored paths such as .venv/, collections/, test_results/, or disposable
#     runner workdirs.
#   - History: results stored in test_results/run-<ts>/, with `latest`
#     symlink and auto-prune to LOOPBACK_HISTORY_KEEP (default 10).
#
# Full spec: docs/governance/loopback-runner.md

set -Eeuo pipefail

# ── 1. constants & globals ──────────────────────────────────────────────────
PROJECT_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$PROJECT_ROOT"

VENV="$PROJECT_ROOT/.venv"
RESULTS_BASE="$PROJECT_ROOT/test_results"
TS=$(date +%Y%m%d-%H%M%S)
RUN_DIR="$RESULTS_BASE/run-$TS"
LATEST_LINK="$RESULTS_BASE/latest"
LOG="$RUN_DIR/orchestrator.log"
STATUS_FILE="$RUN_DIR/.status"
WORKDIR=""                                           # mktemp -d; set in setup_isolation
START_EPOCH=$(date +%s)
E2E_RAN=0
E2E_PROJECT_NAME=""

SMOKE_PROJECT=""
SMOKE_ENV=""
SMOKE_SECRETS=""
SMOKE_INVENTORY=""
SMOKE_RBAC_DIR=""
SMOKE_SEMAPHORE_PORT=""
SMOKE_AUDIT_PORT=""
SMOKE_SEMAPHORE_CONTAINER=""
SMOKE_SINK_CONTAINER=""
SMOKE_RELAY_CONTAINER=""
SMOKE_REACTOR_CONTAINER=""
SMOKE_NET=""
SMOKE_ADMIN_USER="admin"
SMOKE_ADMIN_PASSWORD="loopback_smoke_disposable_pw"  # pragma: allowlist secret
E2E_COMPOSE_FILE="$PROJECT_ROOT/controller/audit/e2e/compose.e2e.yml"

# ── 2. tunables (env overrides) ─────────────────────────────────────────────
MOLECULE_PARALLEL="${MOLECULE_PARALLEL:-0}"          # 0=serial (testing-governance §4.2 default)
COVERAGE_MIN="${COVERAGE_MIN:-70}"                   # coverage --fail-under threshold
SKIP_BOOTSTRAP="${SKIP_BOOTSTRAP:-0}"                # 1 = reuse existing .venv
LOOPBACK_INJECT_DUMMY_VAULT="${LOOPBACK_INJECT_DUMMY_VAULT:-0}"
LOOPBACK_HISTORY_KEEP="${LOOPBACK_HISTORY_KEEP:-10}"
SEMAPHORE_READY_TIMEOUT="${SEMAPHORE_READY_TIMEOUT:-120}"  # seconds
COVERAGE_OMIT="controller/audit/test_*.py"

# ── 3. helpers ──────────────────────────────────────────────────────────────
log() {
    local msg="[$(date +%H:%M:%S)] $*"
    if [ -d "$RUN_DIR" ]; then
        echo "$msg" | tee -a "$LOG"
    else
        echo "$msg"
    fi
}
step() { log ""; log "── $* ──"; }
die()  { log "FATAL: $*"; exit 2; }

reserve_logname() {
    local requested="$1"
    local candidate="$requested"
    local base="$requested" ext="" n=2 safe

    if [[ "$requested" == *.* ]]; then
        base="${requested%.*}"
        ext=".${requested##*.}"
    fi

    mkdir -p "$RUN_DIR/.lognames"
    while true; do
        safe=$(printf '%s' "$candidate" | tr '/[:space:]' '___')
        if mkdir "$RUN_DIR/.lognames/$safe" 2>/dev/null; then
            printf '%s' "$candidate"
            return 0
        fi
        candidate="${base}.${n}${ext}"
        n=$((n + 1))
    done
}

# run_step <label> <relative-log-path> <cmd...>
#   - never aborts the orchestrator; records status to $STATUS_FILE
#   - safe to call inside `&` subshells (file appends are atomic for our line sizes)
run_step() {
    local label="$1" requested_logname="$2"; shift 2
    local logname
    logname=$(reserve_logname "$requested_logname")
    local logfile="$RUN_DIR/$logname"
    mkdir -p "$(dirname "$logfile")"
    log "→ $label"
    if [ "$logname" != "$requested_logname" ]; then
        log "  WARN  duplicate log path '$requested_logname'; using '$logname'"
    fi
    local rc=0
    "$@" >"$logfile" 2>&1 || rc=$?
    if [ "$rc" -eq 0 ]; then
        log "  PASS  $label"
        printf 'PASS\t%s\t%s\n' "$label" "$logname" >>"$STATUS_FILE"
    else
        log "  FAIL  $label (rc=$rc, log=$logname)"
        printf 'FAIL\t%s\t%s\t%s\n' "$label" "$logname" "$rc" >>"$STATUS_FILE"
    fi
    return 0
}

skip_step() {
    local label="$1" logname="${2:--}" reason="${3:-skipped}"
    log "  SKIP  $label ($reason)"
    printf 'SKIP\t%s\t%s\t%s\n' "$label" "$logname" "$reason" >>"$STATUS_FILE"
}

step_failed() {
    local label="$1"
    awk -F'\t' -v label="$label" '$1=="FAIL" && $2==label{f=1} END{exit !f}' "$STATUS_FILE"
}

count_failures() {
    [ -f "$STATUS_FILE" ] || { echo 0; return; }
    awk '$1=="FAIL"{n++} END{print n+0}' "$STATUS_FILE" 2>/dev/null
}
count_passes() {
    [ -f "$STATUS_FILE" ] || { echo 0; return; }
    awk '$1=="PASS"{n++} END{print n+0}' "$STATUS_FILE" 2>/dev/null
}

# ── 4. usage ────────────────────────────────────────────────────────────────
usage() {
    cat <<EOF
Usage: $0 [quick|standard|ci-equiv|full|exhaustive]

Modes (quick through full correspond to testing-governance.md §5 gates):
  quick      ~10s    syntax-check only                          (save-point)
  standard   ~60s    + lint + EDA pyramid + dry-run + secrets   (push, DEFAULT)
  ci-equiv   ~10-20m standard + molecule(4), no local L5 smoke   (CI mirror)
  full       ~15-25m ci-equiv + isolated L5 smoke                (release)
  exhaustive ~20-30m full + EDA e2e disposable docker            (pre-release deep run)

Environment overrides:
  MOLECULE_PARALLEL=1            run 4 molecule scenarios in parallel (experimental;
                                 default 0; serial per testing-governance §4.2)
  COVERAGE_MIN=70                coverage report --fail-under threshold
  SKIP_BOOTSTRAP=1               reuse existing .venv if present (faster reruns)
  LOOPBACK_INJECT_DUMMY_VAULT=1  generate a dummy vault password file inside
                                 the isolation dir (NOT the working tree)
  LOOPBACK_HISTORY_KEEP=10       retain last N test_results/run-* dirs
  SEMAPHORE_READY_TIMEOUT=120    seconds to wait for Semaphore /api/ping

Output:
  test_results/run-<timestamp>/   per-step logs + SUMMARY.md + coverage/
  test_results/latest             symlink → most recent run

Exit codes:
  0  all steps passed
  1  one or more steps failed (see SUMMARY.md)
  2  preflight / fatal error before tests could run

Spec: docs/governance/loopback-runner.md
EOF
}

# ── 5. argument parsing ─────────────────────────────────────────────────────
MODE="${1:-standard}"
case "$MODE" in
    quick|standard|ci-equiv|full|exhaustive) ;;
    -h|--help|help) usage; exit 0 ;;
    *) echo "Unknown mode: $MODE" >&2; usage >&2; exit 2 ;;
esac

# ── 6. preflight ────────────────────────────────────────────────────────────
preflight() {
    step "Phase 0 — Preflight"
    [ "$EUID" -eq 0 ] && die "do not run as root (uses local docker)"
    command -v python3 >/dev/null || die "python3 not found"
    python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" \
        || die "python3 >= 3.11 required (got $(python3 --version))"
    [ -f Makefile ] || die "Makefile not found (run from project root)"

    if [ "$MODE" = "ci-equiv" ] || [ "$MODE" = "full" ] || [ "$MODE" = "exhaustive" ]; then
        command -v docker >/dev/null || die "docker not found in PATH"
        docker info >/dev/null 2>&1 || die "docker daemon not reachable"
    fi

    local mem_gb=0
    if [ -r /proc/meminfo ]; then
        mem_gb=$(awk '/MemAvailable/ {print int($2/1024/1024)}' /proc/meminfo)
    fi
    log "Available memory: ${mem_gb} GB"
    if { [ "$MODE" = "ci-equiv" ] || [ "$MODE" = "full" ] || [ "$MODE" = "exhaustive" ]; } && [ "$mem_gb" -lt 6 ]; then
        log "WARN: $mem_gb GB available; molecule + Semaphore typically need ≥6 GB"
    fi

    if [ -n "$(git status --porcelain 2>/dev/null || true)" ]; then
        log "NOTE: working tree has uncommitted changes (will be tested as-is)"
    fi
    log "PASS  preflight"
}

# ── 7. isolation ────────────────────────────────────────────────────────────
setup_isolation() {
    WORKDIR=$(mktemp -d -t ansispire-loopback-XXXXXXXX)
    log "Isolation dir: $WORKDIR"
    mkdir -p "$WORKDIR/ansible-local-tmp" "$WORKDIR/ansible-remote-tmp"
    export ANSIBLE_LOCAL_TEMP="$WORKDIR/ansible-local-tmp"
    export ANSIBLE_REMOTE_TEMP="$WORKDIR/ansible-remote-tmp"
    log "  ANSIBLE_LOCAL_TEMP → $ANSIBLE_LOCAL_TEMP"
    log "  ANSIBLE_REMOTE_TEMP → $ANSIBLE_REMOTE_TEMP"
    if [ "$LOOPBACK_INJECT_DUMMY_VAULT" = "1" ]; then
        echo "dummy_vault_pass" > "$WORKDIR/.vault_pass"
        chmod 600 "$WORKDIR/.vault_pass"
        export ANSIBLE_VAULT_PASSWORD_FILE="$WORKDIR/.vault_pass"
        log "  ANSIBLE_VAULT_PASSWORD_FILE → $ANSIBLE_VAULT_PASSWORD_FILE"
    fi
}

# ── 8. bootstrap ────────────────────────────────────────────────────────────
bootstrap() {
    step "Phase 1 — Environment Bootstrap"
    if [ "$SKIP_BOOTSTRAP" = "1" ] && [ -x "$VENV/bin/python" ]; then
        log "  reusing existing .venv (SKIP_BOOTSTRAP=1)"
        printf 'PASS\t%s\t%s\n' "bootstrap (skipped)" "-" >>"$STATUS_FILE"
    else
        run_step "bootstrap.sh" "bootstrap.log" bash scripts/bootstrap.sh
        # if bootstrap failed, we can't run anything else — bail cleanly
        if [ "$(count_failures)" -gt 0 ]; then
            die "bootstrap failed; see $RUN_DIR/bootstrap.log"
        fi
    fi
    export PATH="$VENV/bin:$PATH"
    # Standard+ modes require tools declared in requirements.txt. Do not
    # install ad hoc here; a stale venv must be fixed by re-running bootstrap.
    if [ "$MODE" != "quick" ]; then
        [ -x "$VENV/bin/coverage" ] || die "coverage missing from .venv; run scripts/bootstrap.sh or unset SKIP_BOOTSTRAP"
        [ -x "$VENV/bin/detect-secrets" ] || die "detect-secrets missing from .venv; run scripts/bootstrap.sh or unset SKIP_BOOTSTRAP"
        [ -x "$VENV/bin/yamllint" ] || die "yamllint missing from .venv; run scripts/bootstrap.sh or unset SKIP_BOOTSTRAP"
    fi
}

# ── 9. static (L0) ──────────────────────────────────────────────────────────
phase_static() {
    step "Phase 2 — Static (L0)"
    # syntax always runs (quick mode requires only this)
    run_step "syntax-check (stag+prod)" "static/syntax.log" make syntax
    [ "$MODE" = "quick" ] && return

    # parallel: yamllint, ansible-lint, detect-secrets
    local pids=()
    ( run_step "yamllint" "static/yamllint.log" make yamllint ) & pids+=($!)
    ( run_step "ansible-lint (production)" "static/ansible-lint.log" make ansible-lint ) & pids+=($!)
    ( run_step "detect-secrets gate" "static/detect-secrets.log" make detect-secrets ) & pids+=($!)
    for p in "${pids[@]}"; do wait "$p" || true; done
}

# ── 10. Fast Python tests (L1+L2+L3) ────────────────────────────────────────
phase_eda() {
    [ "$MODE" = "quick" ] && return
    step "Phase 3 — Fast Python Tests (L1+L2+L3, with coverage)"
    local cov="$VENV/bin/coverage"
    "$cov" erase >/dev/null 2>&1 || true
    mkdir -p "$RUN_DIR/coverage" "$RUN_DIR/eda"

    local cov_run=("$cov" run -a "--source=controller/audit,filter_plugins")

    run_step "L1 reactor-unit" "eda/unit.log" \
        "${cov_run[@]}" controller/audit/test_reactor.py
    run_step "L2 rules-contract" "eda/contract.log" \
        "${cov_run[@]}" controller/audit/test_rules_contract.py
    run_step "L3 reactor-component" "eda/component.log" \
        "${cov_run[@]}" controller/audit/test_reactor_component.py

    run_step "L1 relay-unit" "eda/relay-unit.log" \
        "${cov_run[@]}" controller/audit/test_relay.py
    run_step "L1 sink-unit" "eda/sink-unit.log" \
        "${cov_run[@]}" controller/audit/test_sink.py
    run_step "L1 filters-unit" "eda/filters-unit.log" \
        "${cov_run[@]}" controller/audit/test_filters.py

    "$cov" report -m --omit="$COVERAGE_OMIT" >"$RUN_DIR/coverage/report.txt" 2>&1 || true
    "$cov" html --omit="$COVERAGE_OMIT" -d "$RUN_DIR/coverage/html" >/dev/null 2>&1 || true
    run_step "coverage --fail-under=${COVERAGE_MIN}" "coverage/threshold.log" \
        "$cov" report -m --omit="$COVERAGE_OMIT" --fail-under="$COVERAGE_MIN"
}

# ── 11. dry-run (L0+ static playbook compile) ───────────────────────────────
phase_dry_run() {
    [ "$MODE" = "quick" ] && return
    step "Phase 4 — Dry-run (ansible-playbook --check)"
    run_step "dry-run" "dry-run.log" make dry-run
}

# ── 12. molecule (L4) ───────────────────────────────────────────────────────
phase_molecule() {
    [ "$MODE" != "ci-equiv" ] && [ "$MODE" != "full" ] && [ "$MODE" != "exhaustive" ] && return
    step "Phase 5 — Molecule (L4, MOLECULE_PARALLEL=$MOLECULE_PARALLEL)"
    local scenarios=(common webserver database full-stack)

    if [ "$MOLECULE_PARALLEL" = "1" ]; then
        log "  WARN: molecule parallel mode is experimental; serial remains the supported evidence path"
        local pids=()
        for s in "${scenarios[@]}"; do
            ( run_step "molecule $s" "molecule/$s.log" "$VENV/bin/molecule" test -s "$s" ) & pids+=($!)
        done
        for p in "${pids[@]}"; do wait "$p" || true; done
    else
        for s in "${scenarios[@]}"; do
            run_step "molecule $s" "molecule/$s.log" "$VENV/bin/molecule" test -s "$s"
        done
    fi
}

# ── 13. EDA e2e (disposable docker; exhaustive only) ────────────────────────
phase_eda_e2e() {
    [ "$MODE" != "exhaustive" ] && return
    step "Phase 6 — EDA E2E (disposable docker stack)"
    E2E_RAN=1
    E2E_PROJECT_NAME="${E2E_PROJECT:-ansispire-e2e-$TS}"
    local e2e_semaphore_port e2e_audit_port
    e2e_semaphore_port="${E2E_SEMAPHORE_PORT:-$(find_free_port)}"
    e2e_audit_port="${E2E_AUDIT_PORT:-$(find_free_port)}"
    while [ "$e2e_audit_port" = "$e2e_semaphore_port" ]; do
        e2e_audit_port=$(find_free_port)
    done
    run_step "test-eda-e2e" "e2e/test-eda-e2e.log" env \
        E2E_PROJECT="$E2E_PROJECT_NAME" \
        E2E_SEMAPHORE_PORT="$e2e_semaphore_port" \
        E2E_AUDIT_PORT="$e2e_audit_port" \
        make test-eda-e2e
}

# ── 14. L5 smoke (control plane + audit relay) ──────────────────────────────
find_free_port() {
    python3 - <<'PY'
import socket

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.bind(("127.0.0.1", 0))
    print(sock.getsockname()[1])
PY
}

prepare_smoke_stack() {
    local semaphore_tag audit_tag
    semaphore_tag=$(grep -E '^SEMAPHORE_IMAGE_TAG=' controller/audit/e2e/.env.example | cut -d= -f2-)
    audit_tag=$(grep -E '^AUDIT_IMAGE_TAG=' controller/audit/e2e/.env.example | cut -d= -f2-)
    semaphore_tag=${semaphore_tag:-v2.18.2}
    audit_tag=${audit_tag:-3.12-alpine}

    SMOKE_PROJECT="ansispire-smoke-$TS"
    SMOKE_ENV="$WORKDIR/smoke.env"
    SMOKE_SECRETS="$WORKDIR/smoke.secrets"
    SMOKE_INVENTORY="$WORKDIR/hosts.smoke.ini"
    SMOKE_RBAC_DIR="$WORKDIR/rbac"
    SMOKE_NET="controller-net-smoke-$TS"
    SMOKE_SEMAPHORE_CONTAINER="ansispire-semaphore-smoke-$TS"
    SMOKE_SINK_CONTAINER="ansispire-audit-sink-smoke-$TS"
    SMOKE_RELAY_CONTAINER="ansispire-audit-relay-smoke-$TS"
    SMOKE_REACTOR_CONTAINER="ansispire-audit-reactor-smoke-$TS"
    SMOKE_SEMAPHORE_PORT=$(find_free_port)
    SMOKE_AUDIT_PORT=$(find_free_port)
    while [ "$SMOKE_AUDIT_PORT" = "$SMOKE_SEMAPHORE_PORT" ]; do
        SMOKE_AUDIT_PORT=$(find_free_port)
    done

    mkdir -p "$SMOKE_RBAC_DIR"
    : >"$SMOKE_SECRETS"
    cat >"$SMOKE_ENV" <<EOF
SEMAPHORE_PORT=$SMOKE_SEMAPHORE_PORT
AUDIT_PORT=$SMOKE_AUDIT_PORT
SEMAPHORE_IMAGE_TAG=$semaphore_tag
AUDIT_IMAGE_TAG=$audit_tag
SEMAPHORE_ADMIN=$SMOKE_ADMIN_USER
SEMAPHORE_ADMIN_PASSWORD=$SMOKE_ADMIN_PASSWORD
TZ=UTC
CONTROLLER_NET_NAME=$SMOKE_NET
SEMAPHORE_CONTAINER_NAME=$SMOKE_SEMAPHORE_CONTAINER
AUDIT_SINK_CONTAINER_NAME=$SMOKE_SINK_CONTAINER
AUDIT_RELAY_CONTAINER_NAME=$SMOKE_RELAY_CONTAINER
AUDIT_REACTOR_CONTAINER_NAME=$SMOKE_REACTOR_CONTAINER
EOF
    cat >"$SMOKE_INVENTORY" <<EOF
[all:vars]
ansible_connection=local
ansible_python_interpreter=/usr/bin/python3

[smoke]
localhost
EOF
    log "  smoke project: $SMOKE_PROJECT"
    log "  smoke semaphore: http://localhost:$SMOKE_SEMAPHORE_PORT"
    log "  smoke sink: http://127.0.0.1:$SMOKE_AUDIT_PORT/event"
}

smoke_compose() {
    docker compose -f "$E2E_COMPOSE_FILE" -p "$SMOKE_PROJECT" \
        --env-file "$SMOKE_ENV" --env-file "$SMOKE_SECRETS" "$@"
}

wait_smoke_semaphore() {
    local elapsed=0
    until curl -fsS "http://localhost:$SMOKE_SEMAPHORE_PORT/api/ping" >/dev/null 2>&1; do
        sleep 2
        elapsed=$((elapsed + 2))
        if [ "$elapsed" -ge "$SEMAPHORE_READY_TIMEOUT" ]; then
            echo "Semaphore did not respond on /api/ping in ${SEMAPHORE_READY_TIMEOUT}s"
            smoke_compose logs --tail=80 semaphore || true
            return 124
        fi
    done
    echo "Semaphore ready in ${elapsed}s"
}

reload_smoke_audit_services() {
    smoke_compose up -d --force-recreate audit-relay audit-reactor
    sleep 4
}

phase_smoke() {
    [ "$MODE" != "full" ] && [ "$MODE" != "exhaustive" ] && return
    step "Phase 7 — Isolated Control-plane Smoke (L5)"

    prepare_smoke_stack
    run_step "smoke compose clean" "smoke/clean.log" smoke_compose down -v --remove-orphans
    run_step "smoke compose up" "smoke/up.log" smoke_compose up -d
    if step_failed "smoke compose up"; then
        skip_step "smoke wait semaphore" "smoke/wait.log" "compose up failed"
        skip_step "smoke bootstrap" "smoke/bootstrap.log" "compose up failed"
        skip_step "rbac-smoke" "smoke/rbac.log" "compose up failed"
        skip_step "loop-smoke" "smoke/loop.log" "compose up failed"
        return
    fi

    run_step "smoke wait semaphore" "smoke/wait.log" wait_smoke_semaphore
    if step_failed "smoke wait semaphore"; then
        skip_step "smoke bootstrap" "smoke/bootstrap.log" "semaphore not ready"
        skip_step "rbac-smoke" "smoke/rbac.log" "semaphore not ready"
        skip_step "loop-smoke" "smoke/loop.log" "semaphore not ready"
        return
    fi

    run_step "smoke bootstrap" "smoke/bootstrap.log" \
        "$VENV/bin/ansible-playbook" controller/semaphore/bootstrap.yml \
        -i "$SMOKE_INVENTORY" \
        -e "semaphore_user=$SMOKE_ADMIN_USER" \
        -e "semaphore_password=$SMOKE_ADMIN_PASSWORD" \
        -e "semaphore_url=http://localhost:$SMOKE_SEMAPHORE_PORT" \
        -e "secrets_path=$SMOKE_SECRETS" \
        -e "rbac_dir=$SMOKE_RBAC_DIR" \
        -e "semaphore_inventory_path=inventory/hosts.ini"
    if step_failed "smoke bootstrap"; then
        skip_step "rbac-smoke" "smoke/rbac.log" "bootstrap failed"
        skip_step "smoke audit token reload" "smoke/audit-reload.log" "bootstrap failed"
        skip_step "loop-smoke" "smoke/loop.log" "bootstrap failed"
        return
    fi
    if ! grep -q '^SEMAPHORE_API_TOKEN=' "$SMOKE_SECRETS"; then
        printf 'FAIL\t%s\t%s\t%s\n' "smoke token" "smoke/bootstrap.log" "3" >>"$STATUS_FILE"
        log "  FAIL  bootstrap completed but did not write SEMAPHORE_API_TOKEN"
        skip_step "rbac-smoke" "smoke/rbac.log" "token missing"
        skip_step "loop-smoke" "smoke/loop.log" "token missing"
        return
    fi

    run_step "rbac-smoke" "smoke/rbac.log" env \
        SEMAPHORE_URL="http://localhost:$SMOKE_SEMAPHORE_PORT" \
        SEMAPHORE_ENV_FILE="$SMOKE_ENV" \
        SEMAPHORE_ADMIN_USER="$SMOKE_ADMIN_USER" \
        SEMAPHORE_ADMIN_PASSWORD="$SMOKE_ADMIN_PASSWORD" \
        RBAC_USERS_FILE="$SMOKE_RBAC_DIR/users.yml" \
        bash controller/rbac/smoke.sh

    run_step "smoke audit token reload" "smoke/audit-reload.log" reload_smoke_audit_services
    if step_failed "smoke audit token reload"; then
        skip_step "loop-smoke" "smoke/loop.log" "audit services failed to reload"
        return
    fi

    run_step "loop-smoke" "smoke/loop.log" env \
        SEMAPHORE_URL="http://localhost:$SMOKE_SEMAPHORE_PORT" \
        SEMAPHORE_ENV_FILE="$SMOKE_ENV" \
        SEMAPHORE_ADMIN_PASSWORD="$SMOKE_ADMIN_PASSWORD" \
        SINK_CONTAINER="$SMOKE_SINK_CONTAINER" \
        RELAY_CONTAINER="$SMOKE_RELAY_CONTAINER" \
        SMOKE_TIMEOUT="${SMOKE_TIMEOUT:-30}" \
        bash controller/audit/loop-smoke.sh
}

# ── 15. teardown (always; idempotent) ───────────────────────────────────────
teardown() {
    set +e
    step "Phase 8 — Teardown"
    {
        echo "[teardown] $(date)"
        if [ -n "$SMOKE_PROJECT" ] && [ -f "$SMOKE_ENV" ]; then
            docker compose -f "$E2E_COMPOSE_FILE" -p "$SMOKE_PROJECT" \
                --env-file "$SMOKE_ENV" --env-file "$SMOKE_SECRETS" \
                down -v --remove-orphans 2>&1 || true
        fi
        if [ "$E2E_RAN" = "1" ] && [ -f controller/audit/e2e/run.sh ]; then
            env E2E_PROJECT="${E2E_PROJECT_NAME:-ansispire-e2e}" \
                bash controller/audit/e2e/run.sh down 2>&1 || true
        fi
    } >>"$RUN_DIR/teardown.log" 2>&1
    [ -n "$WORKDIR" ] && [ -d "$WORKDIR" ] && rm -rf "$WORKDIR"
}

# ── 16. summary + history ───────────────────────────────────────────────────
generate_summary() {
    local summary="$RUN_DIR/SUMMARY.md"
    local duration=$(( $(date +%s) - START_EPOCH ))
    local pass_n fail_n
    pass_n=$(count_passes)
    fail_n=$(count_failures)

    {
        echo "# Loopback Run $TS"
        echo
        echo "| field    | value |"
        echo "|----------|-------|"
        echo "| Mode     | \`$MODE\` |"
        echo "| Duration | $((duration / 60))m $((duration % 60))s |"
        echo "| Passed   | $pass_n |"
        echo "| Failed   | $fail_n |"
        echo "| Project  | $PROJECT_ROOT |"
        echo "| Git HEAD | $(git rev-parse --short HEAD 2>/dev/null || echo n/a) |"
        echo "| Branch   | $(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo n/a) |"
        echo
        echo "## Results"
        echo
        echo "| status | step | log |"
        echo "|--------|------|-----|"
        if [ -f "$STATUS_FILE" ]; then
            while IFS=$'\t' read -r status label logname _; do
                local link="\`$logname\`"
                [ "$logname" = "-" ] && link="—"
                echo "| $status | $label | $link |"
            done <"$STATUS_FILE"
        fi
        echo
        if [ "$fail_n" -gt 0 ]; then
            echo "## Failure tails (last 30 lines per failed step)"
            echo
            while IFS=$'\t' read -r status label logname _rc; do
                [ "$status" = "FAIL" ] || continue
                local lp="$RUN_DIR/$logname"
                echo "### $label"
                echo
                if [ -f "$lp" ]; then
                    echo '```'
                    tail -n 30 "$lp"
                    echo '```'
                else
                    echo "_(log not captured)_"
                fi
                echo
            done <"$STATUS_FILE"
        fi
        if [ -f "$RUN_DIR/coverage/report.txt" ]; then
            echo "## Coverage report"
            echo
            echo '```'
            cat "$RUN_DIR/coverage/report.txt"
            echo '```'
        fi
    } >"$summary"
    log "Summary: $summary"
}

refresh_latest_symlink() {
    rm -f "$LATEST_LINK"
    ln -s "run-$TS" "$LATEST_LINK"
}

prune_history() {
    local keep="$LOOPBACK_HISTORY_KEEP"
    [ "$keep" -lt 1 ] && return
    # list newest first, skip the first $keep, delete the rest
    local victims
    victims=$(ls -1dt "$RESULTS_BASE"/run-* 2>/dev/null | tail -n +$((keep + 1)) || true)
    if [ -n "$victims" ]; then
        echo "$victims" | while read -r old; do
            rm -rf "$old"
            log "  pruned old run: $(basename "$old")"
        done
    fi
}

# ── 17. exit trap ───────────────────────────────────────────────────────────
on_exit() {
    local rc=$?
    set +e
    teardown
    generate_summary
    refresh_latest_symlink
    prune_history
    local fail_n
    fail_n=$(count_failures)
    log ""
    if [ "$rc" -eq 2 ]; then
        log "✗ ABORTED  (rc=$rc; preflight or fatal error)"
        exit "$rc"
    elif [ "$fail_n" -gt 0 ]; then
        log "✗ FAILED  ($fail_n step(s) failed)"
        log "  details: $RUN_DIR/SUMMARY.md"
        exit 1
    elif [ "$rc" -ne 0 ]; then
        log "✗ ABORTED  (rc=$rc)"
        exit "$rc"
    else
        log "✓ PASSED   $RUN_DIR/"
        exit 0
    fi
}

# ── 18. main ────────────────────────────────────────────────────────────────
mkdir -p "$RUN_DIR"
: >"$LOG"
: >"$STATUS_FILE"
trap on_exit EXIT INT TERM

log "═══ Ansispire Loopback Test Runner v2.0 ═══"
log "Mode:    $MODE"
log "Run dir: $RUN_DIR"
log "Project: $PROJECT_ROOT"

preflight
setup_isolation
bootstrap
phase_static
phase_eda
phase_dry_run
phase_molecule
phase_eda_e2e
phase_smoke
# trap on_exit handles teardown + summary + history
