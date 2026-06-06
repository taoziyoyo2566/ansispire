# Commit Rules

Use this file only when the user explicitly asks for a commit or branch-ready checkpoint.

- `.agents/rules/git.md`
- `docs/governance/contributing.md`
- `CLAUDE.md §4` as current branch-policy input, not the only possible source

- Commit one logical unit at a time.
- Keep commit messages short and scoped.
- Prefer `docs(...)`, `fix(...)`, `feat(...)`, `refactor(...)`, or `chore(...)` according to the actual change.
- Do not commit unrelated workspace noise.
- Before committing code or executable configuration, run and report the smallest relevant validation required by `.agents/rules/git.md` and `.agents/rules/testing.md`.
