# Authorization Rules

This is the repository single source of truth for deciding whether an action
may proceed. Other rules may add workflow or verification requirements, but
must not redefine authorization semantics.

## Four concepts that must stay separate

| Concept | What it answers | What it does not authorize |
|---|---|---|
| Task authorization | What outcome and repository scope did the user ask to change? | Work outside that scope |
| Plan approval | Is an approval-gated direction or implementation approach accepted? | Git publication, external writes, or live runs unless separately declared |
| Sandbox capability | Can the current tool technically perform the action here? | User intent; an allow rule is not semantic authorization |
| Action confirmation | Did the user authorize a named high-impact action or live run? | Different targets, operations, or later runs |

Passing one layer does not imply the others. In particular, a sandbox approval
or command allow rule never expands the user's task, and plan approval never
silently becomes permission to publish or mutate live infrastructure.

## Task authorization for repository files

A user request to change, build, fix, update, refactor, or apply stated
recommendations authorizes the repository-file edits reasonably required to
complete that request inside the writable workspace. This includes creating,
modifying, renaming, and removing known in-scope files, plus non-destructive
verification. Do not request permission again per file or per ordinary edit.
These are working-tree writes, not Git index/history/ref operations merely
because Git tracks the files, and they need no sandbox escalation while they
remain inside configured writable roots.

This authorization is bounded:

- state the intended files/surfaces, reason, and out-of-scope boundary before a
  non-trivial edit;
- preserve unrelated, pre-existing, and unrecognized work in a dirty tree;
- do not remove historical evidence or an unrecognized file unless the request
  explicitly includes that outcome;
- stop when a newly discovered decision would materially expand or redirect the
  requested change;
- follow any applicable plan gate before code or executable implementation.

Request wording matters:

| User request | Repository-file authority |
|---|---|
| explain, inspect, review, audit, diagnose, or report | read-only by default |
| change, fix, implement, update, refactor, or apply the recommendations | in-scope workspace edits and normal verification |
| prepare a plan or proposal | planning artifacts only; no implementation |
| approve a plan | only the plan's declared approval scope |

Documentation is classified by effect, not extension:

- typo, comment, or non-functional formatting is L0;
- documentation synchronized with an authorized implementation inherits that
  implementation's task scope;
- changing agent rules, approval semantics, operator procedures, architecture,
  or historical evidence is a behavioral/governance change, not L0 merely
  because the file is Markdown;
- bounded remediation of an authorized governance review may be edited
  directly; a new separately approvable direction still follows the applicable
  L2 plan gate.

## Actions that need no additional confirmation

Once the task is authorized, proceed without a second conversational approval
for:

- local and Git read-only inspection;
- read-only remote queries and documentation lookup;
- in-scope repository-file edits under the writable workspace;
- normal static checks, tests, and local ephemeral outputs that do not mutate
  real infrastructure or external services;
- plain `git fetch origin` used only for repository freshness, after stating
  that reason and without prune, force, or a custom refspec.

If the execution environment blocks one of these technically, request the
narrowest sandbox escalation needed. That technical prompt does not change the
task scope.

## Approval-prompt hygiene

Do not request escalation merely because an executable has some optional mode
that could mutate state. Classify the actual invocation, target, and boundary:

- ordinary reads and in-scope workspace writes should run inside the active
  sandbox;
- shells, interpreters, build tools, `rg`, `sed`, `cp`, and similar utilities
  are not high-impact merely by executable name;
- a compound command made only of authorized reads or workspace-local writes
  should not be escalated as an arbitrary shell;
- an execpolicy rule that prompts for routine sandbox-contained work is a rules
  defect to fix, not a reason to normalize repeated user confirmations.

Escalate only when the actual command needs to cross a protected boundary, such
as Git refs/history, remote services, host state, privilege, credentials, or
data outside writable roots. This hygiene rule does not weaken the explicit
action and exact-confirmation gates below.

## Actions requiring an explicit user request

The user must request or clearly approve the named operation before:

- staging or committing a checkpoint;
- creating or switching branches when the branch action was not already an
  explicit part of the requested outcome;
- stashing or otherwise hiding pre-existing working-tree changes;
- merge, rebase, cherry-pick, revert, tag, pull, push, or remote-ref changes;
- deployment, external API writes, or creation/modification of external
  resources;
- privilege elevation, host package installation, host service changes, or
  writes outside the configured writable roots.

### Commit and push use two-stage authorization

Commit and push are transaction-scoped exceptions to ordinary task autonomy.
No plan, workflow, completion instruction, or tool approval may infer them:

- `continue`, `finish`, `apply the recommendations`, `handle the next step`,
  `make it ready`, plan approval, branch-ready status, and session-end sync
  language do not authorize staging, commit, or push;
- a sandbox/escalation approval only permits the displayed command to cross a
  technical boundary. It is never the missing task authorization, and Codex
  must not request that technical approval before the semantic gate below;
- an allow rule, hook, automation, or project workflow cannot replace the
  current user's transaction confirmation.

Use two separate stages:

1. **Preparation request.** A direct user request to prepare or create a commit
   authorizes read-only inspection and exact-path staging for that proposed
   commit only. A direct request to push authorizes preparation of a push
   manifest only.
2. **Execution confirmation.** After preparation, present the complete commit
   or push manifest required by `.agents/rules/git.md` and stop. Execute only
   after a later user message approves that exact manifest.

The confirmation is single-use and expires if paths, staged content, commit
message, validation status, source ref, destination ref, remote, commit range,
or force mode changes. A commit confirmation does not authorize amend, another
commit, or push. A push confirmation does not authorize commit, amend, tag, a
different ref, or a later push. Even an initial request saying "commit and
push" must pass the commit and push manifests separately because the exact push
range does not exist until the commit is created.

If a required check fails or cannot run, do not commit or push unless the user
first sees the named failure/gap in the manifest and explicitly accepts it.

## Actions requiring exact confirmation

Require the exact action, target, and reason for:

- destructive Git or history/ref rewriting operations;
- commit amend, bypassing hooks, force-push, or deletion of a remote ref;
- deletion or overwrite of unrelated, unrecognized, historical, or
  user-owned data;
- credential rotation, revocation, or secret destruction;
- managed-fleet mutation;
- any live operation whose target set or blast radius is not already bounded.

Use `.agents/rules/git.md` for the destructive Git list and recovery gate.

## Live infrastructure authorization

Direction or implementation approval alone does not authorize a live mutation.
Live work uses one of these two models:

1. **Per-run confirmation** — required for managed fleet and whenever standing
   authorization is absent or incomplete.
2. **Standing test-host authorization** — an approved execution plan or
   addendum may cover repeated runs only when it explicitly records:
   - exact disposable/test hosts or inventory and expected count;
   - allowed playbooks, templates, APIs, or operation classes;
   - allowed phases, time window or round, and attempt limit;
   - expected impact and excluded operations;
   - fallback/recovery owner and evidence to capture;
   - a statement that this block grants standing live authorization.

At execution time, revalidate the recorded target, operation, impact, and
recovery facts. Any mismatch, scope expansion, attempt-limit exhaustion, or
move to managed fleet invalidates the standing authorization and requires
per-run confirmation.

## When uncertain

Do not ask merely because an action writes a project file. Ask only when the
missing answer could materially change scope, destroy or expose user work,
mutate a protected external target, or cross one of the explicit gates above.
