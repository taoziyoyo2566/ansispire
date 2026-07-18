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

If the current branch name maps to a topic directory, look under
`docs/workstreams/<topic>/` first. Fall back to the legacy
`docs/reviews/<topic>/` only when the topic has not been migrated. Both roots
must not contain the same topic.

- `README.md` first, when present, for the functional overview, owner branch,
  artifact map, current action, and stable external links
- `direction-*.md`, `execution-*.md`, and `addendum-*.md` for new approval
  artifacts
- relevant `investigation-*.md` for open unknowns and probe evidence owned by
  the topic
- historical `plan-*.md` files still referenced by `TODO.md` for active intent
  and scope
- latest relevant `review-*.md`, especially any report referenced by TODO,
  plans, or round evidence with unresolved `P0`/`P1` findings
- relevant `decision-*.md` when an active plan or TODO entry depends on the
  decision
- latest `round*.changelog.md` for what landed, what is blocked, and next steps

If an existing topic lacks `README.md`, continue from its current artifacts and
report the missing hub as migration debt. Do not create it during the read-only
bootstrap.

## Freshness check (multi-machine)

When resuming substantial work (not a quick question), also verify this clone is
current before basing anything on it:

- `git fetch origin` — allowed here despite the general no-mutation rule below;
  state "bootstrap freshness check" as the reason (the freshness exception in
  `.agents/rules/git.md` and `.agents/rules/authorization.md`).
- `git log --oneline HEAD..origin/<branch>` — non-empty means this clone is
  behind; surface it in the status report **before** proposing new work.
  See `.agents/rules/branching.md` §Multi-machine sync.

## Environment probe

If the upcoming work depends on environment capabilities (Docker, ansible
toolchain, credentials), check the per-host capability registry instead of
trusting memory or prior session notes — capability claims are dated snapshots
(`~/workspace/.agents/rules/environment-truth.md`; the registry is shared at the
workspace layer):

- `make env-probe-check` (or `make -C ~/workspace env-probe-check`) — passes if
  `~/workspace/.agents/env/<host>.yml` exists and is fresh
- on failure (new machine / stale): `make env-probe` regenerates it
- then read the registry for what is runnable here and which host overrides apply;
  for ansispire venv tools (ansible/lint) see `.agents/env/README.md`

Report capability flips (available ↔ absent vs the previous registry state) in
the status summary — stale plans or memories may depend on the old state.

## Report shape

Summarize:

- current branch
- clean or dirty working tree
- behind/ahead of `origin/<branch>` (from the freshness check, if run)
- active topic and owner branch, if identifiable
- prerequisite branches that still need to merge into `dev`
- immediate next steps
- blocked items
- deferrable items

Do not edit files, stage changes, commit, switch branches, pull, or push during
bootstrap unless the user explicitly asks. `git fetch` is permitted only as the
freshness check above.

## Capability refresh

During bootstrap for substantial ongoing work, do a lightweight check for useful Codex capabilities:

- inspect already available tools
- use `tool_search` when a hidden/deferred tool may fit the task
- do not run a broad search without a task-shaped reason

If a capability could materially reduce token cost, elapsed time, or error risk, mention it in the status summary and route future work through `.agents/rules/codex-capabilities.md`.
