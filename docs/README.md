# Documentation Map

The `docs/` tree is organized by **audience**, not by artefact type. Pick the subdir for who you are right now.

```
docs/
├── user-guide/        # End-users / operators — long-form, with rationale
├── operations/        # Maintainers — terse command reference
├── reference/         # Machine-readable / feature maps / specs / investigations
├── governance/        # Project rules — how to contribute, how to test, AI workflow
├── reviews/           # Project process — plan docs and per-round changelogs
└── reference-cn/      # 中文翻译镜像
```

Top-of-repo documents that are NOT under `docs/`:

- [`README.md`](../README.md) — product entry, capabilities, quickstart, document map
- [`ARCHITECTURE.md`](../ARCHITECTURE.md) — global architecture truth
- [`TODO.md`](../TODO.md) — current task list and branch readiness
- [`CLAUDE.md`](../CLAUDE.md) / [`GEMINI.md`](../GEMINI.md) — AI collaborator mandates

(`CHANGELOG.md` and `SECURITY.md` are added in the P6 step of the in-progress docs refactor; see [`reviews/refactor-docs-enterprise/plan-2026-05-10.md`](reviews/refactor-docs-enterprise/plan-2026-05-10.md).)

---

## user-guide/ — start here if you are setting Ansispire up

Long-form, with the rationale baked in. Safe to read sequentially. No assumed prior knowledge of the codebase.

- [01-installation.md](user-guide/01-installation.md) — clean machine to working hub (Path B + Path A)
- [02-quickstart-eda.md](user-guide/02-quickstart-eda.md) — EDA self-healing end-to-end (the long form, includes architecture, troubleshooting, glossary)

## operations/ — when you already know the project

Terse command-first references. Optimized for "I need to do X right now, what's the line?".

- [eda-core.md](operations/eda-core.md) — reactor / audit-stack day-2 commands
- [hub-deployment.md](operations/hub-deployment.md) — Path A (Ansible role-based) hub deploy reference
- [environments.md](operations/environments.md) — dev / stag / prod inventory and Make-target map

## reference/ — feature maps, test specs, investigations

Lazy-loadable detail. Don't read top-to-bottom; cross-referenced from elsewhere.

- [feature-map/](reference/feature-map/) — one-page summary per feature (audit-plane, eda-core, eda-remediation, test-infra)
- [investigations/INDEX.md](reference/investigations/INDEX.md) — RCA / spike history; rows with `Applied` status route to the active rule location
- [test-specs/](reference/test-specs/) — TSVS verification records per test layer

## governance/ — project rules

How to contribute, how to test, how to operate as an AI in this repo, and the cross-cutting truths the project has converged on.

- [contributing.md](governance/contributing.md) — diff self-check, commit conventions, review-round flow
- [testing-governance.md](governance/testing-governance.md) — verification protocol; what counts as "Done"
- [ai-workflow.md](governance/ai-workflow.md) — L0 → L2 task classification for AI collaborators
- [operational-truths.md](governance/operational-truths.md) — settled engineering invariants (Python baseline, env sensing, etc.)
- [vendor-patches.md](governance/vendor-patches.md) — external roles patched locally; re-apply protocol

## reviews/ — project process

Per-task plan docs and per-round changelogs. Inside each `<kind>-<topic>/` directory you will find both the plan and the round changelogs that lived against it.

- Recent topics: `feat-eda-advanced-healing/`, `refactor-docs-enterprise/`, `feat-test-infra/`, `feat-governance-integration/`
- Older retired-format files live under `_archive/` after the 2026-05-10 docs refactor.

## reference-cn/ — 中文镜像

中文翻译版本。最近一次 snapshot：2026-04-14。
