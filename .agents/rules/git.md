# Git Rules

Use this whenever running git commands, changing branches, staging, committing, pushing, or reviewing repository state.

Authorization semantics come from `.agents/rules/authorization.md`. A command
being technically permitted by the sandbox does not authorize the Git action.

## No additional confirmation

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

Plain `git fetch origin` is the sole pre-authorized ref mutation: use it only
for a stated freshness check, without prune, force, or a custom refspec, and do
not combine it with merge, rebase, reset, checkout, pull, or push.

## Preparation request required

The current user must directly request the named operation before preparation:

- `git add` — only exact reviewed paths and only as part of an explicitly
  requested commit/checkpoint preparation;
- `git commit` — the preparation request does not authorize executing the
  commit; use the commit transaction gate below;
- `git switch` / branch creation — the user must request or approve the branch
  action when it is not already an explicit part of the requested outcome;
- `git merge`, `git rebase`, `git cherry-pick`, `git revert`, `git tag`,
  or `git pull`;
- `git push` — the preparation request does not authorize executing the push;
  use the push transaction gate below;
- `git stash` or other commands that hide or rewrite the visible working-tree
  state.

An execution-environment Yes/Allow response is only technical sandbox
permission. It cannot supply the direct user request or the post-manifest
confirmation required here.

## Commit transaction gate

Use this sequence for every commit:

1. A direct user message asks to prepare or create a commit.
2. Check `git status --short --branch`; inspect all relevant working-tree and
   index diffs; propose one logical unit and its exact path list.
3. Stage only those paths. Never use `git add .`, `git add -A`, a directory
   prefix that includes unreviewed files, or an unrelated pre-existing staged
   change.
4. Apply `.agents/rules/commits.md`: review the complete staged diff, run
   required checks, verify identity, and draft the full message.
5. Present a commit manifest containing branch, exact staged name/status and
   stat, reviewed content summary, validation results and gaps, and the full
   proposed message. Stop and wait.
6. Only a later user message approving that exact manifest authorizes one
   `git commit`. Immediately before execution, confirm the staged paths,
   content, message, and check status are unchanged; otherwise the confirmation
   expires.
7. Inspect and report the created commit. Do not amend, create a follow-up
   commit, or push without a new applicable transaction.

Do not invoke `git commit`, ask for its sandbox escalation, or treat a generic
"continue/finish" response as approval before step 6.

## Push transaction gate

Commit authorization never includes push. Use this separate sequence:

1. A direct user message asks to prepare or perform a push.
2. Run the local CI-equivalent checks for the touched surface. If the repo
   provides a CI/check target, use it.
3. Present a push manifest containing remote URL/name, local source ref,
   destination ref, exact commit range and count, upstream ahead/behind state,
   check results and gaps, and whether force or upstream configuration is
   involved. Stop and wait.
4. Only a later user message approving that exact manifest authorizes one push.
   Re-check the range and refs immediately before execution; any change expires
   the confirmation.
5. Push only the stated refspec. Do not also push tags, another branch, or set
   upstream unless the manifest included it.

If any required check cannot run, do not push until the user sees and explicitly
accepts the named gap in the manifest. If the remote rejects the push, report
the rejection; do not automatically pull, rebase, merge, force-push, or retry a
different refspec.

## Exact confirmation required

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
- `git commit --amend`
- `git commit --no-verify` or any hook bypass
- any `git reset` mode that moves `HEAD`, a branch ref, or changes the index or
  working tree

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
