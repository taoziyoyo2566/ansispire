# VPS Profile Catalog workstream

This bundle owns the direction, approval artifacts, investigations, decisions,
reviews, and round evidence for composable VPS configuration profiles.

## Ownership and current state

| Field | Current value |
|---|---|
| Function | Give each VPS one discoverable non-secret configuration path: one `BaselineProfile` plus zero or more `ServiceProfile` assignments |
| Owner branch | `feat/vps-profile-catalog` |
| Branch state | The current checkout remains `feat/vps-software-catalog`; no owner-branch creation or transition was performed during this documentation round |
| Direction | `APPROVED` on 2026-07-17 |
| Implementation | Blocked until the applicable child execution plan is approved |
| Live operations | Not authorized by direction approval; every live run still needs the execution-time go/no-go gate |

The approved hierarchy keeps identity, host-policy, and baseline-software
components inside a `BaselineProfile`. A Node selects the complete
`BaselineProfile`; routine Node configuration does not compose those internal
components directly.

## Current action

1. Preserve and separate unrelated working-tree changes before any branch
   transition.
2. Create or move to the owner branch only through the repository's branch
   authorization workflow.
3. Execute WU-0 as a non-managed-host carrier probe and record it in
   `investigation-profile-carrier.md`.
4. Replace the carrier-dependent placeholders in
   `execution-identity-migration-2026-07-18.md`, move it from `DRAFT` to
   `PENDING_APPROVAL`, and present it for separate approval.

No profile/catalog implementation or live VPS mutation should start from the
approved direction plan alone.

## Execution and approval status

| Layer | Artifact | State | Execution meaning |
|---|---|---|---|
| Direction | [`plan-composable-vps-profiles-2026-07-17.md`](plan-composable-vps-profiles-2026-07-17.md) | `APPROVED` | Confirms architecture and WU-0–WU-5 roadmap; does not authorize behavioral implementation |
| WU-0 carrier | `investigation-profile-carrier.md` | Not started | Current prerequisite; empirical investigation, not another plan |
| WU-1 catalog + identity | [`execution-identity-migration-2026-07-18.md`](execution-identity-migration-2026-07-18.md) | `DRAFT` | Detailed implementation approach; cannot be presented for approval until WU-0 closes |
| WU-2 fail2ban | [`plan-software-profile-pilot-2026-07-17.md`](plan-software-profile-pilot-2026-07-17.md) | `DRAFT` | Blocked by the final WU-1 resolver/provider contract |
| WU-3–WU-5 | Parent direction roadmap | Not separately planned | Require later scoped execution plans when their approval boundary is reached |
| Predecessor | [`plan-decouple-software-units-2026-07-12.md`](../../reviews/feat-vps-software-catalog/plan-decouple-software-units-2026-07-12.md) | `SUPERSEDED` | Separate legacy topic retained as historical input; not executable |

## Artifact map

| Artifact | Type | State | Purpose |
|---|---|---|---|
| [`plan-composable-vps-profiles-2026-07-17.md`](plan-composable-vps-profiles-2026-07-17.md) | Historical-filename direction plan | `APPROVED` | Defines the profile hierarchy, ownership boundaries, work units, and gates |
| [`execution-identity-migration-2026-07-18.md`](execution-identity-migration-2026-07-18.md) | Execution plan | `DRAFT` | Defines WU-1 catalog foundation, identity migration, compatibility, verification, and live gates |
| [`plan-software-profile-pilot-2026-07-17.md`](plan-software-profile-pilot-2026-07-17.md) | Historical-filename execution plan | `DRAFT` | Defines the fail2ban pilot; remains blocked on the WU-0/WU-1 resolver contract |
| `investigation-profile-carrier.md` | Topic-owned investigation | Not started | Will probe the pinned Ansible/Semaphore carrier and close WU-0 unknowns |

New topic-owned plans, investigations, decisions, reviews, and round evidence
stay in this bundle. Shared stable documents remain at their canonical
locations and are linked below.

## Stable dependencies

- [Project task ledger](../../../TODO.md)
- [Parent takeover execution plan](../../reviews/feat-target-architecture/plan-saberu-vps-takeover-execution-2026-06-24.md)
- [Target-architecture design](../../reviews/feat-target-architecture/design-2026-05-26.md)
- [Product domain model](../../reviews/feat-product-redesign/domain-model-2026-06-23.md)
- [VPS lifecycle feature map](../../reference/feature-map/vps-lifecycle.md)

## Bundle history

- 2026-07-17: the profile direction and fail2ban child plan moved as one topic
  from the legacy `docs/reviews/` root to `docs/workstreams/`, retaining their
  historical filenames.
- 2026-07-18: WU-1 gained a scoped draft execution plan. The superseded
  `feat-vps-software-catalog` plan remains a separate legacy topic because
  supersession alone does not establish whole-topic absorption.
