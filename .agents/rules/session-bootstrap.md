# Session Bootstrap

Use this when starting a Codex session in this repo, after context reset, or when the user asks for current task status.

## Read-only scan

Run these first:

- `git status --short --branch`
- `git log --oneline --decorate --max-count=5`

Then read:

- `TODO.md`
- `.agents/project/overview.md`
- `.agents/project/agent-strategy.md`

If the current branch name maps to a topic directory, read the latest relevant files under `docs/reviews/<topic>/`:

- `plan-*.md` for active intent and scope
- latest `round*.changelog.md` for what landed, what is blocked, and next steps

## Report shape

Summarize:

- current branch
- clean or dirty working tree
- active topic and owner branch, if identifiable
- immediate next steps
- blocked items
- deferrable items

Do not edit files, stage changes, commit, switch branches, fetch, pull, or push during bootstrap unless the user explicitly asks.
