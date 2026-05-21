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
#   EXPECTED_CHECKS="lint,test,build" ./scripts/watch-pr-checks.sh 15
#                                                       # explicit authoritative mode
#
# Authoritative-vs-heuristic mode (codex round 8 fix):
#
#   L1 — branch protection: if `gh api repos/:o/:r/branches/$base/protection/
#        required_status_checks` returns a non-empty `.contexts` list (branch
#        protection is configured AND caller has permission to read it), use
#        that as the expected set. This is the authoritative GitHub-side
#        merge gate.
#   L2 — EXPECTED_CHECKS env var: comma-separated list of names. Use this when
#        branch protection is not configured or readable. Note: names may
#        contain '/' and spaces (matrix check IDs); commas in names are not
#        supported (workaround: use EXPECTED_CHECKS_FILE — one name per line).
#   L3 — heuristic mode: when neither L1 nor L2 yields names, fall back to
#        the empirical settle-time + name-set stability defense. A clear
#        `[HEURISTIC]` warning is printed up-front. Suitable for progress-
#        watching, NOT for use as the only merge gate.
#
# Exit codes:
#   0 — all checks completed successfully
#   1 — timeout (MAX_ITER reached) OR missing dependencies / bad args
#   2 — at least one (expected, in authoritative mode) check reported FAILURE
#
# Output format per iteration:
#   [HH:MM:SS] iter=N (t+Ns): A/B done, C pending, D fail
# Final iteration also prints per-check status sorted (failures first).
#
# Requires: gh (authed), python3.

set -u  # NOT -e — Python's exit code is a signal here, not an error

# STABILITY INVARIANT (required for rc=0 exit) — refined through codex
# rounds 4 / 6 / 7 / 8:
#
#   1. elapsed >= MIN_SETTLE_SEC since watcher START_EPOCH; AND
#   2. The current poll AND the immediately-preceding poll were BOTH
#      all-green observations with the SAME name-set; AND
#   3. (Authoritative modes only) the observed all-green name-set equals
#      the resolved EXPECTED set.
#
# Mode (L1 → L2 → L3, see usage block):
#   - branch-protection / env / env-file → "expected set" is known a priori,
#     and rc=0 requires it to be observed-and-OK. MIN_SETTLE_SEC defaults
#     to 30s (small buffer for transient GitHub state flips).
#   - heuristic → no expected set; defense degrades to empirical settling
#     time + name-set stability. MIN_SETTLE_SEC defaults to 120s
#     (covers observed registration latency on this repo). A clear
#     [HEURISTIC] banner is printed; this mode is suitable for progress
#     watching but NOT as the sole merge gate.
#
# "Immediately-preceding" is strict (rounds 7 + 6): prev_all_green_sig is
# CLEARED on every rc=99 (pending) observation, so a pending dip resets
# the consecutive-pair counter.
#
# Why both invariants (settling AND consecutive stability) even in
# authoritative mode: 2-poll stability defends against transient flips
# (e.g. GitHub momentarily reporting a re-run as pending).

PR="${1:-}"
INTERVAL="${2:-30}"
MAX_ITER="${3:-30}"
# MIN_SETTLE_SEC default is mode-dependent — assigned after mode resolution.
prev_all_green_sig=""  # written ONLY in rc=0 branches; cleared in rc=99
START_EPOCH=$(date +%s)

if [[ -z "$PR" ]]; then
  echo "Usage: $0 <PR_NUMBER> [INTERVAL_SEC=30] [MAX_ITER=30]" >&2
  echo "  env EXPECTED_CHECKS=name1,name2 — explicit authoritative mode (L2)" >&2
  echo "  env EXPECTED_CHECKS_FILE=path  — same as above, one name per line" >&2
  echo "  env MIN_SETTLE_SEC=N (default 120 heuristic / 30 authoritative)" >&2
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
# MIN_SETTLE_SEC validated later (after mode resolution sets default).

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

# === Expected-checks resolution (3-layer: L1 branch protection → L2 env → L3 heuristic) ===
#
# Output: EXPECTED_NL (newline-separated list, empty in heuristic mode) and
# MODE (one of: branch-protection, env, env-file, heuristic).
EXPECTED_NL=""
MODE="heuristic"

# L2-file: EXPECTED_CHECKS_FILE — one name per line, accommodates names with commas
if [[ -n "${EXPECTED_CHECKS_FILE:-}" ]]; then
  if [[ ! -f "$EXPECTED_CHECKS_FILE" ]]; then
    echo "Error: EXPECTED_CHECKS_FILE='$EXPECTED_CHECKS_FILE' does not exist" >&2
    exit 1
  fi
  EXPECTED_NL=$(grep -v '^[[:space:]]*$\|^[[:space:]]*#' "$EXPECTED_CHECKS_FILE")
  MODE="env-file"
elif [[ -n "${EXPECTED_CHECKS:-}" ]]; then
  # L2: comma-separated env var
  EXPECTED_NL=$(printf '%s' "$EXPECTED_CHECKS" | tr ',' '\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | grep -v '^$')
  MODE="env"
else
  # L1: try branch protection. Need the PR's base branch and the repo nwo.
  base=$(gh pr view "$PR" --json baseRefName -q .baseRefName 2>/dev/null || true)
  nwo=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || true)
  if [[ -n "$base" && -n "$nwo" ]]; then
    # 404 (no protection) and 403 (no permission) are both expected — fall through.
    protection_json=$(gh api "repos/${nwo}/branches/${base}/protection/required_status_checks" 2>/dev/null || true)
    if [[ -n "$protection_json" ]]; then
      EXPECTED_NL=$(printf '%s' "$protection_json" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
# .contexts (legacy) or .checks[].context (newer) — try both
names = list(d.get("contexts") or [])
for c in d.get("checks") or []:
    n = c.get("context")
    if n and n not in names:
        names.append(n)
for n in sorted(names):
    print(n)
')
      if [[ -n "$EXPECTED_NL" ]]; then
        MODE="branch-protection"
      fi
    fi
  fi
fi

# Mode-dependent default for MIN_SETTLE_SEC. Authoritative mode doesn't need
# a long settle (we wait for explicit names, not for slow producers to "maybe"
# register). Heuristic keeps 120s. User-set env overrides either default.
if [[ -z "${MIN_SETTLE_SEC+set}" ]]; then
  if [[ "$MODE" == "heuristic" ]]; then
    MIN_SETTLE_SEC=120
  else
    MIN_SETTLE_SEC=30
  fi
fi
if ! is_nonneg_int "$MIN_SETTLE_SEC"; then
  echo "Error: MIN_SETTLE_SEC must be a non-negative integer, got '$MIN_SETTLE_SEC'" >&2
  exit 1
fi

# Re-check MAX_ITER lower bound with the (possibly mode-adjusted) MIN_SETTLE_SEC.
settling_polls=$(( (MIN_SETTLE_SEC + INTERVAL - 1) / INTERVAL + 1 ))
min_required_iter=$(( settling_polls > 2 ? settling_polls : 2 ))
if (( MAX_ITER < min_required_iter )); then
  echo "Error: MAX_ITER=$MAX_ITER too small for INTERVAL=${INTERVAL}s + MIN_SETTLE_SEC=${MIN_SETTLE_SEC}s" >&2
  echo "       need MAX_ITER >= $min_required_iter (settling + 2 consecutive all-green polls)" >&2
  exit 1
fi

# Banner: tell the operator which mode we're in.
if [[ "$MODE" == "heuristic" ]]; then
  echo "[HEURISTIC] no branch protection / EXPECTED_CHECKS — falling back to empirical settle (${MIN_SETTLE_SEC}s) + name-set stability." >&2
  echo "[HEURISTIC] safe for progress-watching; NOT authoritative as a merge gate. Set EXPECTED_CHECKS or configure branch protection for L1/L2." >&2
else
  echo "[$MODE] expected checks ($(printf '%s\n' "$EXPECTED_NL" | wc -l | tr -d ' ')):" >&2
  printf '%s\n' "$EXPECTED_NL" | sed 's/^/  /' >&2
fi

export EXPECTED_NL  # Make available to the python3 subprocess inside the loop
                    # (without export, the inline `var=value cmd1 | cmd2` form
                    # would only set the var for cmd1, leaving python3 blind).

for ((i=1; i<=MAX_ITER; i++)); do
  result=$(gh pr view "$PR" --json statusCheckRollup 2>/dev/null | python3 -c "
import json, os, sys
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

# Authoritative-mode expected set (codex round 8 fix). When non-empty:
# the gate is 'all EXPECTED names present + all OK terminal', not just
# 'no pending'. When empty: heuristic mode — same as before.
EXPECTED = set()
for n in (os.environ.get('EXPECTED_NL') or '').split('\n'):
    n = n.strip()
    if n:
        EXPECTED.add(n)
AUTHORITATIVE = bool(EXPECTED)

def terminal(c):
    if c.get('conclusion'):
        return c['conclusion']
    s = c.get('state')
    if s and s not in PENDING_STATES:
        return s
    return None

def display(c):
    return c.get('conclusion') or c.get('state') or c.get('status') or '?'

def name(c):
    return c.get('name') or c.get('context') or '?'

d = json.load(sys.stdin)
checks = d.get('statusCheckRollup', [])
total = len(checks)
if total == 0:
    print('0/0 done (workflow runs not yet registered)', end='')
    print()
    sys.exit(99)
terms = [terminal(c) for c in checks]
done = sum(1 for t in terms if t is not None)
pending_count = total - done

if AUTHORITATIVE:
    # Build name -> (terminal, check) map. Same name twice = take the latest
    # observation (rare; happens with re-runs).
    by_name = {}
    for c, t in zip(checks, terms):
        by_name[name(c)] = (t, c)
    missing = sorted(EXPECTED - by_name.keys())
    expected_failed = []
    expected_pending = []
    for n in EXPECTED:
        if n not in by_name:
            continue
        t, _ = by_name[n]
        if t is None:
            expected_pending.append(n)
        elif t not in OK_TERMINAL:
            expected_failed.append(n)
    # Emit sorted name-set of EXPECTED checks observed so far (drives the
    # consecutive-stability check on the bash side). Note: we still use
    # \"is this set stable\" because even with authoritative gating, two
    # consecutive observations defend against transient GitHub state flips.
    observed_expected = sorted(EXPECTED & by_name.keys())
    print('__NAMES__:' + ','.join(observed_expected))
    extras = sorted(by_name.keys() - EXPECTED)
    extras_note = f' (+{len(extras)} extra)' if extras else ''
    print(f'expected: {len(observed_expected)}/{len(EXPECTED)} present, '
          f'{len(expected_pending)} pending, {len(expected_failed)} fail{extras_note}', end='')
    if expected_failed:
        print()
        # Show failed expected checks first, then pending, then OK expected, then extras
        for n in expected_failed + expected_pending:
            t, c = by_name[n]
            print(f'  {display(c):14} {n}')
        sys.exit(2)
    if missing or expected_pending:
        print()
        sys.exit(99)
    # All expected present and OK. Print the OK list (and extras for info).
    print()
    for n in sorted(EXPECTED):
        t, c = by_name[n]
        print(f'  {display(c):14} {n}')
    if extras:
        print('  --- extras (not in expected set; not gated) ---')
        for n in extras:
            t, c = by_name[n]
            print(f'  {display(c):14} {n}')
    sys.exit(0)

# Heuristic mode — pre-round-8 behavior.
failures = [name(c) for c, t in zip(checks, terms) if t and t not in OK_TERMINAL]
sorted_names = sorted(name(c) for c in checks)
print('__NAMES__:' + ','.join(sorted_names))
print(f'{done}/{total} done, {pending_count} pending, {len(failures)} fail', end='')
if pending_count == 0:
    print()
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
