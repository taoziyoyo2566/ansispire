#!/usr/bin/env bash
# scripts/watch-pr-checks.sh — poll GitHub PR checks until all complete.
#
# Usage:
#   ./scripts/watch-pr-checks.sh <PR_NUMBER> [INTERVAL_SEC=30] [MAX_ITER=30]
#
# Examples:
#   ./scripts/watch-pr-checks.sh 15                    # default: poll PR 15 every 30s, up to 15 min
#   ./scripts/watch-pr-checks.sh 15 60 60               # poll every 60s, up to 60 min
#
# Exit codes:
#   0 — all checks completed successfully
#   1 — timeout (MAX_ITER reached) OR missing dependencies
#   2 — at least one check reported FAILURE
#
# Output format per iteration:
#   [HH:MM:SS] iter=N: A/B done, C pending, D fail
# Final iteration also prints per-check status sorted (failures first).
#
# Requires: gh (authed), python3.

set -u  # NOT -e — Python's exit code is a signal here, not an error

PR="${1:-}"
INTERVAL="${2:-30}"
MAX_ITER="${3:-30}"

if [[ -z "$PR" ]]; then
  echo "Usage: $0 <PR_NUMBER> [INTERVAL_SEC=30] [MAX_ITER=30]" >&2
  exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "Error: gh CLI not found (or not on PATH)" >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: python3 not found" >&2
  exit 1
fi

# Sanity: PR must exist
if ! gh pr view "$PR" --json number >/dev/null 2>&1; then
  echo "Error: PR #$PR not found in current repo" >&2
  exit 1
fi

for ((i=1; i<=MAX_ITER; i++)); do
  result=$(gh pr view "$PR" --json statusCheckRollup 2>/dev/null | python3 -c "
import json,sys
d=json.load(sys.stdin)
checks=d.get('statusCheckRollup', [])
done=sum(1 for c in checks if c.get('conclusion'))
pending=sum(1 for c in checks if not c.get('conclusion'))
total=len(checks)
failures=[c['name'] for c in checks if c.get('conclusion')=='FAILURE']
print(f'{done}/{total} done, {pending} pending, {len(failures)} fail', end='')
if pending == 0:
    print()
    # Sort: failures first, then by name
    for c in sorted(checks, key=lambda x: (x.get('conclusion','')!='FAILURE', x['name'])):
        print(f\"  {(c.get('conclusion') or c['status']):12} {c['name']}\")
    sys.exit(0 if not failures else 2)
print()
sys.exit(99)
")
  rc=$?
  ts=$(date -u +%H:%M:%S)
  echo "[${ts}] iter=${i}: ${result}"

  if [[ $rc -eq 0 ]]; then
    echo "FINAL: all checks green"
    exit 0
  elif [[ $rc -eq 2 ]]; then
    echo "FINAL: at least one check failed"
    exit 2
  fi
  # rc == 99 means still pending; continue
  sleep "$INTERVAL"
done

echo "TIMEOUT after ${MAX_ITER} iterations (${INTERVAL}s each)"
exit 1
