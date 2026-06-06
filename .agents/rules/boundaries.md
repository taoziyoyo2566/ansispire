# Boundaries

Before editing, answer:

1. What files are in scope?
2. Why is this change needed?
3. What is explicitly out of scope?

- Do not mix control-plane changes and role/data-plane changes casually.
- Do not change inventory model, deployment flow, or plugin ownership without checking:
  - `ARCHITECTURE.md`
  - `TODO.md`
  - relevant plan docs in `docs/reviews/`
- Do not silently change operator workflows documented in `docs/operations/` or `docs/user-guide/` without syncing those docs.
- Do not treat an investigation document as an implementation mandate unless current plans or TODO entries still point to it.
- Preserve historical records in `docs/reviews/_archive/` and investigation files.
