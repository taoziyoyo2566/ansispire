# Git Rules

Use this whenever running git commands, changing branches, staging, committing, pushing, or reviewing repository state.

## Allowed without review

Run read-only git inspection without asking for permission or escalation.

Allowed examples:

- `git status`
- `git log`
- `git show`
- `git diff`
- `git diff --check`
- `git grep`
- `git branch --list`
- `git merge-base`
- `git merge-tree`
- `git ls-files`

Rule: if the command does not modify the working tree, index, refs, remotes, git config, credentials, or external service state, it is read-only.

## Review required

These are allowed only after checking `git status --short --branch` and stating the reason:

- `git add`
- `git commit`
- `git switch` / `git checkout`
- `git merge`
- `git cherry-pick`
- `git revert`
- `git reset`
- `git tag`
- `git fetch`
- `git pull`
- `git push`

Before committing code or executable configuration, run the smallest relevant validation from `.agents/rules/testing.md` and `docs/governance/testing-governance.md`.

Before pushing, run the local CI-equivalent checks for the touched surface. If the repo provides a CI/check target, use it. If any required check cannot run, do not push until the user accepts the gap.

## Prohibited unless explicitly approved

Do not run these unless the user explicitly requested the exact action, target, and reason:

- `git reset --hard`
- `git reset --merge`
- `git reset --keep`
- `git checkout -- <path>`
- `git restore <path>`
- `git clean`
- `git branch -D`
- force-push
- remote ref deletion

For destructive ref operations, prefer repository scripts such as `scripts/archive_branch.sh` when available.

## Reset / rewrite gate

Do not use reset or history rewrite just to make a branch look clean.

Any reset that moves `HEAD` or a branch ref requires:

- current branch and clean/dirty state
- current commit recorded with `git rev-parse HEAD`
- reason why merge, revert, cherry-pick, or a new branch is worse
- recovery ref created or identified first
- explicit user approval for target and mode
- post-check with `git log`, `git reflog`, and diff against the recovery ref

Never delete the recovery ref until the user confirms the rewritten branch is merged or no longer needed.
