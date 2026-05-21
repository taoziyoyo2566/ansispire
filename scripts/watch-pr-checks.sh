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

# Wave-registration race — TWO-LAYER defense (W-R15 attack category j refined
# after codex rounds 4 + 6):
#
# Different check producers register at different times after a push.
# Empirical observation on this repo: GitHub Actions matrix can take up
# to ~120s to fully register after `git push`, while StatusContext entries
# (e.g. GitGuardian) often appear within 5s. A naive "0 pending + all
# SUCCESS" check on the early partial wave produces a false-green.
#
# Codex round 4 fix tried name-set stability across 2 polls. Codex round 6
# repro showed it was insufficient: if iter-1 sees {GG=PENDING} and iter-2
# sees {GG=SUCCESS}, the *sig* is identical across polls but the set is
# still partial. The bug: prev_sig was updated on every iteration, so two
# observations of the same partial wave could pass the "stable" check.
#
# Real defense (this iteration):
#   (a) MIN_SETTLE_SEC — minimum wall-clock seconds since watch start before
#       any rc=0 exit. Set to 120s based on observed registration latency.
#       Eliminates the "fast partial wave passes before slow wave even
#       registers" class entirely (independent of name-set logic).
#   (b) prev_all_green_sig — tracked SEPARATELY from any pending-state
#       observation. Only updated in the rc=0 branch. Ensures the "stable
#       across 2 polls" requirement counts only consecutive ALL-GREEN
#       observations, not pending-then-success transitions.
#   (c) MAX_ITER lower bound — with min 2 all-green polls and MIN_SETTLE_SEC,
#       MAX_ITER must allow at least ceil(MIN_SETTLE_SEC/INTERVAL)+1 polls.
#       Reject smaller MAX_ITER upfront rather than guaranteeing timeout.

PR="${1:-}"
INTERVAL="${2:-30}"
MAX_ITER="${3:-30}"
MIN_SETTLE_SEC="${MIN_SETTLE_SEC:-120}"
prev_all_green_sig=""  # ONLY updated inside the rc=0 branch
START_EPOCH=$(date +%s)

if [[ -z "$PR" ]]; then
  echo "Usage: $0 <PR_NUMBER> [INTERVAL_SEC=30] [MAX_ITER=30]" >&2
  echo "  env MIN_SETTLE_SEC=N (default 120) — wall-clock floor before rc=0 exit" >&2
  exit 1
fi

# Sanity: INTERVAL + MIN_SETTLE_SEC vs MAX_ITER. Need at least enough polls
# to: (i) cover MIN_SETTLE_SEC, AND (ii) observe 2 consecutive all-green polls.
min_required_iter=$(( (MIN_SETTLE_SEC + INTERVAL - 1) / INTERVAL + 1 ))
if (( MAX_ITER < min_required_iter )); then
  echo "Error: MAX_ITER=$MAX_ITER too small for INTERVAL=${INTERVAL}s + MIN_SETTLE_SEC=${MIN_SETTLE_SEC}s" >&2
  echo "       need MAX_ITER >= $min_required_iter (settling + 2-poll stability needs that many polls)" >&2
  echo "       either raise MAX_ITER, raise INTERVAL, or set MIN_SETTLE_SEC=0 to disable settling" >&2
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
# statusCheckRollup mixes two entry shapes:
#   CheckRun       — Actions / Check API; carries 'conclusion' (terminal) and
#                    'status' (running state). conclusion=None means not done.
#   StatusContext  — Commit Statuses API / branch-protection external; carries
#                    'state' instead. state in {PENDING, EXPECTED} = not done;
#                    {SUCCESS, FAILURE, ERROR} = terminal.
# OK terminal states across both: SUCCESS, SKIPPED, NEUTRAL (CheckRun-only;
# StatusContext does not emit SKIPPED/NEUTRAL).
OK_TERMINAL = {'SUCCESS', 'SKIPPED', 'NEUTRAL'}
PENDING_STATES = {'PENDING', 'EXPECTED'}

def terminal(c):
    # Prefer CheckRun's conclusion if set
    if c.get('conclusion'):
        return c['conclusion']
    # Fall back to StatusContext's state, unless still pending
    s = c.get('state')
    if s and s not in PENDING_STATES:
        return s
    return None

def display(c):
    return c.get('conclusion') or c.get('state') or c.get('status') or '?'

def name(c):
    # CheckRun → 'name'; StatusContext → 'context'; defensive fallback for
    # unexpected entry shapes so a KeyError doesn't silently become a timeout.
    return c.get('name') or c.get('context') or '?'

d=json.load(sys.stdin)
checks=d.get('statusCheckRollup', [])
total=len(checks)
# Empty rollup right after push = workflow runs not yet registered. Treat
# as 'still pending' — declaring green on total=0 was a prior bug.
if total == 0:
    print('0/0 done (workflow runs not yet registered)', end='')
    print()
    sys.exit(99)
terms = [terminal(c) for c in checks]
done = sum(1 for t in terms if t is not None)
pending = total - done
failures = [name(c) for c, t in zip(checks, terms) if t and t not in OK_TERMINAL]
# Emit the sorted name-set on its own line — bash side uses it for the
# wave-registration stability check. Emitted unconditionally (i.e. in BOTH
# pending and all-done branches) so prev_sig stays meaningful across the
# transition into the all-done state.
sorted_names = sorted(name(c) for c in checks)
print('__NAMES__:' + ','.join(sorted_names))
print(f'{done}/{total} done, {pending} pending, {len(failures)} fail', end='')
if pending == 0:
    print()
    # Sort: failures first, then by name
    for c, t in sorted(zip(checks, terms), key=lambda p: (p[1] in OK_TERMINAL, name(p[0]))):
        print(f\"  {display(c):14} {name(c)}\")
    sys.exit(0 if not failures else 2)
print()
sys.exit(99)
")
  rc=$?
  ts=$(date -u +%H:%M:%S)
  # Split __NAMES__: signal line (if any) from the user-facing display.
  current_sig=$(printf '%s\n' "$result" | sed -n 's/^__NAMES__://p')
  result_display=$(printf '%s\n' "$result" | grep -v '^__NAMES__:')
  now_epoch=$(date +%s)
  elapsed=$(( now_epoch - START_EPOCH ))
  echo "[${ts}] iter=${i} (t+${elapsed}s): ${result_display}"

  if [[ $rc -eq 0 ]]; then
    # Two-layer wave-registration defense (see header comment for full
    # rationale). BOTH must hold for rc=0 exit:
    #
    #   (a) elapsed >= MIN_SETTLE_SEC — guarantees we waited long enough
    #       for slow producers (e.g. GitHub Actions matrix taking ~120s)
    #       to register, regardless of what we observed in the meantime.
    #
    #   (b) current_sig == prev_all_green_sig — two consecutive all-green
    #       observations with the same name-set. prev_all_green_sig is
    #       updated ONLY in this branch (never in rc=99/pending), so two
    #       observations of the same partial wave with pending-then-success
    #       transition cannot pass this check (codex round 6 repro).
    if (( elapsed < MIN_SETTLE_SEC )); then
      echo "  (all green observed, but only ${elapsed}s elapsed since start — waiting until t+${MIN_SETTLE_SEC}s)"
      prev_all_green_sig="$current_sig"
      sleep "$INTERVAL"
      continue
    fi
    if [[ -n "$current_sig" && "$current_sig" == "$prev_all_green_sig" ]]; then
      echo "FINAL: all checks green (settled t+${elapsed}s, name-set stable across 2 all-green polls)"
      exit 0
    fi
    echo "  (all green, but name-set not yet stable across 2 all-green polls — waiting)"
    prev_all_green_sig="$current_sig"
    sleep "$INTERVAL"
    continue
  elif [[ $rc -eq 2 ]]; then
    # Failures are reported immediately regardless of settling — a confirmed
    # FAILURE/ERROR is a terminal state, not an early observation that might
    # be revised by later registrations.
    echo "FINAL: at least one check failed (t+${elapsed}s)"
    exit 2
  elif [[ $rc -ne 99 ]]; then
    # Unexpected rc (Python crash, KeyError, gh failure piped to corrupt JSON,
    # etc.) — fail fast instead of silently treating as 'still pending' and
    # waiting out MAX_ITER.
    echo "FINAL: watcher exited unexpectedly (rc=$rc); aborting watch" >&2
    exit "$rc"
  fi
  # rc == 99 means still pending.
  # CRITICAL: do NOT touch prev_all_green_sig here — that would re-introduce
  # the codex-round-6 partial-wave-stable bug. Pending observations are not
  # evidence of name-set stability for the all-green decision.
  sleep "$INTERVAL"
done

echo "TIMEOUT after ${MAX_ITER} iterations (${INTERVAL}s each)"
exit 1
