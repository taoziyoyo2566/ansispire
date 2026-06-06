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
- `git reset`
- `git tag`
- `git fetch`
- `git pull`
- `git push`

Before mutating git state, check the working tree with `git status --short --branch`.

## Destructive operations

Never run destructive git operations unless the user explicitly requested that exact class of action and the expected target is clear:

- `git reset --hard`
- `git reset --merge`
- `git reset --keep`
- `git checkout -- <path>`
- `git restore <path>`
- `git clean`
- `git branch -D`
- force-push or remote ref deletion

For destructive ref operations, follow `CLAUDE.md §4` / archive script rules and prefer repository scripts over hand-written ref mutation.

## Reset and history rewrite protocol

Do not use `git reset` as a shortcut to make a branch look clean.

Before any `git reset` that moves `HEAD` or a branch ref:

1. Confirm the exact current branch and cleanliness with `git status --short --branch`.
2. Record the current commit with `git rev-parse HEAD`.
3. Explain why merge, revert, cherry-pick, or a new branch is not the better option.
4. Create or identify a recovery ref before moving the branch.
5. Get explicit user approval for the reset target and reset mode.
6. After the reset, verify with `git log`, `git reflog`, and a diff against the recovery ref.

Prefer non-rewriting operations for normal branch cleanup:

- Use `git revert` to undo public or shared commits.
- Use a new dev-based branch plus cherry-pick when extracting a clean topic.
- Use backup refs only as recovery evidence, never as proof that the task is complete.

Never delete the recovery ref until the user confirms the rewritten branch is merged or no longer needed.
