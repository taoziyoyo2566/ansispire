#!/usr/bin/env bash
# scripts/push-and-watch-pr.sh — push current branch + watch the corresponding PR's CI.
#
# Designed as a single "fire and continue" workflow: invoke this via your
# agent's background-task mechanism, get on with the next piece of work,
# and let the notification fire when CI either goes green, fails, or
# times out.
#
# Usage:
#   ./scripts/push-and-watch-pr.sh                       # auto-detect PR from current branch
#   ./scripts/push-and-watch-pr.sh <PR_NUMBER>           # explicit PR (skip auto-detect)
#   ./scripts/push-and-watch-pr.sh <PR_NUMBER> <INTERVAL_SEC> <MAX_ITER>
#
# Behavior:
#   1. `git push` (sets upstream automatically if missing via --set-upstream)
#   2. Auto-detects PR number from current branch via `gh pr view`
#      (unless explicitly passed). Aborts if no PR exists for the branch.
#   3. Delegates to watch-pr-checks.sh (same dir) for the polling loop.
#
# Exit codes:
#   0 — push succeeded AND all checks green
#   1 — push failed, OR no PR found, OR timeout
#   2 — push succeeded but at least one check failed
#
# Requires: git, gh (authed), python3 (used by watch-pr-checks.sh).

set -u

PR_ARG="${1:-}"
INTERVAL="${2:-30}"
MAX_ITER="${3:-30}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WATCH="$SCRIPT_DIR/watch-pr-checks.sh"

if [[ ! -x "$WATCH" ]]; then
  echo "Error: companion script not found or not executable: $WATCH" >&2
  exit 1
fi

# Step 1: push
BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if [[ "$BRANCH" == "HEAD" ]]; then
  echo "Error: detached HEAD; refusing to push" >&2
  exit 1
fi

echo "── Step 1/2: push branch '$BRANCH' ─────────────────────────────"
if git rev-parse --abbrev-ref --symbolic-full-name "@{u}" >/dev/null 2>&1; then
  git push
else
  echo "(no upstream set; using --set-upstream)"
  git push --set-upstream origin "$BRANCH"
fi
push_rc=$?
if [[ $push_rc -ne 0 ]]; then
  echo "Error: git push failed (rc=$push_rc)" >&2
  exit 1
fi

# Step 2: resolve PR number
if [[ -n "$PR_ARG" ]]; then
  PR_NUM="$PR_ARG"
  echo "── Step 2/2: watch PR #$PR_NUM (explicit) ─────────────────"
else
  PR_NUM="$(gh pr view --json number -q .number 2>/dev/null || true)"
  if [[ -z "$PR_NUM" ]]; then
    echo "Error: no PR found for branch '$BRANCH'. Open one first or pass PR# explicitly." >&2
    exit 1
  fi
  echo "── Step 2/2: watch PR #$PR_NUM (auto-detected from '$BRANCH') ──"
fi

# Step 3: delegate
exec "$WATCH" "$PR_NUM" "$INTERVAL" "$MAX_ITER"
