# Commit Rules

Use this file only after the user directly asks to prepare or create a commit.
That request starts preparation; it does not authorize executing `git commit`.
Execution requires the post-manifest confirmation in `.agents/rules/git.md`.

Related inputs:

- `.agents/rules/git.md`
- `docs/governance/contributing.md`
- `CLAUDE.md §4` as current branch-policy input, not the only possible source

## Message format

`<type>(<scope>): <subject>` — Conventional Commits.

- type: `feat` / `fix` / `refactor` / `chore` / `docs` / `test`
- subject states **what** changed, at the change level; the body explains **why** — short prose summary, `-` bullets for enumerable items
- **no trailers** — no `Co-Authored-By`, no `Signed-off-by` (workspace-wide rule, W-R25); tooling defaults that auto-append one are overridden — omit it explicitly. (Pre-existing history keeps its trailers; do not rewrite.)

## Rules

- Commit one logical unit at a time.
- Keep commit messages short and scoped.
- Do not commit unrelated workspace noise.
- Do not treat `continue`, `finish`, plan approval, branch-ready language, a
  tool approval prompt, or a session-end synchronization recommendation as a
  commit request or confirmation.
- Before staging, propose the exact path list. Stage only those paths after the
  user directly requests commit preparation; never use `git add .`, `git add
  -A`, or a broad directory containing unreviewed changes.
- Review the complete staged diff, not only its stat or selected excerpts.
- Confirm every staged file belongs to the same logical unit, every material
  claim is supported, links/paths resolve where applicable, and no known
  incorrect or incomplete content is being represented as finished.
- **Identity gate before committing** (W-R25): report `git config --show-origin user.name user.email` and confirm it resolves from the host's **global** gitconfig to the current operator. Unset, repo-local override, or someone else's identity → stop and resolve with the user first. Identity values live in `~/.gitconfig` only — never hardcode names/emails in this file.
- Run and report the relevant validation required by `.agents/rules/git.md`,
  `.agents/rules/testing.md`, and the touched documentation/governance surface.
  A failed or blocked required check is a commit blocker unless named in the
  manifest and explicitly accepted by the user.
- Draft the complete subject and body from the staged diff. Do not claim
  approval, completion, application, or verification that the evidence does
  not support.
- Present branch, exact staged name/status and stat, content summary,
  validation results/gaps, and the full message as the commit manifest. Stop
  and wait for a later user confirmation of that exact manifest.
- Immediately before committing, re-check that staged paths/content, message,
  and validation status are unchanged. A change invalidates the confirmation.
- After committing, inspect the result — `git log -1 --format='%an <%ae>%n%H%n%s%n%n%b'` — and confirm author, subject, body, and absence of trailers match what was drafted.
- Do not automatically amend, bypass hooks, make a corrective second commit, or
  push. Each is a new transaction with its own authorization.
