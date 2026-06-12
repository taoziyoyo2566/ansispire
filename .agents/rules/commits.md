# Commit Rules

Use this file only when the user explicitly asks for a commit or branch-ready checkpoint.

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
- **Identity gate before committing** (W-R25): report `git config --show-origin user.name user.email` and confirm it resolves from the host's **global** gitconfig to the current operator. Unset, repo-local override, or someone else's identity → stop and resolve with the user first. Identity values live in `~/.gitconfig` only — never hardcode names/emails in this file.
- Before committing code or executable configuration, run and report the smallest relevant validation required by `.agents/rules/git.md` and `.agents/rules/testing.md`.
- After committing, inspect the result — `git log -1 --format='%an <%ae>%n%H%n%s%n%n%b'` — and confirm author, subject, body, and absence of trailers match what was drafted.
