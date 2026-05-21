#!/usr/bin/env bash
# scripts/archive_branch.sh — execute the CLAUDE.md §4 archive recipe with safety guards.
#
# After a merged PR closes, this script replaces the hand-edited git
# tag/push/delete sequence so the dangerous part (`git push origin :<branch>`)
# cannot be retargeted by a typo or by an agent that copied the wrong recipe.
#
# Usage:
#   ./scripts/archive_branch.sh <BRANCH> <MERGE_TARGET> <PR_NUMBER>
#
# Example:
#   ./scripts/archive_branch.sh feat/foo dev 17
#   ./scripts/archive_branch.sh fix/bar feat/foo 18
#
# Behavior (in order):
#   1. Validate three positional args.
#   2. Reject if BRANCH is a trunk-protected name (dev/master/main).
#   3. Reject if working tree is dirty.
#   4. Reject if currently checked out on BRANCH.
#   5. Fetch + verify origin/MERGE_TARGET and origin/BRANCH both exist.
#   6. Verify branch is merged into MERGE_TARGET via EITHER:
#      (a) ancestor check — origin/BRANCH tip is reachable from MERGE_TARGET
#          (true-merge case, no GitHub round-trip needed), OR
#      (b) PR cross-check — `gh pr view PR_NUMBER` confirms ALL THREE:
#          state=MERGED, headRefName=BRANCH, baseRefName=MERGE_TARGET
#          (squash-merge case; state alone is NOT enough — a merged PR for a
#          different branch does not authorize deleting this branch).
#   7. Compute archive tag: archive/<branch-slash-to-dash>-<YYYY-MM-DD>.
#   8. Refuse to overwrite an existing archive tag (no-clobber).
#   9. Create annotated tag at origin/BRANCH's tip.
#  10. Push tag to origin.
#  11. Push :BRANCH to origin (delete remote ref).
#  12. Delete local BRANCH if it exists locally.
#
# Exit codes:
#   0 — archived successfully.
#   1 — usage / validation error (no destructive action taken).
#   2 — git operation failed mid-way (output describes which step).

set -uo pipefail

usage() {
  echo "Usage: $0 <BRANCH> <MERGE_TARGET> <PR_NUMBER>" >&2
  echo "" >&2
  echo "  BRANCH        the merged branch to archive (e.g. feat/foo or fix/bar)" >&2
  echo "  MERGE_TARGET  branch the work landed on (e.g. dev for feat/, feat/parent for fix/)" >&2
  echo "  PR_NUMBER     the PR number for the annotation message" >&2
  exit 1
}

[[ $# -eq 3 ]] || usage
BRANCH="$1"
TARGET="$2"
PR_NUM="$3"

# Guard 1: Trunk-protected names
case "$BRANCH" in
  dev|master|main|stg|todo|HEAD)
    echo "Error: refusing to archive trunk-protected branch '$BRANCH'" >&2
    exit 1
    ;;
esac

# Guard 2: PR_NUMBER looks numeric
if ! [[ "$PR_NUM" =~ ^[0-9]+$ ]]; then
  echo "Error: PR_NUMBER must be numeric, got '$PR_NUM'" >&2
  exit 1
fi

# Guard 3: Inside a git working tree
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Error: not inside a git working tree" >&2
  exit 1
fi

cd "$(git rev-parse --show-toplevel)"

# Guard 4: Working tree clean
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "Error: working tree is dirty. Commit or stash first." >&2
  exit 1
fi

# Guard 5: Not currently on the branch
current=$(git rev-parse --abbrev-ref HEAD)
if [[ "$current" == "$BRANCH" ]]; then
  echo "Error: currently on '$BRANCH'. Switch to '$TARGET' (or any other branch) first." >&2
  exit 1
fi

# Guard 6: Refresh refs from origin
echo "── Fetching origin..."
if ! git fetch --quiet origin; then
  echo "Error: git fetch origin failed" >&2
  exit 2
fi

# Guard 7: Both refs exist on origin
if ! git rev-parse --verify --quiet "origin/$BRANCH" >/dev/null; then
  echo "Error: origin/$BRANCH does not exist (already archived?)" >&2
  exit 1
fi
if ! git rev-parse --verify --quiet "origin/$TARGET" >/dev/null; then
  echo "Error: origin/$TARGET does not exist" >&2
  exit 1
fi

TIP=$(git rev-parse "origin/$BRANCH")

# Guard 8: branch is actually merged
# Two acceptance paths:
#   (a) tip is an ancestor of target — true-merge fast path, works without `gh`.
#   (b) GitHub PR check via `gh pr view PR_NUM` — squash-merge path. To prevent
#       a typo or copy-paste error from archiving the wrong branch, the PR
#       must satisfy ALL THREE: state=MERGED, headRefName=BRANCH, baseRefName
#       =TARGET. State alone is NOT enough — a merged PR for a different branch
#       does not authorize deleting THIS branch.
# Anything else: refuse.
if git merge-base --is-ancestor "$TIP" "origin/$TARGET" 2>/dev/null; then
  echo "── '$BRANCH' is merged into '$TARGET' (true merge ancestry)"
else
  if ! command -v gh >/dev/null 2>&1; then
    echo "Error: '$BRANCH' tip is not an ancestor of '$TARGET' and 'gh' CLI is unavailable" >&2
    echo "       cannot verify squash-merge state without GitHub PR lookup" >&2
    exit 1
  fi
  pr_info=$(gh pr view "$PR_NUM" \
              --json state,headRefName,baseRefName \
              -q '[.state, .headRefName, .baseRefName] | @tsv' 2>/dev/null || true)
  if [[ -z "$pr_info" ]]; then
    echo "Error: 'gh pr view $PR_NUM' returned no data" >&2
    echo "       PR may not exist, gh may be unauthed, or network failed" >&2
    exit 1
  fi
  IFS=$'\t' read -r pr_state pr_head pr_base <<<"$pr_info"
  if [[ "$pr_state" != "MERGED" ]]; then
    echo "Error: PR #$PR_NUM state is '${pr_state:-unknown}' (expected MERGED)" >&2
    echo "       ancestor check also failed: tip is not an ancestor of origin/$TARGET" >&2
    exit 1
  fi
  if [[ "$pr_head" != "$BRANCH" ]]; then
    echo "Error: PR #$PR_NUM head branch is '$pr_head', not '$BRANCH'" >&2
    echo "       refusing to archive '$BRANCH' based on a PR for a different branch" >&2
    exit 1
  fi
  if [[ "$pr_base" != "$TARGET" ]]; then
    echo "Error: PR #$PR_NUM merged into '$pr_base', not '$TARGET'" >&2
    echo "       refusing to archive: archive metadata would be wrong" >&2
    exit 1
  fi
  echo "── '$BRANCH' merged via squash (PR #$PR_NUM: state=MERGED, head=$pr_head, base=$pr_base)"
fi

# Guard 9: Compute and validate archive tag
SLUG="${BRANCH//\//-}"
DATE=$(date -u +%Y-%m-%d)
TAG="archive/${SLUG}-${DATE}"

if git rev-parse --verify --quiet "refs/tags/$TAG" >/dev/null \
   || git ls-remote --exit-code --tags origin "refs/tags/$TAG" >/dev/null 2>&1; then
  echo "Error: archive tag '$TAG' already exists. Won't overwrite." >&2
  exit 1
fi

echo "── Will archive:"
echo "     branch:  $BRANCH"
echo "     tip:     $TIP"
echo "     target:  $TARGET (PR #$PR_NUM)"
echo "     tag:     $TAG"
echo ""

# Step 1: create annotated tag locally
if ! git tag -a "$TAG" "$TIP" -m "Merged to $TARGET via PR #$PR_NUM on $DATE"; then
  echo "Error: tag creation failed" >&2
  exit 2
fi
echo "✅ tag created locally"

# Step 2: push tag
if ! git push --quiet origin "$TAG"; then
  echo "Error: tag push failed; reverting local tag" >&2
  git tag -d "$TAG" >/dev/null
  exit 2
fi
echo "✅ tag pushed to origin"

# Step 3: delete remote branch — this is the high-blast step;
# tag has been verified-pushed so commits remain reachable.
if ! git push --quiet origin ":$BRANCH"; then
  echo "Error: remote branch delete failed. Tag remains; remote branch unchanged." >&2
  exit 2
fi
echo "✅ remote branch deleted (commits live on under $TAG)"

# Step 4: delete local branch if present
if git rev-parse --verify --quiet "refs/heads/$BRANCH" >/dev/null; then
  if ! git branch -D "$BRANCH" >/dev/null; then
    echo "Warning: local branch delete failed (non-fatal)" >&2
  else
    echo "✅ local branch deleted"
  fi
else
  echo "ℹ local branch already absent"
fi

echo ""
echo "─── Done. Recover commits anytime via: git show $TAG"
exit 0
