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
#      (b) PR cross-check — `gh pr view PR_NUMBER` confirms ALL FIVE:
#          state=MERGED, headRefName=BRANCH, baseRefName=MERGE_TARGET,
#          headRefOid=origin/BRANCH (no post-merge re-push), and
#          isCrossRepository=false (no fork PRs). Each check is independent
#          and surfaces a distinct error.
#   7. Compute archive tag: archive/<branch-slash-to-dash>-<YYYY-MM-DD>.
#   8. Refuse to overwrite an existing archive tag (no-clobber).
#   9. Create annotated tag at origin/BRANCH's tip (local only).
#  10. Atomic remote push: create tag + delete :BRANCH on origin in one
#      server-side transaction (`git push --atomic ...`), with lease
#      `refs/heads/BRANCH:TIP` on the delete refspec. Both refs update
#      or neither (no stuck "tag pushed, branch not deleted" state).
#  11. Delete local BRANCH if local tip matches TIP (keeps unpushed work).
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
#   (b) GitHub PR check via `gh pr view PR_NUM` — squash-merge path. The PR
#       must satisfy ALL FIVE conditions:
#         state            == MERGED
#         headRefName      == BRANCH    (PR is for THIS branch by name)
#         baseRefName      == TARGET    (PR landed on the right target)
#         headRefOid       == TIP       (current ref points to the exact commit
#                                        that was merged — protects against
#                                        post-merge re-push / branch reuse)
#         isCrossRepository == false    (fork PRs: source branch lives in
#                                        another repo; archive does not apply)
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
              --json state,headRefName,baseRefName,headRefOid,isCrossRepository \
              -q '[.state, .headRefName, .baseRefName, .headRefOid, (.isCrossRepository|tostring)] | @tsv' \
              2>/dev/null || true)
  if [[ -z "$pr_info" ]]; then
    echo "Error: 'gh pr view $PR_NUM' returned no data" >&2
    echo "       PR may not exist, gh may be unauthed, or network failed" >&2
    exit 1
  fi
  IFS=$'\t' read -r pr_state pr_head pr_base pr_head_oid pr_cross_repo <<<"$pr_info"
  if [[ "$pr_state" != "MERGED" ]]; then
    echo "Error: PR #$PR_NUM state is '${pr_state:-unknown}' (expected MERGED)" >&2
    echo "       ancestor check also failed: tip is not an ancestor of origin/$TARGET" >&2
    exit 1
  fi
  if [[ "$pr_cross_repo" == "true" ]]; then
    echo "Error: PR #$PR_NUM is from a fork (isCrossRepository=true)" >&2
    echo "       source branch lives in another repo; archive does not apply" >&2
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
  if [[ "$pr_head_oid" != "$TIP" ]]; then
    echo "Error: origin/$BRANCH tip ($TIP)" >&2
    echo "       does not match PR #$PR_NUM merged head ($pr_head_oid)" >&2
    echo "       branch has commits added after merge — refusing to archive" >&2
    echo "       unmerged work as if it were part of the merged history" >&2
    exit 1
  fi
  echo "── '$BRANCH' merged via squash (PR #$PR_NUM: state=MERGED, head=$pr_head, base=$pr_base, tip matches merged head)"
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

# Steps 2+3: atomic remote push — create tag AND delete branch as one
# server-side transaction. --atomic guarantees both refs update or neither.
# This eliminates the stuck state where tag-push succeeded but
# branch-delete failed, which would block re-runs at guard 9 (tag exists).
# Per W-R19: lease keyed to refs/heads/$BRANCH:$TIP — if someone pushed
# to origin/$BRANCH between guard 8's gh check and now, the lease fails
# and the WHOLE atomic push rolls back (no orphan tag).
if ! git push --quiet --atomic \
       --force-with-lease="refs/heads/$BRANCH:$TIP" \
       origin \
       "refs/tags/$TAG" \
       ":refs/heads/$BRANCH"; then
  echo "Error: atomic archive push failed (both refs rolled back on remote)." >&2
  echo "       Possible causes:" >&2
  echo "         (a) origin/$BRANCH was updated since verification — lease" >&2
  echo "             refused; re-run after re-checking new commits" >&2
  echo "         (b) remote tag '$TAG' was created by another process in the" >&2
  echo "             race window between guard 9 and now" >&2
  echo "         (c) network / auth / other git error" >&2
  echo "       Reverting local tag '$TAG'..." >&2
  git tag -d "$TAG" >/dev/null
  exit 2
fi
echo "✅ remote archived atomically: tag '$TAG' created + branch '$BRANCH' deleted"

# Step 4: delete local branch if present AND local tip matches the merged TIP
# (per W-R19: no unguarded `-D`. Refuse if local has commits beyond TIP — those
# would be unpushed work that the archive tag does NOT cover.)
if git rev-parse --verify --quiet "refs/heads/$BRANCH" >/dev/null; then
  local_tip=$(git rev-parse "refs/heads/$BRANCH")
  if [[ "$local_tip" != "$TIP" ]]; then
    echo "ℹ local '$BRANCH' kept: local tip ($local_tip)" >&2
    echo "  differs from merged TIP ($TIP) — may contain unpushed commits" >&2
    echo "  review with: git log $TIP..$local_tip   then delete manually if safe" >&2
  elif ! git branch -D "$BRANCH" >/dev/null; then
    echo "Warning: local branch delete failed (non-fatal)" >&2
  else
    echo "✅ local branch deleted (tip == merged TIP)"
  fi
else
  echo "ℹ local branch already absent"
fi

echo ""
echo "─── Done. Recover commits anytime via: git show $TAG"
exit 0
