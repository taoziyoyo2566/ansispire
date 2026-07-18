> **Status**: DRAFT
> **Created**: 2026-07-18
> **Branch**: feat/vps-profile-catalog
> **Classification**: [L2] Architecture / Execution
> **Plan type**: Execution plan
> **Approval scope**: implementation approach
> **Parent plan**:
> [`plan-composable-vps-profiles-2026-07-17.md`](plan-composable-vps-profiles-2026-07-17.md)
> **Blocks implementation**: only WU-1 catalog foundation and identity migration
> **Does not supersede**: the approved parent direction, the WU-2 fail2ban
> execution plan, or the existing VPS takeover safety gates
> **Draft blocker**: WU-0 must publish `investigation-profile-carrier.md`, and
> its carrier/ownership decision must be accepted before this plan can move to
> `PENDING_APPROVAL`.

# Execution — VPS profile foundation and identity migration

## §1 Why this plan exists

1. **What is missing**: the approved profile direction defines one
   `BaselineProfile` per Node, but the repository has no profile catalog,
   resolver, identity component, or execution adapter. The active VPS path still
   reads the managed account directly from `vps_task.managed`.
2. **Why it matters**: user, public-key, group, shell, and sudo policy are split
   among `vps_task.managed`, `common__deploy_users`, and
   `infra_baseline_mgr_user`. Semaphore bootstrap also rewrites
   `vps-onboard-env` JSON from a checked-in example, so an operator cannot rely
   on one durable configuration owner.
3. **Why now**: the parent direction was approved on 2026-07-17 and names
   identity as the first migration pilot. WU-1 needs a separately reviewable
   implementation contract before any catalog code or lifecycle behavior
   changes.

This plan implements only the catalog foundation and identity migration. It
does not implement the fail2ban/software pilot, host-policy migration,
ServiceProfile execution, or removal of compatibility fields.

## §2 Current state

### Confirmed repository facts

- `playbooks/vps/onboard.yml` aliases `vps_task.managed` to `vps_managed` and
  directly creates groups, the managed user, authorized keys, and a sudoers
  file before the SSH cutover.
- `playbooks/vps/examples/onboard.minimal.yml` stores the managed identity inside
  the task payload. `vps_task.schema.json` validates the top-level section name
  but intentionally leaves its inner shape permissive.
- `controller/semaphore/bootstrap.yml` reads the checked-in minimal example into
  `vps_onboard_env_json`, creates `vps-onboard-env`, then sends that same JSON
  during every converge `PUT`. The same Environment also carries the required
  vault-free `ANSIBLE_CONFIG` process environment.
- The earlier runtime investigation
  [`IVG-SEMAPHORE-INVENTORY-API`](../../reference/investigations/IVG-SEMAPHORE-INVENTORY-API.md)
  proved against pinned Semaphore `v2.18.2` that:
  - a `static` inventory persists and returns its whole inventory blob;
  - `PUT` replaces that whole object;
  - a task-level `environment` JSON string can deliver a nested `vps_task`.
  It did not select the final host/group encoding for profile assignment.
- `config/manifest.yml` pins Semaphore `v2.18.2`; current Semaphore web
  documentation may describe features added after that version and therefore
  cannot replace the WU-0 runtime probe.
- The repository already configures project-root `filter_plugins/` in
  `ansible.cfg`, directly unit-tests pure filters, and registers
  `make test-filters` in `make verify`.
- No `profiles/vps/` directory or profile resolver exists.
- `roles/infra_baseline` actively creates `infra_baseline_mgr_user`, its group,
  sudoers rule, and authorized-key file; `playbooks/deploy_target.yml` invokes
  that role.
- `roles/common` can create zero or more `common__deploy_users`. Repository
  search found no tracked non-test assignment that makes this list non-empty,
  but `common` is still used by `site.yml` and role dependencies. External
  inventory or operator-supplied values remain an unproven consumer.
- Existing verification includes:
  - `make test-vps-examples-schema`;
  - `make vps-lifecycle-syntax`;
  - `make test-filters`;
  - `molecule test -s common`;
  - `make test-api-contract`;
  - `TSVS-VPS-ONBOARD-E2E-001` and `make controller-vps-smoke`.
  There is no resolver/catalog test or isolated management-identity scenario.
- Ubuntu 24.04 and Debian 13.5 completed the existing onboard-to-managed audit
  loop. Rocky 9 remains blocked at the separate EPEL/fail2ban path; this plan
  must not relabel that partial evidence as full RHEL onboard acceptance.

### Current ownership map

| Concern | Current writer/input | Current consumer | Migration issue |
|---|---|---|---|
| VPS managed account | `vps_task.managed` in Environment/task payload | inline tasks in `playbooks/vps/onboard.yml` | task-wide input is acting as durable desired state |
| Target baseline manager | `infra_baseline_mgr_*` role variables | `roles/infra_baseline` | second management-account executor and schema |
| General deploy users | `common__deploy_users` | `roles/common/tasks/packages.yml` | may overlap the managed account, but can also represent distinct application users |
| Environment JSON | checked-in `onboard.minimal.yml` | `controller/semaphore/bootstrap.yml` | bootstrap overwrites operator-edited JSON |
| SSH private credential | Semaphore Key Store | Semaphore task runner | correct owner; must remain outside Git profiles |

### Verified external facts

- Ansible inventory supports host and group variables; host values override
  group values, and extra vars have higher precedence than inventory. The
  resolver must therefore receive explicit sources and reject ambiguous
  legacy/new combinations instead of relying on ambient variable precedence.
- Ansible filter plugins are intended for controller-side data manipulation and
  can be loaded from a configured `filter_plugins` path. This matches the
  repository's existing pure-function test seam.
- Ansible role argument specifications insert validation before role execution.
  A canonical identity executor can use this boundary to reject malformed
  identity data before creating accounts or sudoers files.
- Current Semaphore documentation says static inventories are editable in the
  web UI and can store inventory variables. It separately describes Variable
  Groups as reusable JSON configuration and Survey Variables as per-run typed
  input. Availability and exact behavior in pinned `v2.18.2` remain runtime
  questions, not assumed facts.

### Unknowns and close points

| ID | Unknown | Classification | Close point | Method / fallback |
|---|---|---|---|---|
| U1 | Exact serialized carrier for one baseline name and zero/many service names | Needs runtime probe | WU-0 before this plan becomes `PENDING_APPROVAL` | `ansible-inventory` fixtures plus pinned Semaphore UI/API round-trip |
| U2 | Whether Variable Groups or Survey Variables exist with the documented shape in `v2.18.2` | Needs runtime probe | WU-0 | Official docs plus disposable pinned API/UI probe; retain a minimal Environment/task payload if absent |
| U3 | Exact active contents and owner of live `vps-onboard-env` and `vps-fleet` | Needs operator/export evidence | Phase 0 | Export identifiers and sanitized non-secret JSON/inventory before implementation |
| U4 | Whether external callers set `common__deploy_users` to the same automation account | Needs consumer evidence | Phase 0 inventory; Phase 5 decision | Repo call graph, inventory search, operator confirmation; keep compatibility surface if unproven |
| U5 | Compatibility duration for `vps_task.managed` and `infra_baseline_mgr_*` | Needs operator decision | Phase 0 | Record release/round exit condition; default is retain through this WU |
| U6 | Fresh recoverable live targets for identity/SSH validation | Needs operator decision | Phase 6 | Use explicitly approved disposable targets; otherwise record live gate blocked |

### Entry criteria for approval

This document stays `DRAFT` until all of the following are true:

- `investigation-profile-carrier.md` records the selected carrier, exact
  variable names, UI/API round-trip evidence, and ownership matrix;
- the owner branch exists from the intended `feat/target-architecture`
  baseline, with unrelated working-tree changes separated safely;
- the carrier-dependent placeholders in this plan are replaced with the
  accepted serialization;
- the compatibility duration and live-test target policy have named owners;
- the revised document is presented as `PENDING_APPROVAL`.

## §3 Scope

### Goal and expected effect

Deliver one Git-owned, schema-validated VPS profile catalog and one canonical
management-identity execution path. A Node's selected `BaselineProfile` must
resolve independently per inventory host before any remote mutation. The
existing `vps_task.managed` input remains a visible temporary adapter, and
Semaphore bootstrap must stop overwriting operator-owned JSON.

When WU-1 is complete:

- operators can find non-secret identity policy under `profiles/vps/`;
- per-host inventory assignment resolves to one BaselineProfile and one identity
  component;
- invalid, unknown, conflicting, or mixed legacy/new input fails before account,
  sudoers, key, firewall, or SSH changes;
- private credentials remain in Semaphore Key Store;
- `onboard.yml` and overlapping legacy paths call one identity executor;
- re-running controller bootstrap preserves operator-owned data;
- docs and tests identify the new owner and the remaining compatibility window.

### Implementation policy

1. **Plain data, not a new DSL**: profile files contain typed YAML data only.
   They cannot contain task names, Jinja snippets, arbitrary file paths, or
   executable content.
2. **Explicit catalog load**: `catalog.yml` allowlists every profile/component
   file. A loader validates safe relative paths before reading files, preserves
   documents as a list so duplicate names can be detected, and passes explicit
   data into a side-effect-free resolver.
3. **Per-host resolution**: the resolver accepts the current host's assignment,
   catalog documents, OS facts, allowlisted exception data, and optional legacy
   input. It does not read ambient `hostvars`, access the network/filesystem, or
   mutate state.
4. **Single mutation boundary**: a reusable `managed_identity` role owns group,
   user, authorized-key, and sudoers resources. The resolver never performs
   remote work.
5. **Compatibility is explicit**: new profile assignment plus equivalent legacy
   input is an error. Legacy-only input maps deterministically, reports a
   deprecation source, and remains covered until a separately approved removal.
6. **Bootstrap preserves data**: controller bootstrap may converge resource
   existence, template binding, and required process environment, but it must
   round-trip existing operator JSON rather than replacing it with the example.
7. **Safety ordering is fixed**: profile resolution and identity validation are
   inserted before mutation; the proven SSH/firewall cutover sequence remains
   in the lifecycle playbook and is not made profile-composable.

### Logical data contract

WU-0 chooses the serialized Inventory form, but the resolver-facing logical
assignment remains:

```yaml
saberu_profile_assignment:
  baseline: personal-standard
  services: []
```

The first BaselineProfile composes one identity component:

```yaml
api_version: ansispire.io/v1alpha1
kind: BaselineProfile
name: personal-standard
identity: managed-ansible
composition:
  host_policies: []
  software: []
```

The identity component contains non-secret desired state:

```yaml
api_version: ansispire.io/v1alpha1
kind: IdentityComponent
name: managed-ansible
user: ansible
groups:
  common:
    - ssh-users
  by_os_family:
    Debian:
      - sudo
    RedHat:
      - wheel
shell: /bin/bash
authorized_keys:
  - public_key_content: "ssh-ed25519 REPLACE-WITH-PUBLIC-KEY"
sudo:
  nopasswd: true
```

Private keys, passwords, API tokens, and secret values are invalid in this
catalog. Public keys are allowed but must still be redacted from committed
execution evidence when they could identify a real operator or host.

The resolver produces one namespaced object:

```yaml
saberu_resolved_profile:
  source: catalog
  baseline: personal-standard
  os_family: Debian
  identity:
    component: managed-ansible
    user: ansible
    groups: [sudo, ssh-users]
    shell: /bin/bash
    authorized_keys:
      - public_key_content: "<redacted>"
    sudo:
      nopasswd: true
  composition:
    host_policies: []
    software: []
  diagnostics:
    legacy_adapter_used: false
    node_exception_keys: []
```

The exact public-key values are present at runtime but are omitted from normal
diagnostic output.

### Compatibility contract

| Input state | Required result |
|---|---|
| Valid per-host profile assignment; no legacy identity | Resolve catalog identity and call the canonical executor |
| Legacy `vps_task.managed`; no profile assignment | Map supported fields to the resolved identity shape, mark `source: legacy-vps-task`, and emit a deprecation message |
| Profile assignment and legacy `vps_task.managed` both present | Fail before mutation with the conflicting source names |
| Unknown baseline/component name | Fail before any dynamic file read or remote mutation |
| Duplicate catalog kind/name | Fail catalog validation |
| Unsafe catalog path, unknown key, invalid group/user/shell/sudo value | Fail catalog validation |
| `infra_baseline_mgr_*` path during compatibility | Map to the canonical identity role; keep variable names until the declared exit gate |
| `common__deploy_users` proven to represent application users only | Keep its separate domain, document the distinction, and do not claim it is the management-identity owner |
| `common__deploy_users` proven to create the same management identity | Route the overlapping item through the canonical role; retain list compatibility until consumer evidence permits removal |

The identity resolver flattens `groups.common` plus the current
`groups.by_os_family` entry. Missing or unsupported OS-family mappings fail
before the role runs; the role does not guess an administrative group.

### Recovery and rollback contract

- Each phase is independently committable and keeps the preceding verified path
  usable until its replacement passes.
- WU-1 does not delete legacy input fields. If catalog resolution or lifecycle
  wiring fails before live acceptance, the operator can run the exported
  legacy-only payload while the new assignment is removed from the test host.
- Before controller changes, export the current Environment and Inventory. If
  bootstrap preservation fails, stop bootstrap use and restore the exported
  object through the existing operator/API recovery path.
- Before live identity/SSH work, preserve provider console or reinstall access,
  the prior Inventory line, and the legacy payload outside Git. A failed managed
  login is a stop condition, not permission to continue with more hosts.
- Removal of adapters, keys, users, sudoers files, or old API fields is not a
  rollback technique in this WU and requires its own approved lifecycle scope.

### Expected modification surfaces

| Surface | Planned change |
|---|---|
| `profiles/vps/README.md` | Operator-facing configuration location, ownership, examples, secret boundary, compatibility policy |
| `profiles/vps/catalog.yml` | Allowlisted registry of profile/component documents |
| `profiles/vps/schemas/*.schema.json` | Draft-07 schemas for catalog manifest, BaselineProfile, IdentityComponent, and assignment |
| `profiles/vps/baseline/personal-standard.yml` | First complete BaselineProfile |
| `profiles/vps/components/identity/managed-ansible.yml` | First identity component |
| `filter_plugins/vps_profiles.py` | Side-effect-free manifest validation and per-host resolver |
| `playbooks/vps/tests/test_profile_resolver.py` | Pure resolver/catalog/compatibility unit tests |
| `playbooks/vps/tasks/resolve_profile.yml` | Thin catalog-load and resolver invocation boundary |
| `roles/managed_identity/` | Canonical identity mutation role with argument spec and `no_log` key handling |
| `molecule/managed-identity/` | Debian- and RHEL-family functional/idempotency scenario |
| `playbooks/vps/onboard.yml` | Resolve before mutation and consume only the resolved identity object |
| `playbooks/vps/examples/*.yml` and `vps_task.schema.json` | Profile-assignment examples plus explicit temporary legacy contract |
| `roles/infra_baseline/` | Compatibility mapping to canonical executor; remove duplicate resource writes only after its tests pass |
| `roles/common/` | Consumer classification; change only if overlap with management identity is proven |
| `controller/semaphore/bootstrap.yml` | Preserve existing Environment JSON while converging required resource contract/process environment |
| `controller/semaphore/bootstrap_preflight.yml` or `controller/semaphore/preflight/` | Disposable sentinel-preservation contract for Environment update behavior |
| `Makefile`, `.github/workflows/ci.yml` | Register resolver/catalog and managed-identity tests |
| testing governance and TSVS | Register every new target/scenario and identity/profile acceptance contract |
| feature maps, operator docs, `ARCHITECTURE.md`, `README.md`, `CHANGELOG.md`, `TODO.md` | Promote current ownership and operator workflow after behavior lands |

### In scope

- WU-0 result consumption and exact carrier freeze.
- Catalog manifest, schemas, one identity component, and one BaselineProfile.
- Explicit, pure per-host resolver and diagnostics.
- Canonical management-identity role.
- VPS legacy adapter and deterministic conflict rejection.
- `infra_baseline` compatibility mapping.
- `common__deploy_users` consumer classification and only the overlap proven by
  evidence.
- Bootstrap preservation of operator-owned JSON.
- Automated cross-family, controller-contract, and disposable two-host
  verification.
- A separately authorized live identity/SSH acceptance run.
- Required stable docs, testing registration, round evidence, and reflection.

### Out of scope

- WU-2 fail2ban extraction or any other software component.
- Host-policy component migration, including SSH/firewall policy
  decomposition.
- ServiceProfile execution.
- Offboard/reverse identity removal.
- Deleting `vps_task.managed`, `infra_baseline_mgr_*`, or
  `common__deploy_users` merely because adapters exist.
- A custom UI/API, profile database, or profile compiler service.
- Secret storage in Git or migration of private keys out of Key Store.
- Production fleet rollout without the exact live go/no-go gate.

### Capability fit

- Use repository search and call-graph inspection for consumer classification.
- Use the existing Python/filter-plugin seam for deterministic resolver tests.
- Use `ansible-inventory` fixtures for host-scoped assignment proof.
- Use Molecule for the canonical identity role and the existing disposable
  Semaphore preflight harness for bootstrap-preservation behavior.
- Do not use sub-agents unless the user explicitly requests delegation.
- Do not create a Codex skill/plugin; this is product configuration and belongs
  in repository data, code, and documentation.

## §4 Implementation plan

### Phase 0 — Close WU-0 and freeze execution inputs

**Goal**: replace every carrier-dependent placeholder and make the migration
recoverable before code changes.

**Pre-condition**: direction remains approved; the owner branch is based on the
intended target-architecture baseline; unrelated changes are preserved.

**Steps**:

1. Complete `investigation-profile-carrier.md` with:
   - INI and YAML `ansible-inventory` fixtures;
   - per-host and per-group scalar/list assignment results;
   - pinned `v2.18.2` UI/API round-trip behavior;
   - Variable Group and Survey availability;
   - chosen durable assignment owner and one-run input owner.
2. Replace the logical placeholder in this plan with the exact Inventory
   serialization and variable names.
3. Export the current `vps-fleet` and `vps-onboard-env` identifiers and
   sanitized non-secret content. Record where the operator keeps the full
   recovery copy without committing it.
4. Inventory every repository and operator-known consumer of
   `vps_task.managed`, `infra_baseline_mgr_*`, and `common__deploy_users`.
5. Record the compatibility exit rule, defaulting to retention through WU-1.
6. Revalidate official docs and pinned runtime behavior if Semaphore/Ansible
   versions changed.
7. Move this plan to `PENDING_APPROVAL` and present the exact revised document.

**Gate**: explicit user approval of the carrier decision and this execution
plan. Direction approval alone does not pass this gate.

**Deliverables**: completed carrier investigation, sanitized recovery ledger,
consumer map, approval-ready execution plan.

| WU-0 result | Plan action |
|---|---|
| Per-host baseline scalar and service list survive the selected static inventory format | Freeze that encoding and proceed |
| Baseline scalar works but service-list encoding does not | Freeze baseline only for WU-1; keep services empty and defer their carrier to WU-4 |
| Only a task-wide Environment can carry the assignment | Stop; this contradicts per-host resolution and requires a direction addendum |
| Pinned UI/API mutates or loses assignment data | Stop; select a different carrier or amend direction before implementation |

### Phase 1 — Add catalog contracts and pure resolution

**Goal**: build and validate the catalog without changing lifecycle behavior.

**Pre-condition**: Phase 0 plan gate passed.

**Steps**:

1. Add `profiles/vps/README.md`, `catalog.yml`, the schema set, the
   `managed-ansible` identity component, and `personal-standard` baseline.
2. Make `catalog.yml` the only file registry. Reject absolute paths, `..`,
   unexpected directories, duplicate `(kind, name)` pairs, unknown kinds, and
   unregistered files.
3. Add `filter_plugins/vps_profiles.py` with pure functions for:
   - manifest validation;
   - runtime object-shape and unknown-key validation without assuming the
     controller image provides the `jsonschema` package;
   - schema-independent cross-document checks;
   - assignment resolution;
   - OS/dependency/conflict checks;
   - allowlisted Node exceptions;
   - legacy/new conflict detection;
   - redacted diagnostics.
4. Add `playbooks/vps/tasks/resolve_profile.yml` to:
   - read only the fixed Git catalog root;
   - validate manifest paths before loading entries;
   - pass explicit catalog documents and current-host inputs to the resolver;
   - set only `saberu_resolved_profile`.
5. Add `playbooks/vps/tests/test_profile_resolver.py` covering valid resolution,
   two different hosts, unknown/duplicate/unsafe inputs, mixed sources,
   deterministic ordering, and diagnostic redaction.
6. Add `make test-vps-profiles` and register it in `make verify`, CI,
   `testing-governance.md`, and a new TSVS.

**Gate**:

- schema/meta-schema validation passes;
- resolver unit tests pass;
- an `ansible-inventory` two-host fixture produces distinct assignment inputs;
- catalog loading performs no remote or external mutation;
- unknown and mixed inputs fail before returning a resolved object.

**Deliverables**: catalog foundation, pure resolver, registered L1/L2 tests,
initial profile TSVS.

### Phase 2 — Add the canonical identity executor

**Goal**: provide one validated, reusable mutation boundary for management
identity without wiring it into the proven onboard sequence yet.

**Pre-condition**: Phase 1 gate passed.

**Steps**:

1. Add `roles/managed_identity/` with:
   - namespaced input `managed_identity`;
   - `meta/argument_specs.yml`;
   - group/user/home/shell handling;
   - authorized-key handling with `no_log: true`;
   - a mutually exclusive compatibility-only remote
     `authorized_keys_source_path` for the current `infra_baseline` copy-from-root
     behavior, allowlisted to `/root/.ssh/authorized_keys`;
   - sudoers template/copy validated by `visudo`;
   - stable resource naming and ownership;
   - no SSH daemon, firewall, package, or controller logic.
2. Define check-mode behavior and preflight/validate explicit keys or the
   allowlisted remote source before group, user, sudoers, or key mutation.
3. Reject simultaneous explicit `authorized_keys` and
   `authorized_keys_source_path`. Keep `exclusive: false` during WU-1. Key
   removal/rotation needs separate
   lifecycle semantics and is not inferred from catalog absence.
4. Add `molecule/managed-identity/` with Debian- and RHEL-family platforms,
   invalid-input checks, functional assertions, and a zero-change second
   converge.
5. Register the scenario in `molecule-all`, CI, testing governance, and a
   managed-identity TSVS.
6. Compare resource paths with current onboard, `infra_baseline`, and `common`
   writers. Record every path that must be migrated or deliberately retained.

**Gate**: argument validation, both OS-family functional assertions, sudoers
validation, key secrecy, and idempotency pass without modifying lifecycle
playbooks.

**Deliverables**: canonical identity role, cross-family scenario, resource-owner
map, TSVS.

### Phase 3 — Wire per-host profiles into VPS onboard

**Goal**: make `onboard.yml` consume only a validated resolved identity while
preserving takeover order and compatibility.

**Pre-condition**: Phases 1 and 2 pass; current onboard recovery payload is
available.

**Steps**:

1. Invoke `playbooks/vps/tasks/resolve_profile.yml` as the first non-mutating
   pre-task after required facts are available and before package, group, user,
   sudoers, firewall, or SSH mutation.
2. Replace direct reads of `vps_task.managed` with
   `saberu_resolved_profile.identity`.
3. Replace the inline group/user/key/sudoers block with the canonical
   `managed_identity` role at the same ordering point.
4. Add the legacy-only adapter for `vps_task.managed`; reject legacy plus
   profile assignment before mutation and emit a deprecation message that names
   the configured exit gate.
5. Preserve:
   - `strategy: free`;
   - managed-channel validation using the task's Key Store transport key;
   - SSH service/socket detection;
   - firewall port choreography;
   - bootstrap-port closure ordering;
   - `no_log` on key-bearing values.
6. Update checked-in examples and make `vps_task.schema.json` describe both the
   profile-assignment path and temporary legacy path. Do not silently make an
   empty assignment select a profile.
7. Add syntax and local fixture tests for:
   - two hosts selecting different baselines;
   - legacy-only compatibility;
   - mixed-source failure;
   - unknown assignment failure;
   - no mutation task reached after resolution failure.

**Gate**: resolver, schema, syntax, role scenario, and two-host fixture pass;
task ordering diff confirms the SSH/firewall skeleton is unchanged.

**Deliverables**: profile-aware onboard path, explicit adapter, migrated
examples, pre-mutation failure coverage.

### Phase 4 — Stop bootstrap from overwriting operator data

**Goal**: retain resource convergence while removing bootstrap's ownership of
durable desired-state JSON.

**Pre-condition**: the WU-0 one-run input contract is frozen and current
Environment content is recoverable.

**Steps**:

1. Stop deriving converged `vps-onboard-env` JSON from
   `playbooks/vps/examples/onboard.minimal.yml`.
2. On create, seed only the minimal JSON required by the WU-0 one-run input
   contract; examples remain documentation/test fixtures, not live desired
   state.
3. On update, fetch and round-trip the existing Environment JSON while
   converging only repository-owned fields such as name, project binding, and
   required `ANSIBLE_CONFIG` process environment.
4. Preserve template binding and the existing Key Store credential path.
5. Add a disposable preflight test that:
   - creates an Environment with a non-secret sentinel JSON value;
   - runs the converge path;
   - proves the sentinel survives unchanged;
   - proves required process environment and template binding converge.
6. Update template descriptions and operator docs so they no longer instruct
   operators to edit a source bootstrap will replace.

**Gate**: `make test-api-contract` passes against pinned Semaphore; sentinel JSON
survives a second converge; no example payload is treated as live data.

**Deliverables**: ownership-safe bootstrap, disposable preservation contract,
corrected operator workflow.

| Existing Environment state | Required behavior |
|---|---|
| Resource absent | Create minimal contract-safe Environment |
| Resource exists with valid operator JSON | Preserve JSON exactly; converge repository-owned fields |
| Resource exists with invalid JSON/API shape | Fail without overwriting; report resource id and recovery action |
| Required process env missing | Add it while preserving JSON |

### Phase 5 — Converge overlapping legacy identity owners

**Goal**: route proven overlaps through the canonical role without deleting
unclassified compatibility APIs.

**Pre-condition**: canonical role and onboard wiring pass; Phase 0 consumer map
is complete.

**Steps**:

1. Replace `roles/infra_baseline`'s inline management-user/group/sudoers/key
   writes with a deterministic mapping from `infra_baseline_mgr_*` to
   `managed_identity`; use the canonical role's compatibility-only
   `authorized_keys_source_path: /root/.ssh/authorized_keys` so the current
   copy-from-root behavior remains explicit and tested.
2. Preserve existing `infra_baseline` defaults and resource behavior during the
   compatibility window; add regression assertions for user, group, sudoers,
   home, and authorized keys.
3. Classify `common__deploy_users` entries:
   - if they are application/deploy identities, document that domain boundary
     and leave their API intact;
   - if an entry represents the same management identity, map only that overlap
     to the canonical role and retain caller compatibility.
4. Do not remove a legacy variable or resource path until repository search,
   operator confirmation, and its registered scenario prove no remaining
   consumer.
5. Update deprecation messages and the owner matrix with the exact removal
   candidate for a later approved round.

**Gate**: `infra_baseline`, `common` when touched, managed-identity, and
full-stack relevant tests pass; repository search shows one writer for each
migrated resource path.

**Deliverables**: converged overlapping writers, documented non-overlapping
identity domains, retained compatibility surfaces.

| Consumer finding | Action |
|---|---|
| `infra_baseline` creates the same management account | Map to canonical role in WU-1 |
| `common__deploy_users` is empty or app-user-only | Keep it separate and document why it is not a competing management-identity owner |
| `common__deploy_users` creates the same management account | Map that overlap through the canonical role; retain list input |
| Consumer purpose remains unknown | Preserve current behavior and keep WU-1 closeout item open |

### Phase 6 — Acceptance, live gate, and closeout

**Goal**: prove the migration through local, controller, and explicitly
authorized live paths, then promote the accepted ownership model.

**Pre-condition**: Phases 1–5 pass; live target and recovery fields are complete.

**Steps**:

1. Run the complete automated matrix in §5.
2. Use a disposable two-host inventory fixture to prove distinct
   BaselineProfile assignment and resolved identity in one play.
3. Fill the live go/no-go table below and request exact per-run authorization.
4. On fresh recoverable test hosts:
   - preflight connection and package reachability;
   - run profile-based onboard;
   - switch Inventory to the managed channel;
   - run managed audit;
   - require `success`, `changed=0`, `failed=0`, and `unreachable=0`;
   - repeat bootstrap and prove operator profile assignment/Environment JSON
     remain unchanged.
5. If RHEL onboarding reaches the unrelated fail2ban/EPEL blocker, isolate and
   record it; do not claim full RHEL takeover. The managed-identity role still
   requires cross-family Molecule evidence.
6. Update `profiles/vps/README.md`, repository `README.md`, `ARCHITECTURE.md`,
   feature maps, operator guides, testing governance, TSVS, `CHANGELOG.md`,
   `TODO.md`, and the workstream hub.
7. Write `round<N>-YYYY-MM-DD.changelog.md`, using the actual round-completion
   date, with sanitized evidence and the execution-reflection answers.
8. Advance this plan to `COMPLETED` only when every required gate and checklist
   item is closed.

**Gate**: automated checks pass; live run has separate exact authorization;
stable docs identify one active owner; compatibility gaps are explicit.

**Deliverables**: automated/live evidence, stable ownership docs, round
changelog, completed execution plan.

#### Live go/no-go record

| Field | Required before a run |
|---|---|
| Target scope | exact disposable host aliases, inventory/group, OS family, expected count |
| Operation | exact template/playbook and selected BaselineProfile |
| Credential path | Semaphore Key Store entry name/id or approved manual key path, never the secret |
| Expected impact | user, groups, authorized keys, sudoers, SSH port, firewall, packages, services, files |
| Recovery | provider console/reinstall owner plus exported legacy payload/inventory location |
| Evidence | task id, sanitized recap, resolved-profile summary, post-run audit |
| Authorization | current per-run user confirmation; direction/plan approval is insufficient |

| Live result | Closeout action |
|---|---|
| Debian and RHEL test paths pass | Record both; close cross-family live identity gate |
| Debian passes; RHEL hits the existing EPEL blocker after identity succeeds | Preserve partial identity evidence, keep full RHEL takeover wording blocked |
| Resolver/identity behavior contradicts the plan | Stop further live runs, classify the contradiction, and amend the plan |
| Managed login fails | Use console/reinstall recovery, restore exported input, and keep WU-1 incomplete |

## §5 Verification

| Phase | Verification method | Pass condition | Evidence artifact |
|---|---|---|---|
| 0 | carrier investigation + sanitized export review | exact carrier and owners frozen; recovery copy exists; plan approved separately | `investigation-profile-carrier.md` + approval record |
| 1 | JSON Schema meta-validation, `make test-vps-profiles`, `ansible-inventory` two-host fixture | valid catalog resolves deterministically; unsafe/unknown/duplicate/mixed input fails; hosts resolve independently | profile TSVS + round changelog |
| 2 | role argument validation + `molecule test -s managed-identity` + idempotence | Debian/RHEL user/group/key/sudoers assertions pass; second converge has zero changes; secret-bearing output suppressed | managed-identity TSVS |
| 3 | `make test-vps-examples-schema`, resolver tests, `make vps-lifecycle-syntax`, task-order review | new/legacy paths are deterministic; invalid input reaches no mutation; takeover ordering unchanged | test output + reviewed diff |
| 4 | `make verify` + `make test-api-contract` with sentinel Environment | operator JSON survives create/converge; required env/template fields converge | sanitized preflight output |
| 5 | relevant `infra_baseline`, `common`, managed-identity, and full-stack checks | each migrated resource has one writer; compatibility inputs retain behavior | scenario output + owner search |
| 6 | complete automated matrix + approved Semaphore test-host runs + managed audit | selected BaselineProfile applies intended identity; managed audit is success/zero-change; bootstrap preserves assignment | task ids, redacted recaps, TSVS, changelog |

Required automated commands after all planned surfaces land:

```text
make test-vps-profiles
make test-vps-examples-schema
make test-filters
make vps-lifecycle-syntax
molecule test -s managed-identity
molecule test -s common                 # when common is changed
make verify
make test-api-contract
make verify-full                        # because role/Make/CI surfaces change
```

Any new target or scenario must be registered in the Makefile, CI,
`docs/governance/testing-governance.md`, and
`docs/reference/test-specs/INDEX.md` in the same phase. A command that cannot
run is a named gap, not a pass.

## §6 Risks and fallbacks

| Risk | Likelihood | Impact | Mitigation | Fallback |
|---|---|---|---|---|
| Wrong per-host carrier makes assignment task-global | Medium until WU-0 | High | hard WU-0 gate and two-host fixture | stop and amend direction; do not implement WU-1 |
| Resolver becomes an implicit precedence engine or DSL | Medium | High | explicit inputs, pure functions, fixed schema, no executable fields | reduce to baseline-name lookup with no Node exceptions |
| Profile and legacy input both mutate the host | High without guard | High | reject mixed sources before mutation | run legacy-only adapter until assignment is corrected |
| Identity migration locks out SSH | Medium | High | preserve cutover order, fresh recoverable hosts, Key Store reuse, console owner | recover via console/reinstall and restore exported payload |
| Bootstrap destroys operator data | High in current behavior | High | read/round-trip existing JSON and sentinel test | restore export; revert to create-only resource management |
| Public/private key boundary is violated | Low | High | schemas reject private-key/password fields; Key Store remains owner; secret scan/no_log | stop, remove exposure through authorized remediation, rotate compromised secret |
| Canonical role changes current sudoers/key behavior | Medium | High | resource-path inventory, compatibility mapping, cross-family Molecule | retain old writer until equivalence is proven |
| `common__deploy_users` is wrongly treated as management identity | Medium | Medium | classify consumers and resources before edits | keep common domain separate and correct owner documentation |
| RHEL live proof is hidden by EPEL reachability | Medium | Medium | role-level cross-family proof and explicit live result table | keep full RHEL takeover blocked; do not narrow support silently |
| New tests are invisible to normal verification | Medium | Medium | same-phase Make/CI/governance/TSVS registration | block phase closeout until registered |

## §7 Post-completion checklist

- [ ] WU-0 investigation records the selected carrier and stable owner.
- [ ] `profiles/vps/README.md` is the operator-facing configuration entry.
- [ ] Catalog schemas reject secrets, unknown keys, duplicate names, and unsafe
      paths.
- [ ] Two hosts resolve distinct BaselineProfiles in one fixture.
- [ ] `playbooks/vps/onboard.yml` consumes only the resolved identity object.
- [ ] Legacy-only input works; mixed legacy/new input fails before mutation.
- [ ] `managed_identity` owns every migrated group/user/key/sudoers resource.
- [ ] `infra_baseline` overlap routes through the canonical executor.
- [ ] `common__deploy_users` is either mapped where overlapping or documented as
      a distinct application/deploy-user domain.
- [ ] Bootstrap preserves operator Environment JSON and profile assignment.
- [ ] Private credentials remain in Key Store; committed evidence is redacted.
- [ ] Makefile, CI, testing governance, and TSVS register every new test.
- [ ] Repository `README.md`, `ARCHITECTURE.md`, feature maps, operator docs,
      `CHANGELOG.md`, `TODO.md`, and workstream README reflect the landed state.
- [ ] `round<N>-YYYY-MM-DD.changelog.md` records automated and live evidence.
- [ ] Closeout reflection states whether a repo, plan, runtime, or rules
      assumption proved false.
- [ ] Remaining compatibility fields have an owner and separately approvable
      removal trigger.
- [ ] This document advances to `COMPLETED` only after all required gates pass.
- [ ] WU-2 fail2ban plan is revalidated against the final resolver/provider
      contract before it can move beyond `DRAFT`.

### Evidence map / sources checked 2026-07-18

| Claim / dependency | Source | Classification / close point |
|---|---|---|
| Approved hierarchy, ownership split, and WU-1 boundary | [`plan-composable-vps-profiles-2026-07-17.md`](plan-composable-vps-profiles-2026-07-17.md) | Approved repo direction |
| Static inventory whole-object CRUD and task-level Environment payload on pinned Semaphore | [`IVG-SEMAPHORE-INVENTORY-API`](../../reference/investigations/IVG-SEMAPHORE-INVENTORY-API.md) §8 | Verified pinned-runtime evidence; assignment carrier still closes at WU-0 |
| Inventory can store host/group variables | https://docs.ansible.com/projects/ansible/latest/getting_started/get_started_inventory.html | Verified current official docs; pinned fixture at WU-0 |
| Variable precedence can make extra vars override inventory | https://docs.ansible.com/projects/ansible/latest/playbook_guide/playbooks_variables.html | Verified current official docs; design rejects ambiguous sources |
| Filter plugins are a controller-side data-manipulation extension loaded from configured paths | https://docs.ansible.com/projects/ansible/latest/plugins/filter.html | Verified current official docs; pinned local test in Phase 1 |
| Role argument specs validate inputs before role execution | https://docs.ansible.com/projects/ansible-core/devel/playbook_guide/playbooks_reuse_roles.html#role-argument-validation | Verified current official docs; pinned Molecule proof in Phase 2 |
| Semaphore static Inventory is UI-editable and stores inventory variables | https://semaphoreui.com/docs/user-guide/inventory | Verified current docs; exact `v2.18.2` behavior closes at WU-0 |
| Variable Groups are reusable JSON configuration | https://semaphoreui.com/docs/user-guide/environment | Verified current docs; feature/version probe at WU-0 |
| Survey Variables are per-run typed Ansible extra vars | https://semaphoreui.com/docs/user-guide/task-templates/survey-vars | Verified current docs; feature/version probe at WU-0 |
| Current code owners and test seams | `playbooks/vps/onboard.yml`, `controller/semaphore/bootstrap.yml`, `roles/common/`, `roles/infra_baseline/`, `Makefile`, testing governance | Known repo facts; re-check at each phase start |

## Next steps

- Complete WU-0 and write `investigation-profile-carrier.md`.
- Replace carrier-dependent placeholders and record compatibility/live owners.
- Present the revised plan as `PENDING_APPROVAL`.
- Do not implement WU-1 from this `DRAFT`.
- Keep WU-2 fail2ban work blocked until WU-1 freezes and proves the resolver
  provider contract.
