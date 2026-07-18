# Changelog

All **user-visible** changes are documented here. Versioning starts at
`0.0.1` with the migration to `saberu-ops/saberu`; pre-0.0.1 change history
is preserved in the archived upstream `ansispire` repository.

The format is loosely adapted from [Keep a Changelog](https://keepachangelog.com).

## What counts as user-visible (when to add an entry)

A change qualifies as user-visible — and therefore requires an entry in
`[Unreleased]` in the same commit (`CLAUDE.md §0 Sync Guard #4`) — when it
touches any of:

- **CLI behavior** — Make targets, scripts users invoke, output format
- **Configuration defaults** — variables in `defaults/`, `group_vars/`, role-public knobs
- **Public interface** — role contracts, EDA rule schema, controller HTTP surfaces
- **Breaking refactor** — variable renames, removed aliases, path moves users may reference
- **Security policy** — firewall, RBAC, secrets handling, hardening defaults

Changes that do NOT trigger a CHANGELOG entry:

- Pure-internal refactors with no caller-visible effect
- Test additions / changes (covered by TSVS records)
- Documentation cleanup
- AI-collaborator instruction changes (`CLAUDE.md`, `.agents/`)
- Per-round plan / changelog files under `docs/workstreams/` or legacy `docs/reviews/`

---

## [Unreleased]

(nothing yet)

---

## [0.0.1] — 2026-07-18

Initial import into `saberu-ops/saberu`.

- Content baseline: the consolidated working tree of the upstream
  `ansispire` repository (branch line `dev` → `feat/target-architecture` →
  `feat/vps-software-catalog`, plus the governance-rules refactor and the
  VPS-profile-catalog workstream migration), pruned for the new project.
- Pruned relative to upstream: archived review evidence, per-round
  changelogs under `docs/reviews/`, the stale Chinese reference snapshot,
  the retired Gemini agent guidance layer, and the orphaned legacy
  `plugins/` routing stub.
- Not renamed: internal `ansispire` naming (roles, service configs, paths)
  is deliberately unchanged in 0.0.1; the `ansispire` → `saberu` rename is
  scheduled for 0.0.2.
- Provenance and migration evidence:
  `docs/workstreams/feat-saberu-migration/`; full pre-0.0.1 commit history
  remains in the archived upstream repository
  (`github.com/taoziyoyo2566/ansispire`).
