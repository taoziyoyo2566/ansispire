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
- `.agents/rules/codex-capabilities.md`

If the current branch name maps to a topic directory, read the latest relevant files under `docs/reviews/<topic>/`:

- `plan-*.md` for active intent and scope
- latest `round*.changelog.md` for what landed, what is blocked, and next steps

## Report shape

Summarize:

- current branch
- clean or dirty working tree
- active topic and owner branch, if identifiable
- prerequisite branches that still need to merge into `dev`
- immediate next steps
- blocked items
- deferrable items

Do not edit files, stage changes, commit, switch branches, fetch, pull, or push during bootstrap unless the user explicitly asks.

## Capability refresh

During bootstrap for substantial ongoing work, do a lightweight check for useful Codex capabilities:

- inspect already available tools
- use `tool_search` when a hidden/deferred tool may fit the task
- do not run a broad search without a task-shaped reason

If a capability could materially reduce token cost, elapsed time, or error risk, mention it in the status summary and route future work through `.agents/rules/codex-capabilities.md`.
