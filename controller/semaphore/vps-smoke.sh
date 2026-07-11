#!/usr/bin/env bash
# controller/semaphore/vps-smoke.sh — Saberu managed-fleet audit smoke.
#
# Verifies the managed channel is healthy and the managed state is idempotent:
# runs the `VPS Audit` template against whatever `vps-fleet` currently points at
# (expected: onboarded hosts on their managed user/port) and asserts the task
# succeeds with changed=0 / failed=0 / unreachable=0 on every host. Drives the
# Semaphore REST API directly — no ansible-playbook on the host.
#
# This is the read-only companion to onboard (TSVS-VPS-ONBOARD-E2E-001). It does
# NOT run onboard (onboard is a takeover and not a repeatable smoke); it proves
# the already-managed fleet audits clean.
#
# Requires:
#   - Semaphore running (SEMAPHORE_URL, else derived from controller/semaphore/.env)
#   - controller-bootstrap has run (VPS Audit template exists)
#   - controller/semaphore/.secrets holds SEMAPHORE_API_TOKEN
#   - vps-fleet has at least one reachable host
#   - curl, jq, python3
#
# Exits non-zero on any expectation miss.

set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
env_file="${SEMAPHORE_ENV_FILE:-$here/.env}"
secrets_file="${SEMAPHORE_SECRETS_FILE:-$here/.secrets}"

port="3300"
[ -f "$env_file" ] && port="$(grep -E '^SEMAPHORE_PORT=' "$env_file" | cut -d= -f2 | tr -d '[:space:]' || true)"
SEM="${SEMAPHORE_URL:-http://localhost:${port:-3300}}"
PROJECT_ID="${SEMAPHORE_PROJECT_ID:-1}"

[ -f "$secrets_file" ] || { echo "FAIL: $secrets_file not found — run 'make controller-bootstrap' first" >&2; exit 1; }
TOKEN="$(grep -E '^SEMAPHORE_API_TOKEN=' "$secrets_file" | cut -d= -f2-)"
[ -n "$TOKEN" ] || { echo "FAIL: SEMAPHORE_API_TOKEN missing in $secrets_file" >&2; exit 1; }

api() { curl -fsS -H "Authorization: Bearer $TOKEN" "$@"; }

echo "==> vps-smoke: $SEM (project $PROJECT_ID)"

tpl_id="$(api "$SEM/api/project/$PROJECT_ID/templates" | jq -r '.[] | select(.name=="VPS Audit") | .id')"
[ -n "$tpl_id" ] && [ "$tpl_id" != "null" ] || { echo "FAIL: 'VPS Audit' template not found — run controller-bootstrap" >&2; exit 1; }

task_id="$(api -X POST -H 'Content-Type: application/json' \
  "$SEM/api/project/$PROJECT_ID/tasks" -d "{\"template_id\":$tpl_id}" | jq -r '.id')"
[ -n "$task_id" ] && [ "$task_id" != "null" ] || { echo "FAIL: could not start VPS Audit task" >&2; exit 1; }
echo "==> started VPS Audit task $task_id; polling..."

status="waiting"
for _ in $(seq 1 60); do
  status="$(api "$SEM/api/project/$PROJECT_ID/tasks/$task_id" | jq -r '.status')"
  case "$status" in success|error|stopped) break;; esac
  sleep 3
done
echo "==> task $task_id status=$status"
[ "$status" = success ] || { echo "FAIL: VPS Audit did not succeed (status=$status)" >&2; exit 1; }

# Parse the PLAY RECAP: every host must be changed=0 / failed=0 / unreachable=0,
# and there must be at least one host (an empty fleet is not a passing smoke).
api "$SEM/api/project/$PROJECT_ID/tasks/$task_id/output" \
  | jq -r '.[].output' \
  | sed -r 's/\x1b\[[0-9;]*m//g' \
  | python3 -c '
import re, sys
recap = False
hosts = 0
bad = []
for line in sys.stdin:
    if "PLAY RECAP" in line:
        recap = True
        continue
    if not recap:
        continue
    m = re.search(r"^(\S+)\s*:\s*ok=\d+\s+changed=(\d+)\s+unreachable=(\d+)\s+failed=(\d+)", line)
    if m:
        hosts += 1
        host, changed, unreach, failed = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))
        if changed or unreach or failed:
            bad.append(f"{host}: changed={changed} unreachable={unreach} failed={failed}")
if hosts == 0:
    print("FAIL: no hosts in PLAY RECAP — vps-fleet empty or unreachable", file=sys.stderr); sys.exit(1)
if bad:
    print("FAIL: managed fleet not idempotent/clean:", file=sys.stderr)
    for b in bad: print("  " + b, file=sys.stderr)
    sys.exit(1)
print(f"PASS: {hosts} host(s) audited clean (changed=0, failed=0, unreachable=0)")
'
