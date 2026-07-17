> **Status**: DRAFT
> **Created**: 2026-07-17
> **Branch**: feat/vps-profile-catalog
> **Classification**: [L2] Architecture / Execution
> **Plan type**: Execution plan
> **Approval scope**: implementation approach
> **Parent plan**:
> [`plan-composable-vps-profiles-2026-07-17.md`](plan-composable-vps-profiles-2026-07-17.md)
> **Blocks implementation**: only the fail2ban software-profile pilot
> **Supersedes**:
> [`../feat-vps-software-catalog/plan-decouple-software-units-2026-07-12.md`](../feat-vps-software-catalog/plan-decouple-software-units-2026-07-12.md)
> **Does not supersede**: the parent profile direction or the approved takeover
> skeleton

# Plan — Fail2ban software-profile pilot

## §1 Why this plan exists

The superseded software-only draft correctly identified duplicate fail2ban
logic, but review found that its selection was task-global, its migration
behavior was undefined, its runtime allowlist was deferred, and its test/live
gates were incomplete. This child plan keeps fail2ban as a small pilot while
making it consume the software composition inside each host's resolved
BaselineProfile.

Without those corrections, a multi-host Semaphore run would apply one
Environment-wide software list to every host, old payloads could silently stop
installing fail2ban, and a dynamic `tasks_from` value could reach an unvalidated
include.

## §2 Current state

### Confirmed facts

- `playbooks/vps/onboard.yml` owns one inline fail2ban path and reads
  `vps_task.fail2ban`.
- `playbooks/vps/modify.yml` owns a second fail2ban path under
  `vps_task.changes.fail2ban`.
- The onboarding examples enable fail2ban by default. A new empty software list
  would therefore be a behavior regression, not a neutral default.
- RHEL-family onboard currently reaches a separate EPEL prerequisite before
  fail2ban installation. The last live Rocky proof was blocked by mirror
  reachability.
- `roles/common/tasks/security.yml` uses tags but remains a monolithic task file;
  it is convention evidence, not already the reusable unit architecture.
- `make test-vps-examples-schema` validates checked-in examples only.
- `molecule-all` and the CI matrix enumerate four scenarios explicitly. A new
  scenario is invisible unless both are updated.
- Dynamic includes need an explicit runtime allowlist. Schema validation of
  repository examples alone cannot protect live Inventory/Environment values.
- Tags on a dynamic include need deliberate include/apply handling; they are not
  a substitute for per-host BaselineProfile assignment.

### Assumptions / unknowns

| Item | Classification | Close point |
|---|---|---|
| Exact resolver variable name and Inventory carrier | Depends on parent WU-0/WU-1 | Before this plan can move to PENDING_APPROVAL |
| RHEL test image/repository path for fail2ban | Needs implementation probe | Phase 1 |
| Whether `modify.yml` should support disable/remove in this pilot | Scope decision | Phase 0; recommended no removal, preserve existing configure/enable semantics |

## §3 Scope

### In scope

- Add one reusable fail2ban execution unit under `roles/vps_software/`.
- Add one fail2ban component under `profiles/vps/components/software/`.
- Select the unit from the software composition of the Node's resolved
  BaselineProfile, not from a Node-level `vps_task.software` list.
- Wire both onboard and modify to the same unit implementation.
- Keep EPEL/RHEL divergence inside the unit and fail with actionable evidence
  when package repositories are unreachable.
- Validate the unit name against a runtime catalog allowlist before dynamic
  include.
- Preserve default onboarding behavior through a deterministic legacy adapter.
- Preserve useful Ansible tag entry points with explicit include/apply tags.
- Add Debian- and RHEL-family Molecule coverage, idempotency, Make/CI wiring,
  governance registration, TSVS, and safe live acceptance.

### Out of scope

- Other software units.
- Category-based selection.
- A generic recursive plugin/DSL.
- Fail2ban removal/offboard unless a later child plan defines lifecycle
  semantics.
- Full convergence of `roles/common/tasks/security.yml`.
- Re-running full onboarding against already-managed u24/d13 as if they were
  fresh recoverable hosts.

### Compatibility contract

| Input state | Required result |
|---|---|
| Selected BaselineProfile contains `fail2ban`; no legacy field | Apply the unit with BaselineProfile/component config |
| Legacy onboard `vps_task.fail2ban.enabled=true`; no new selection | Compatibility adapter selects fail2ban and maps supported settings |
| Legacy onboard `enabled=false`; no new selection | Do not apply fail2ban |
| Legacy modify `vps_task.changes.fail2ban`; no new selection | Map supported change fields to the shared unit |
| BaselineProfile selection and legacy equivalent both present | Fail before mutation with a migration message |
| Unknown software/unit name | Fail before dynamic include |
| No new or legacy field in an existing minimal/standard example | Examples must be migrated so established default behavior remains explicit |

The adapter is temporary and must emit a deprecation message. Removal requires
consumer evidence and a later approved phase; it is not silently removed in
this pilot.

## §4 Implementation plan

### Phase 0 — Revalidate parent contract and approve this child

**Goal**: replace placeholder assumptions with the actual WU-1 resolver
contract.

**Pre-condition**: parent WU-1 is complete.

**Steps**:

1. Update this draft with the exact resolved-profile variable and carrier.
2. Inventory current onboard/modify fail2ban fields, templates, handlers, tags,
   generated files, package/repository steps, and docs.
3. Decide the non-removal lifecycle boundary and compatibility duration.
4. Present this plan as `PENDING_APPROVAL`.

**Gate**: explicit user approval.

**Deliverables**: approved child plan and implementation checklist.

### Phase 1 — Add catalog entry, unit, and automated coverage

**Goal**: create one independently testable fail2ban unit without changing the
proven lifecycle path yet.

**Pre-condition**: Phase 0 approved; current environment registry is fresh.

**Steps**:

1. Add the fail2ban catalog/profile data and schema.
2. Add `roles/vps_software/tasks/fail2ban.yml`, defaults/argument validation,
   template/handler ownership, and OS support assertions.
3. Put RHEL repository enablement/reachability handling inside the unit.
4. Add a `molecule/vps-software` scenario with:
   - a Debian-family platform;
   - a Rocky/RHEL-family platform;
   - selected-host install/config/service assertions;
   - unselected-host no-op assertions;
   - idempotent second converge.
5. Register the scenario in `molecule-all`, CI, testing governance, and a TSVS.

**Gate**: schema, lint, syntax, both OS-family scenario paths, and idempotency
pass. If the RHEL container repository is unreachable, classify the failure;
do not delete the RHEL platform to make the gate green.

**Deliverables**: isolated unit and catalog data, automated evidence, docs.

| RHEL probe result | Next action |
|---|---|
| Package/repository path works | Complete cross-family assertions |
| EPEL mirror is temporarily unreachable | Retry with a documented supported mirror/carrier; record external blocker if still unavailable |
| Package semantics differ from the plan | Stop and amend this plan before lifecycle wiring |

### Phase 2 — Wire BaselineProfile composition and migration

**Goal**: replace both inline copies without changing established default
behavior.

**Pre-condition**: Phase 1 passes.

**Steps**:

1. Add a pre-mutation assert that every selected software name exists in the
   runtime catalog and that legacy/new sources are not mixed.
2. Add a shared include path to onboard and modify using the software
   composition in the parent resolver's per-host BaselineProfile output.
3. Use explicit `apply.tags`/include tags so `--tags fail2ban` and the selected
   execution path behave as documented.
4. Add the compatibility mapping in the resolver/adapter.
5. Delete both inline fail2ban implementations only after the shared path's
   functional assertions pass.
6. Move the template/handler to its single owner and assert no old duplicate
   path remains.
7. Migrate minimal/standard/modify examples and strengthen schema tests.

**Gate**: a two-host fixture in one play selects fail2ban for one host and not
the other; legacy examples preserve behavior; mixed/unknown input fails before
mutation; syntax/lint/schema/Molecule pass.

**Deliverables**: shared lifecycle wiring, adapters, migrated examples, deleted
duplicates.

### Phase 3 — Semaphore and live acceptance

**Goal**: prove the change through the actual control/execution path without
using an already-managed host as a disposable takeover fixture.

**Pre-condition**: automated gates pass; explicit live go/no-go table is filled;
fresh recoverable Debian- and RHEL-family targets are available, or a missing
target is recorded as a blocker.

**Steps**:

1. Verify the live Semaphore Inventory BaselineProfile assignment with the same
   runtime validator used by playbooks.
2. On one fresh recoverable Debian-family target, run onboard, switch Inventory
   to the managed channel, run audit, and require `success` + `changed=0`.
3. Repeat on one fresh recoverable RHEL-family target with package reachability
   preflight.
4. Run modify through the shared unit on a managed test target and verify a
   deterministic setting change plus idempotent repeat.
5. Run `make controller-vps-smoke` for the managed audit segment.
6. Record task IDs, redacted recaps, resource identifiers, and plan
   contradictions.

**Gate**: both OS-family live paths pass. If RHEL infrastructure remains
unavailable, Phase 3 remains blocked and the feature is not called
cross-family complete.

**Deliverables**: live evidence and round changelog.

### Phase 4 — Documentation and closeout

**Goal**: make the new location and migration behavior discoverable.

**Pre-condition**: Phase 3 passed.

**Steps**:

1. Update the profile README/catalog, VPS operator guide, feature map, testing
   governance, TSVS index, CHANGELOG, and TODO.
2. Document legacy adapter duration and removal trigger.
3. Write reflection and advance this plan to `COMPLETED`.

**Gate**: docs point to the profile library as the desired-state entry; no docs
recommend editing an overwritten source.

**Deliverables**: synchronized docs and closeout evidence.

## §5 Verification

| Phase | Verification method | Pass condition | Evidence |
|---|---|---|---|
| 1 | schema test + Molecule Debian/RHEL + idempotency | selected hosts converge; unselected host untouched; second run has no changes | command output in round changelog |
| 2 | two-host fixture + legacy/mixed/unknown input tests + lifecycle syntax | two BaselineProfiles produce different software outcomes in one run; old defaults preserved; invalid input stops before mutation | tests + diff evidence |
| 3 | Semaphore task runs + managed audit smoke | Debian and RHEL onboard/modify succeed; repeat audit `changed=0` | task ids, redacted recap, TSVS |
| 4 | link/search/docs checks | one documented owner and migration path | closeout changelog |

Required local surfaces include `make test-vps-examples-schema`,
`make vps-lifecycle-syntax`, the registered `vps-software` Molecule scenario,
and the repository's normal push gate. Exact commands are updated in Phase 0
if the parent adds a dedicated profile validator target.

## §6 Risks and fallbacks

| Risk | Likelihood | Impact | Mitigation | Fallback |
|---|---|---|---|---|
| Default fail2ban behavior disappears | High without migration | High | Explicit compatibility table and migrated examples | Restore inline block and adapter, then reassess |
| Dynamic include accepts arbitrary task filename | Medium | High | Runtime catalog allowlist before include | Replace dynamic include with static dispatcher |
| Tags skip included work unexpectedly | Medium | Medium | Explicit include/apply tags and tag-specific test | Document selection-only execution and remove unsupported tag promise |
| Multi-host run still uses one software list | High in old design | High | Resolve one BaselineProfile per host and test two baselines in one play | Declare one-host-per-run temporary limitation and block composition claim |
| RHEL package source unavailable | Medium | Medium | Reachability preflight and cross-family container/live gates | Keep RHEL gate blocked; do not narrow support silently |
| Existing managed hosts are locked out by retest | Low-Medium | High | Fresh recoverable targets and separate live approval | Console/reinstall recovery; revert lifecycle wiring |

## §7 Post-completion checklist

- [ ] Parent catalog links the fail2ban profile and its supported OS families.
- [ ] Inline onboard/modify duplicates are gone.
- [ ] Legacy adapter and removal trigger are documented.
- [ ] Makefile, CI, testing governance, and TSVS register the new scenario.
- [ ] Operator guide assigns one BaselineProfile per host and does not expose
      software components as routine Node-level choices.
- [ ] Feature map and CHANGELOG reflect the behavior.
- [ ] TODO records the child completion without marking the whole parent
      profile work complete.
- [ ] Round changelog includes automated/live evidence and reflection.
- [ ] This plan advances to `COMPLETED` only after both family gates pass.

## Next steps

- Wait for the parent direction and WU-1 identity migration contract.
- Revalidate this draft in Phase 0, then present it separately for approval.
- Do not implement fail2ban extraction from the superseded 2026-07-12 draft.
