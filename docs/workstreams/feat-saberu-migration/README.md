# Saberu Repo Migration workstream

This bundle owns the one-time migration of the ansispire working tree into a
fresh `saberu-ops/saberu` repository as version 0.0.1, with history dropped and
content pruned.

## Ownership and current state

| Field | Current value |
|---|---|
| Function | Export the consolidated ansispire working tree (pruned) as the initial commit of `saberu-ops/saberu`, tagged `v0.0.1` |
| Owner branch | `feat/saberu-migration` (created from `feat/vps-software-catalog`, carrying the consolidated working tree) |
| Branch state | Migration executed on this branch; pushed to the old origin as archived evidence |
| Direction | Approved by user in-session on 2026-07-18 (baseline = working tree; repo name = `saberu-ops/saberu`; prune list C1 conservative / C2 drop Gemini / C3 trim TODO / C4 reset CHANGELOG; internal `ansispire` naming untouched until 0.0.2) |
| Implementation | **COMPLETED 2026-07-18** — `saberu-ops/saberu` live (private); `v0.0.1` tagged on `feat/saberu-0.0.1-import` (unmerged by user decision); evidence in `round1-2026-07-18.changelog.md` |
| Live operations | None (no managed VPS touched); external actions were GitHub repo creation and pushes under the Phase-4 user go |

## Artifact map

| Artifact | Purpose |
|---|---|
| `execution-saberu-0.0.1-repo-migration-2026-07-18.md` | Approval-gated implementation approach for the migration |
| `round<N>-*.changelog.md` | Round evidence (created at execution time) |

## Stable external links

- Old repository (becomes archive): <https://github.com/taoziyoyo2566/ansispire>
- New repository (created in Phase 4): <https://github.com/saberu-ops/saberu>
- Naming decision: `docs/reviews/feat-product-redesign/name-decision-saberu-2026-06-23.md`
- Superseded-in-part blueprint: `docs/reviews/feat-product-redesign/plan-saberu-new-project-2026-06-23.md`
