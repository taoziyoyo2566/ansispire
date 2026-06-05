#!/usr/bin/env bash
# scripts/check_claude_md_links.sh — lint repo-tracked CLAUDE.md files for
# wikilink-style references (`[[name]]`) that escaped from personal-memory
# namespace into governance.
#
# Why this exists:
#   CLAUDE.md is loaded as resident context for every Claude session and is the
#   shared workflow baseline for Claude sessions (see project ./CLAUDE.md). Wikilinks
#   like `[[feedback-foo]]` resolve only inside an agent's private
#   `~/.claude/projects/*/memory/` namespace — they are dead references
#   from the repo's point of view. A future agent that inherits only the
#   tracked repo cannot follow them.
#
# Behavior:
#   - Finds every `CLAUDE.md` tracked in git (project root + nested).
#   - Greps for `[[...]]` patterns.
#   - Exits 1 with file:line context on any hit.
#   - Exits 0 silently when clean (suitable for `make verify` chaining).
#
# Usage:
#   ./scripts/check_claude_md_links.sh
#
# Exit codes:
#   0 — clean (no wikilinks in any tracked CLAUDE.md).
#   1 — at least one CLAUDE.md contains a wikilink.
#   2 — not run from a git working tree.

set -u

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Error: must be run inside a git working tree" >&2
  exit 2
fi

cd "$(git rev-parse --show-toplevel)"

# All tracked CLAUDE.md files. -z + read -d '' handles paths with spaces.
mapfile -d '' -t files < <(git ls-files -z 'CLAUDE.md' '*/CLAUDE.md')

if [[ ${#files[@]} -eq 0 ]]; then
  # Nothing to lint — non-error. Repos without a CLAUDE.md are valid.
  exit 0
fi

found=0
for f in "${files[@]}"; do
  # grep -nE: line-numbered ERE. `-H` forces filename even with single file.
  if matches=$(grep -nHE '\[\[[^]]+\]\]' "$f"); then
    if [[ $found -eq 0 ]]; then
      echo "Wikilink found in tracked CLAUDE.md (these belong to personal-memory namespace, not repo governance):" >&2
      echo "" >&2
    fi
    echo "$matches" >&2
    echo "" >&2
    found=1
  fi
done

if [[ $found -eq 1 ]]; then
  echo "Remove the wikilink(s) above. Inline the rule, or link to a real repo path." >&2
  exit 1
fi

exit 0
