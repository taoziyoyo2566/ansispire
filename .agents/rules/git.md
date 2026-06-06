# Git Rules

Use this whenever running git commands, changing branches, staging, committing, or reviewing repository state.

## Read-only inspection

Read-only git inspection is pre-authorized. Do not ask for permission or escalation before running git commands that do not modify:

- working tree
- index
- refs
- remotes
- git config
- credentials
- external service state

Examples:

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

Judge by effect, not subcommand name.

## Mutating operations

These modify state and require normal care:

- `git add`
- `git commit`
- `git switch` / `git checkout`
- `git merge`
- `git cherry-pick`
- `git revert`
- `git tag`
- `git fetch`
- `git pull`
- `git push`

Before mutating git state, check the working tree with `git status --short --branch`.

## Destructive operations

Never run destructive git operations unless the user explicitly requested that exact class of action and the expected target is clear:

- `git reset --hard`
- `git checkout -- <path>`
- `git restore <path>`
- `git clean`
- `git branch -D`
- force-push or remote ref deletion

For destructive ref operations, follow `CLAUDE.md §4` / archive script rules and prefer repository scripts over hand-written ref mutation.
