# TODO — Target Architecture Branch Management

> Date: 2026-06-03
> Scope: solve the current branch-ownership problem around the "return to Ansible + Semaphore" architecture direction
> Related docs:
> - `docs/reviews/feat-target-architecture/plan-2026-05-25.md`
> - `docs/reviews/feat-target-architecture/design-2026-05-26.md`
> - `docs/reference/investigations/IVG-MULTI-SERVER-ANSIBLE-PRACTICE.md`

---

## 1. Problem Statement

Current state is split across the wrong places:

- bootstrap时的 mainline truth still contained the local `vps_manager` runtime and its docs; owner branch cleanup has now removed that control surface here.
- `feat/vps-manager-v2` contains a historical transition attempt (`vps_manager` -> `vps_runner`) but is not the accepted owner for the final architecture.
- The newer "return to Semaphore Inventory + Key Store + Task API" target architecture is documented under `docs/reviews/feat-target-architecture/`, and now has a dedicated owner branch.
- Without a dedicated owner branch, future cleanup of `vps_manager` code and unrelated docs will drift across the wrong branches.

Target state:

- `feat/vps-manager-v2` stays as the **transition branch / historical reference**.
- `feat/target-architecture` becomes the **single planning branch** for the architecture return-to-Semaphore direction.
- Future implementation branches derive from `feat/target-architecture`, not from `feat/vps-manager-v2`.

---

## 2. Ownership Rules

- `feat/vps-manager-v2`
  - Owns: `vps_manager` -> `vps_runner` rewrite history, cutover evidence, transitional docs.
  - Does not own: final Semaphore-centric architecture decisions.

- `feat/target-architecture`
  - Owns: target architecture plan, design, branch split decisions, and all follow-up planning for Semaphore Inventory / Key Store / Task API / CF Worker wizard.
  - Becomes the parent branch for any work that removes or supersedes the current `vps_manager` control surface.

---

## 3. Immediate TODO

### A. Branch bootstrap

- [x] Create branch `feat/target-architecture`.
- [x] Add `docs/reviews/feat-target-architecture/plan-2026-05-25.md`.
- [x] Add `docs/reviews/feat-target-architecture/design-2026-05-26.md`.
- [x] Add this TODO file to the same branch.
- [x] Add agent guidance for this topic directory.
- [x] Add a branch-bootstrap changelog.
- [x] Commit the initial branch-management snapshot with a docs-only commit. *(landed as `3cf02fe` bootstrap commit, 2026-06-03)*

### B. Branch boundary cleanup

- [x] Record explicitly that `IVG-MULTI-SERVER-ANSIBLE-PRACTICE.md` remains historical context under `feat/vps-manager-v2`, while `feat-target-architecture` references it instead of moving it.
- [x] Stop adding new "return to Semaphore" planning content to `feat/vps-manager-v2`.
- [ ] Keep `feat/vps-manager-v2` available as a reference branch only until the new architecture branch is accepted.
- [x] Execute the actual `vps_manager` code and doc removal only under this branch or its child implementation branches.

### C. Plan normalization

- [x] Update `plan-2026-05-25.md` header from "cross-branch global plan" to the actual owner branch once `feat/target-architecture` exists.
- [x] Add one short note in the plan or a future changelog explaining why this topic was split out of `feat/vps-manager-v2`.
- [x] Add a changelog entry when the branch split is finalized.
- [x] Normalize the plan/design docs so they matched the Round 1 repo truth (`vps_manager` still present) instead of the old `vps_runner` draft context.

---

## 4. Follow-up Branches To Create Later

These should **not** be created before the parent planning branch exists.

- [ ] `feat/semaphore-inventory-api`
  - Purpose: Phase 1 API investigation and CRUD contract validation.

- [ ] `feat/cf-worker-wizard`
  - Purpose: Phase 2 Worker + wizard implementation.

- [ ] `refactor/semaphore-vps-cutover`
  - Purpose: Phase 3 inventory source switch + retained `playbooks/vps/` Semaphore wiring.

- [ ] `feat/semaphore-prod-hardening`
  - Purpose: Phase 4 backup / TLS / target_group hardening.

---

## 5. Done Criteria

This branch-management issue is considered solved only when all of the following are true:

- [x] `feat/target-architecture` exists.
- [x] The target-architecture docs are committed on that branch. *(bootstrap `3cf02fe`)*
- [x] New architecture work no longer lands on `feat/vps-manager-v2`.
- [x] There is a written rule for which future work belongs to which branch.
- [ ] The next implementation topic is opened from the correct parent branch. *(still pending — blocked on Phase 1 runtime probe; see TODO.md Open Decisions ENV)*

---

## 6. Recommended Execution Order

1. Create `feat/target-architecture`.
2. Commit the three docs in this directory first.
3. Treat `feat/vps-manager-v2` as frozen reference for this topic.
4. Open the next concrete workstream from `feat/target-architecture`.
