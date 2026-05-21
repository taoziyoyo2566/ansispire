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

# Wave-registration race — defense after codex rounds 4 + 6 + 7. Refined
# in this iteration to a single, honest invariant:
#
#   STABILITY INVARIANT (required for rc=0 exit):
#     1. elapsed >= MIN_SETTLE_SEC since watcher START_EPOCH; AND
#     2. The current poll AND the immediately-preceding poll were BOTH
#        all-green observations with the SAME name-set.
#
# "Immediately-preceding" is strict: if a pending/failed/error poll
# occurs between two all-green observations, the consecutiveness breaks
# and the stability counter resets. (Codex round 7 repro: all-green →
# pending → all-green would otherwise satisfy "two all-green sigs match"
# without being consecutive — that's the bug iter-6 fixes.)
#
# Implementation: prev_all_green_sig is cleared in EVERY non-rc=0 path
# (rc=99 pending, and the unexpected-rc abort which itself exits). Only
# rc=0 paths read or write it.
#
# Why both layers (settling AND consecutive stability):
#   - Settling alone is insufficient: someone could pass MIN_SETTLE_SEC=0;
#     defense-in-depth means consecutive stability still catches the bug.
#   - Stability alone is insufficient: codex round 4 demonstrated a stuck
#     partial wave (same partial set across many polls) could satisfy
#     stability without representing the full check set.
#
# Empirical: GitHub Actions matrix takes up to ~120s to fully register
# after `git push`; StatusContext (GitGuardian) often <5s. Default
# MIN_SETTLE_SEC=120 covers the slowest observed registration window.

PR="${1:-}"
INTERVAL="${2:-30}"
MAX_ITER="${3:-30}"
MIN_SETTLE_SEC="${MIN_SETTLE_SEC:-120}"
prev_all_green_sig=""  # written ONLY in rc=0 branches; cleared in rc=99
START_EPOCH=$(date +%s)

if [[ -z "$PR" ]]; then
  echo "Usage: $0 <PR_NUMBER> [INTERVAL_SEC=30] [MAX_ITER=30]" >&2
  echo "  env MIN_SETTLE_SEC=N (default 120) — wall-clock floor before rc=0 exit" >&2
  exit 1
fi

# Positive-integer validation for the three numeric inputs (codex round 7
# LOW finding). Catches: empty string, non-digit chars, leading zeroes/signs,
# and the dangerous INTERVAL=0 case (division-by-zero in min_required_iter).
# MIN_SETTLE_SEC=0 is explicitly allowed (it's the documented "disable
# settling" sentinel); everything else must be >= 1.
is_positive_int() { [[ "$1" =~ ^[1-9][0-9]*$ ]]; }
is_nonneg_int()   { [[ "$1" =~ ^(0|[1-9][0-9]*)$ ]]; }

if ! is_positive_int "$INTERVAL"; then
  echo "Error: INTERVAL must be a positive integer, got '$INTERVAL'" >&2
  exit 1
fi
if ! is_positive_int "$MAX_ITER"; then
  echo "Error: MAX_ITER must be a positive integer, got '$MAX_ITER'" >&2
  exit 1
fi
if ! is_nonneg_int "$MIN_SETTLE_SEC"; then
  echo "Error: MIN_SETTLE_SEC must be a non-negative integer, got '$MIN_SETTLE_SEC'" >&2
  exit 1
fi

# Sanity: INTERVAL + MIN_SETTLE_SEC vs MAX_ITER. Need at least enough polls
# to: (i) cover MIN_SETTLE_SEC, AND (ii) observe 2 CONSECUTIVE all-green
# polls (so floor is 2 even when settling is disabled).
settling_polls=$(( (MIN_SETTLE_SEC + INTERVAL - 1) / INTERVAL + 1 ))
min_required_iter=$(( settling_polls > 2 ? settling_polls : 2 ))
if (( MAX_ITER < min_required_iter )); then
  echo "Error: MAX_ITER=$MAX_ITER too small for INTERVAL=${INTERVAL}s + MIN_SETTLE_SEC=${MIN_SETTLE_SEC}s" >&2
  echo "       need MAX_ITER >= $min_required_iter (settling + 2 consecutive all-green polls)" >&2
  echo "       either raise MAX_ITER, raise INTERVAL, or set MIN_SETTLE_SEC=0 to disable settling" >&2
  echo "       (note: even with MIN_SETTLE_SEC=0, MAX_ITER >= 2 is required for stability)" >&2
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
    # Stability invariant (see header). BOTH must hold for rc=0 exit:
    #
    #   (a) elapsed >= MIN_SETTLE_SEC — guarantees we waited long enough
    #       for slow producers (e.g. GitHub Actions matrix taking ~120s)
    #       to register, regardless of what we observed in the meantime.
    #
    #   (b) current_sig == prev_all_green_sig with prev being the
    #       IMMEDIATELY-PRECEDING poll's sig (and that poll was also
    #       all-green). Because prev_all_green_sig is cleared on every
    #       rc=99 transition, a non-empty match here implies the prior
    #       poll was likewise all-green with the same name-set.
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
  # Clear prev_all_green_sig: stability requires CONSECUTIVE all-green polls.
  # A pending observation breaks the chain — the next all-green poll starts
  # a fresh consecutive count. Codex round 7 repro: without this clear,
  # "all-green → pending → all-green" satisfies sig-match across two
  # all-green observations that were NOT consecutive, which is the bug
  # (codex finding line 180 / 201). The invariant in the header says
  # "immediately-preceding poll was all-green"; this line enforces it.
  prev_all_green_sig=""
  sleep "$INTERVAL"
done

echo "TIMEOUT after ${MAX_ITER} iterations (${INTERVAL}s each)"
exit 1
