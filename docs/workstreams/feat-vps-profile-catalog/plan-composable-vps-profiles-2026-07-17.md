> **Status**: APPROVED
> **Approved**: 2026-07-17
> **Created**: 2026-07-17
> **Branch**: feat/vps-profile-catalog
> **Classification**: [L2] Architecture
> **Plan type**: Direction plan
> **Approval scope**: direction
> **Parent plan**:
> [`../../reviews/feat-target-architecture/plan-saberu-vps-takeover-execution-2026-06-24.md`](../../reviews/feat-target-architecture/plan-saberu-vps-takeover-execution-2026-06-24.md)
> **Blocks implementation**: yes — all new profile/catalog code and all
> behavioral changes to the proven VPS lifecycle path
> **Does not supersede**: the approved Semaphore-native takeover direction or
> its live-operation gates
> **Updated**: 2026-07-17 — user confirmed `BaselineProfile` as the higher-level
> design: a Node selects one BaselineProfile, while identity, host policy, and
> baseline software remain internal reusable components.
> **Updated**: 2026-07-17 — moved the active topic to `docs/workstreams/` while
> preserving its historical filename, and routed WU-0 probe evidence to an IVG;
> approval scope is unchanged.
> **Updated**: 2026-07-18 — corrected documentation routing: the WU-0 probe is
> topic-owned evidence in `investigation-profile-carrier.md`; the superseded
> software-only predecessor remains a separate legacy topic because
> supersession alone does not establish absorption. Approval scope,
> implementation approach, and verification criteria are unchanged.

# Direction — Composable VPS configuration profiles

## §1 Why this plan exists

1. **What is missing**: Saberu has no single, discoverable configuration
   library. The managed-user policy is stored in a task-wide Semaphore
   Environment payload, while two older roles own separate user models.
   Software, host policy, and service settings are likewise split between
   examples, role defaults, inventory variables, and inline playbook blocks.
2. **Why it matters**: an operator cannot answer “where do I change this user
   configuration?” without knowing implementation history. The same desired
   state can have multiple owners, per-host composition is not reliable, and
   running `controller-bootstrap` can overwrite an operator's manual Environment
   edit with a checked-in example.
3. **Why now**: review of the software-catalog branch showed that extracting
   fail2ban alone would improve code reuse but would leave the actual
   configuration-ownership problem untouched. The user requested a reusable
   configuration library in which complete baselines and services can be
   selected predictably, while their lower-level components remain reusable and
   discoverable.

The target is not a new automation DSL. It is a thin product-level catalog of
plain YAML data, resolved into existing Ansible roles/playbooks:

```text
Git profile library (desired-state definitions)
  + Semaphore Inventory (node/group profile assignment)
  + Semaphore Key Store (secrets and credentials)
  + one-run task input (operation intent only)
  -> validated per-host resolved profile
  -> roles and ordered lifecycle playbooks
  -> task/audit evidence
```

## §2 Current state

### Confirmed repo facts

- The confirmed product domain already names `BaselineProfile` and
  `ServiceProfile`; both are still implicit rather than first-class catalog
  entries.
- `playbooks/vps/examples/onboard.minimal.yml` puts the managed user, groups,
  authorized public keys, and sudo policy under `vps_task.managed`.
- `playbooks/vps/onboard.yml` consumes that task-wide object and creates the
  managed user, keys, and sudoers file.
- `controller/semaphore/bootstrap.yml` reads
  `playbooks/vps/examples/onboard.minimal.yml` and unconditionally `PUT`s its
  JSON into `vps-onboard-env`. The operator guide separately tells the operator
  to edit that Environment in the UI. Both cannot be authoritative.
- The classic `common` role exposes `common__deploy_users`; the
  `infra_baseline` role exposes `infra_baseline_mgr_user`; the VPS lifecycle
  exposes `vps_task.managed`. These are three user-management owners with
  different behavior.
- `vps_task.schema.json` currently validates section names but intentionally
  leaves inner objects permissive. It does not validate a live Semaphore
  Environment or a resolved per-host profile.
- The current static `vps-fleet` Inventory is the durable connection-state
  carrier. The existing target-architecture design says policy/configuration
  should be Git-managed, but the active onboard implementation stores policy in
  the Semaphore Environment instead.
- The takeover chain is proven on Ubuntu 24.04 and Debian 13.5. Rocky 9.8 is
  still blocked after reaching the EPEL/fail2ban package path; that partial
  proof must not be described as full RHEL acceptance.
- The current branch contains a planning commit only. No profile or
  software-catalog implementation has landed.

### Verified external facts

- Ansible's built-in `host_group_vars` plugin loads `host_vars` and
  `group_vars`; official guidance describes separate host/group variable files
  as a robust way to express system policy.
- Ansible resolves values by documented precedence. Extra vars have high
  precedence, so silently mixing task payload, inventory values, and role
  defaults would make ownership harder to understand rather than easier.
- Semaphore Inventory can carry host/group variables and can be stored as
  INI, YAML, JSON, or TOML. The exact best carrier for one BaselineProfile name
  and zero/many ServiceProfile names in the repository's pinned Semaphore
  version still needs a local probe.
- Semaphore Key Store is the intended storage for remote-host credentials and
  other secrets.
- Current Semaphore documentation distinguishes reusable static Variable Groups
  from per-run Survey Variables. Availability and API shape must be probed
  against the pinned Semaphore `v2.18.2` before either becomes part of this
  implementation.

### Current ownership conflict

| Concern | Current owner(s) | Problem |
|---|---|---|
| Managed user | `vps_task.managed`, `common__deploy_users`, `infra_baseline_mgr_user` | Three schemas and three executors |
| Onboard defaults | checked-in example and live `vps-onboard-env` | Bootstrap overwrites UI edits |
| Per-node choice | task-wide Environment JSON | One payload applies to every host in a multi-host task |
| Connection state | Semaphore static Inventory | Correct direction, but mixed with manual lifecycle edits |
| Credentials | Semaphore Key Store plus historical file/vault paths | Active path is clearer than legacy paths, but docs still expose both |
| Software behavior | inline VPS tasks, `common`, and service roles | Duplicate owners and no common selection contract |

### Unknowns and close points

| Unknown | Classification | Close at | Method / fallback |
|---|---|---|---|
| Best BaselineProfile/ServiceProfile assignment carrier in pinned Semaphore | Needs runtime probe | WU-0 | Prefer one scalar baseline name plus a service-name list; probe static INI and static YAML/API behavior |
| Variable Groups and Survey Variables in `v2.18.2` | Needs runtime probe | WU-0 | Official docs plus read-only/local disposable API probe; keep existing Environment if unavailable |
| Whether `common` and `infra_baseline` still have live consumers that require their user APIs | Known gap requiring repo analysis | WU-1 child plan | `git grep`, inventory/playbook call graph, and Molecule consumers; retain compatibility adapters until consumers migrate |
| Exact live RHEL acceptance target | Needs operator decision/runtime availability | WU-2 live gate | Use a recoverable RHEL-family host with working package reachability; otherwise record the gate as blocked |

## §3 Scope

### In scope

- Establish one discoverable Git location for non-secret VPS profile
  definitions:

  ```text
  profiles/vps/
    README.md
    catalog.yml
    schemas/
    baseline/
    components/
      identity/
      host-policy/
      software/
    service/
  ```

- Establish an explicit two-level model:
  - a `Node` directly selects exactly one `BaselineProfile`;
  - a `Node` directly selects zero or more `ServiceProfile` entries;
  - a `BaselineProfile` internally composes exactly one identity component,
    host-policy components, and baseline software components;
  - lower-level identity/host-policy/software components are catalog building
    blocks and are not assigned directly to a Node in normal operation;
  - a `ServiceProfile` describes one workload/service recipe such as a Docker
    host and remains outside the takeover baseline.
- Make profile resolution per host. A multi-host task must be able to resolve a
  different BaselineProfile and ServiceProfile set for each inventory host.
- Make ownership explicit:
  - Git catalog owns non-secret desired-state definitions;
  - Semaphore Inventory owns node/group assignment and connection facts;
  - Key Store owns private credentials/secrets;
  - task Environment/Survey input owns only one-run operation parameters, not
    durable desired-state overrides;
  - roles/playbooks own execution behavior, not operator choices;
  - bootstrap owns resource existence/contract convergence, not operator data.
- Use the identity component inside the first BaselineProfile as the first
  migration pilot because it is the configuration the operator currently cannot
  locate.
- Preserve the takeover skeleton's fixed SSH/firewall cutover order. Profiles
  provide policy values; they do not make safety-critical ordering freely
  composable.
- Add schema/catalog validation, dependency/conflict validation, migration
  adapters, automated tests, documentation, and evidence.
- Treat the corrected software-unit work as a child execution plan, starting
  with fail2ban only after the parent direction and identity ownership model are
  approved.

### Out of scope

- No custom Saberu UI/API in this workstream.
- No storage of private keys, passwords, tokens, or secret values in profile
  files.
- No arbitrary Jinja/task snippets inside catalog data.
- No unbounded recursive inheritance or implicit Ansible `hash_behavior=merge`.
- No direct routine assignment of identity, host-policy, or software components
  to a Node; define or reuse a BaselineProfile instead.
- No promise that every unit can be combined with every other unit; explicit
  dependencies and conflicts are part of the contract.
- No decomposition of the ordered SSH cutover or firewall port choreography
  into freely ordered units.
- No offboard/reverse implementation (TASK-010).
- No live VPS mutation merely from approving this direction plan. Every live
  run needs the separate execution-time go/no-go gate.

### Target hierarchy and assignment contract

The product-level hierarchy is:

```text
Node
├── exactly one BaselineProfile
│   ├── exactly one identity component
│   ├── zero or more host-policy components
│   └── zero or more baseline software components
└── zero or more ServiceProfile entries
```

A Node's logical assignment is intentionally small and independent of its final
Inventory serialization:

```yaml
saberu_profile_assignment:
  baseline: personal-standard
  services: []
```

The referenced BaselineProfile performs the lower-level composition:

```yaml
kind: BaselineProfile
name: personal-standard
identity: managed-ansible
composition:
  host_policies:
    - secure-ssh
    - standard-firewall
    - standard-limits
  software:
    - fail2ban
    - unattended-upgrades
```

The resolver produces one namespaced object, for example
`saberu_resolved_profile`, and validates it before any mutating task runs.
Operator-facing node assignment never sets component or internal role variables
directly. A reusable combination is created as a new BaselineProfile rather
than copied into every Node.

Node-specific exceptions are allowed only as schema-allowlisted, visible
exceptions with an owner and reason. They are not the normal composition path.
One-run task parameters describe the requested operation; they do not silently
become durable desired-state overrides.

### Precedence and conflict rules

1. Component defaults.
2. The selected BaselineProfile or ServiceProfile's explicit configuration.
3. A schema-allowlisted, recorded Node exception.

The resolver implements and reports this order explicitly; it must not rely on
ambient Ansible variable precedence to merge desired state. During migration,
providing both a legacy field and its new profile equivalent is an error unless
the child plan defines a deterministic compatibility rule. One-run task input
does not enter this desired-state precedence chain. Each final setting has one
owning profile/component kind.

### Confirmed hierarchy decision

The user confirmed on 2026-07-17 that `BaselineProfile` is the higher-level
design. Identity remains an internal reusable component of a BaselineProfile,
not a separately assigned product entity. Promote it to a first-class
`IdentityProfile` only if later requirements need independently assigned
multiple identities, identity lifecycle/rotation, or team/RBAC ownership.

### Open decisions

| ID | Decision | Recommendation | Owner / deadline |
|---|---|---|---|
| D1 | Exact Inventory representation for per-host assignment | Prefer scalar BaselineProfile name plus zero/many ServiceProfile names; choose the simplest UI-editable carrier that preserves per-host behavior | Plan executor, WU-0 |
| D2 | Legacy role convergence order | Migrate active VPS identity first; retain adapters for `common`/`infra_baseline`, then remove only after consumer evidence | WU-1 child plan |
| D3 | One-run operation-input surface | Prefer typed Survey fields if supported; otherwise a minimal Environment object with runtime validation | WU-0 probe |

## §4 Implementation plan

Every behavioral work unit after WU-0 requires a child execution plan with its
own approval scope. Parent-direction approval does not authorize code or live
execution by itself.

### WU-0 — Prove the configuration carrier and freeze ownership

**Goal**: close the load-bearing storage/API unknowns without changing managed
hosts.

**Pre-condition**: this direction plan is explicitly approved; branch is moved
to or recreated as `feat/vps-profile-catalog` from the current
`feat/target-architecture` baseline; existing unrelated worktree changes are
preserved.

**Steps**:

1. Record the current configuration call graph, legacy consumers, hypotheses,
   probes, and results in
   `docs/workstreams/feat-vps-profile-catalog/investigation-profile-carrier.md`.
2. Use the repository venv's `ansible-inventory` against disposable fixtures to
   compare:
   - scalar BaselineProfile assignment in INI and YAML;
   - zero/many ServiceProfile names in INI and YAML;
   - per-group versus per-host assignment;
   - resolved values for two hosts with different baseline/service assignments.
3. Probe the pinned Semaphore API/UI capability for static YAML, Variable
   Groups, and Survey Variables without mutating production inventories.
4. Choose the canonical carrier and write an ownership matrix plus transition
   rules in the investigation conclusion. If the result changes the approved
   direction, stop and request a direction addendum; otherwise carry the
   accepted contract into the WU-1 execution plan and later stable profile
   documentation.
5. Draft the WU-1 identity migration execution plan, including exact consumers,
   compatibility duration, and rollback.

**Gate**: user approves the carrier/ownership decision and the WU-1 child plan.

**Deliverables**: `investigation-profile-carrier.md`, disposable fixtures/tests,
WU-1 execution plan, round changelog.

| Probe result | Next action |
|---|---|
| Baseline scalar + service list are stable and UI-editable | Use them directly in `vps-fleet` |
| Service list encoding is impractical in the pinned UI | Keep scalar BaselineProfile assignment first; defer ServiceProfile assignment carrier to WU-4 |
| Only task-wide Environment is viable | Stop; do not claim per-host assignment, and reassess the control-plane carrier before WU-1 |

### WU-1 — Build the catalog foundation and migrate identity

**Goal**: make user configuration easy to find and give it one active owner.

**Pre-condition**: WU-0 gate passed; WU-1 child plan approved; current active
VPS identity values are exported/redacted and recoverable.

**Steps**:

1. Add `profiles/vps/README.md`, `catalog.yml`, schemas, a default identity
   component, and one `BaselineProfile` that composes it.
2. Add a resolver/validator that:
   - resolves independently for each `inventory_hostname`;
   - allowlists catalog names;
   - checks kind, OS support, dependencies, conflicts, and unknown keys;
   - emits a redacted selection summary before mutation.
3. Adapt `playbooks/vps/onboard.yml` to consume the resolved identity object
   while preserving managed-channel validation and cutover order.
4. Add an explicit compatibility path for `vps_task.managed`; reject ambiguous
   mixed old/new input and emit a migration message.
5. Change `controller/semaphore/bootstrap.yml` so it cannot overwrite
   operator-owned profile assignment. Bootstrap may converge resource contract
   fields, but operator data must be create-only, preserved, or moved to its
   declared SSOT.
6. Inventory and document `common__deploy_users` and
   `infra_baseline_mgr_user` consumers. Do not delete either API until its
   callers have a migration path and tests.
7. Add schema/unit/Molecule coverage and register every new test target in
   Makefile, CI, testing governance, and TSVS.

**Gate**: automated tests pass; a disposable two-host fixture proves distinct
BaselineProfile assignment and resolved identity; no real VPS run until the
live go/no-go record is approved.

**Deliverables**: catalog foundation, identity pilot, compatibility adapter,
ownership-safe bootstrap behavior, tests, docs, round changelog.

### WU-2 — Pilot composable software with fail2ban

**Goal**: prove that profile data can select reusable execution behavior without
editing the takeover skeleton for each software unit.

**Pre-condition**: WU-1 complete; child plan
[`plan-software-profile-pilot-2026-07-17.md`](plan-software-profile-pilot-2026-07-17.md)
is approved; Debian- and RHEL-family test carriers are available.

**Steps**: execute the child plan. The pilot must consume the software selection
inside each host's resolved BaselineProfile, include a runtime catalog
allowlist, migrate both onboard and modify legacy fields, wire Molecule/CI, and
preserve tag behavior explicitly.

**Gate**: child-plan automated and live acceptance gates pass. A blocked RHEL
runtime gate remains blocked; it is not converted into a pass by Debian
evidence.

**Deliverables**: fail2ban unit, migration adapters, cross-family evidence,
round changelog.

### WU-3 — Migrate host policies and remaining small software units

**Goal**: move limits, unattended upgrades, swap, and network tuning into
single-owner profile/unit paths.

**Pre-condition**: WU-2 completed and its reflection shows the resolver/unit
boundary is sound.

**Steps**:

1. Write and approve a child plan that inventories every file/resource owner.
2. Migrate one concern per independently committable round.
3. Remove duplicate writes such as competing limits files only after proving
   the replacement and rollback.
4. Keep SSH/firewall execution ordering in the lifecycle skeleton while moving
   policy data to the profile library.

**Gate**: idempotency, cross-family coverage, and no duplicate managed files or
tasks for each migrated concern.

**Deliverables**: typed host-policy/software entries, migrated executors,
deprecation notes, evidence.

### WU-4 — Add ServiceProfile composition

**Goal**: connect the confirmed `ServiceProfile` product entity as a direct
zero-to-many Node assignment alongside, but not inside, the Node's single
BaselineProfile; do not treat large service roles as tiny software toggles.

**Pre-condition**: host baseline composition is stable; exact first service is
chosen by a separate child plan.

**Steps**:

1. Map existing Docker/web/database roles and playbooks to service ownership.
2. Select one service pilot with explicit ports, dependencies, variables,
   validation, and lifecycle boundaries.
3. Keep service execution separate from takeover when failure should not risk
   SSH access.
4. Record resulting `Service` state/evidence using the existing Semaphore task
   history until a later product state store is approved.

**Gate**: service child plan approved and its functional/idempotency evidence
passes.

**Deliverables**: first ServiceProfile, tests, operator workflow, evidence.

### WU-5 — Retire legacy owners and close documentation

**Goal**: leave one documented entry point and no silent compatibility paths.

**Pre-condition**: all known consumers have migrated and at least one release
window has retained deprecation evidence.

**Steps**:

1. Remove expired adapters and unused user/software APIs.
2. Update `README.md`, `ARCHITECTURE.md`, operator guides, feature maps,
   testing governance, TSVS index, CHANGELOG, and `TODO.md`.
3. Add a configuration-location table to the operator guide and link
   `profiles/vps/README.md` from the repository entry points.
4. Complete the plan and write closeout reflection.

**Gate**: repository search finds no undocumented active owner for each migrated
setting; full required verification passes.

**Deliverables**: single discoverable configuration path, cleaned legacy APIs,
final round changelog.

### Capability fit

- Use parallel read-only repository inspections for call graphs and ownership
  inventories.
- Use the existing venv, `ansible-inventory`, JSON Schema, Molecule, and
  Semaphore disposable API preflight rather than introducing a separate config
  compiler service.
- Do not use sub-agents unless the user explicitly requests delegation.
- Do not build a plugin/skill for product configuration: this is repository
  architecture and belongs in code/data/docs. The review taxonomy remains
  repository rules/scenarios; it is separate from the runtime profile model.

## §5 Verification

| WU | Verification method | Pass condition | Evidence artifact |
|---|---|---|---|
| 0 | `ansible-inventory` fixtures + pinned Semaphore API/UI probe | Two hosts resolve distinct baseline/service assignments; chosen carrier survives read/write without loss; capability claims match pinned version | `investigation-profile-carrier.md` + sanitized probe output in round changelog |
| 1 | schema tests, resolver unit tests, syntax/lint, identity Molecule scenario | unknown/mixed inputs fail before mutation; two BaselineProfiles resolve their intended identities; second converge is idempotent; bootstrap preserves operator data | test output + changelog |
| 2 | child plan: schema/runtime validation, Debian+RHEL Molecule, onboard/modify checks | fail2ban selected per host, unselected host unchanged, second run idempotent, legacy migration deterministic | child round changelog + TSVS |
| 3 | per-unit Molecule and file-owner assertions | one writer/resource owner per migrated concern; cross-family passes | round changelog |
| 4 | service scenario + managed audit | selected service reaches declared health state and repeat run is idempotent | task id/recap + TSVS |
| 5 | `git grep`, docs link checks, `make verify-full` where applicable | no active undocumented legacy owner; docs point to one configuration entry | closeout changelog |

Before any live mutation, record the exact target(s), inventory count,
operation/template, credential reference, expected users/SSH/firewall/packages,
console/reinstall fallback owner, evidence path, and explicit operator approval.
Existing u24/d13 managed hosts are not disposable onboarding fixtures merely
because they passed an earlier audit.

## §6 Risks and fallbacks

| Risk | Likelihood | Impact | Mitigation | Fallback |
|---|---|---|---|---|
| Generic catalog becomes a bespoke DSL | Medium | High | Plain YAML data only; roles/playbooks remain behavior owners; add fields only for demonstrated needs | Reduce Node assignment to BaselineProfile name only |
| Profile sources recreate precedence ambiguity | High | High | One BaselineProfile per Node, explicit resolver order, namespaced inputs, mixed-source rejection, redacted resolved summary | Disable Node exceptions and require a dedicated BaselineProfile |
| Bootstrap overwrites operator choices | High today | High | Separate resource-contract convergence from operator data; preservation test | Restore exported Environment/Inventory and revert bootstrap change |
| Identity migration locks out SSH | Medium | High | Preserve ordered cutover, compatibility adapter, fresh recoverable host, console fallback | Recover via console/reinstall; revert to exported legacy payload |
| Per-host selection is actually task-global | High in old draft | High | Resolve from host inventory/hostvars and test two different hosts in one run | Use one-host-per-run only as an explicit temporary limitation, not as full composition |
| RHEL test depends on unreachable EPEL mirror | Medium | Medium | Reachability preflight and alternate recoverable RHEL carrier/mirror policy | Mark RHEL gate blocked; do not claim cross-family completion |
| `common`/`infra_baseline` consumers break | Medium | Medium | Consumer inventory and compatibility period | Retain adapters/legacy vars until their child migration |
| Sensitive key material enters profiles/logs | Low | High | Public references only; Key Store for secrets; `no_log` and secret gate | Rotate credential and purge leaked evidence before continuing |

## §7 Post-completion checklist

- [ ] `profiles/vps/README.md` is the operator-facing configuration entry point.
- [ ] `README.md` and `ARCHITECTURE.md` link the profile library and ownership
      model.
- [ ] `docs/feat-target-architecture/operator-guide.md` no longer directs an
      operator to edit data that bootstrap later overwrites.
- [ ] `docs/reference/feature-map/vps-lifecycle.md` and its index describe
      profile resolution and active owners.
- [ ] Every new test target is in `Makefile`, CI where appropriate,
      `docs/governance/testing-governance.md`, and the TSVS index.
- [ ] `CHANGELOG.md [Unreleased]` records the operator-visible migration.
- [ ] `TODO.md` marks the direction and each child scope accurately.
- [ ] `investigation-profile-carrier.md` records the accepted carrier and links
      the stable contract that owns the current conclusion.
- [ ] Each implementation round has a
      `round<N>-YYYY-MM-DD.changelog.md` with sanitized evidence.
- [ ] Live-created or mutated Semaphore resources are recorded in the external
      resource ledger.
- [ ] Plan contradictions/rules gaps are reflected in a dated note or updated
      rule.
- [ ] This plan advances to `COMPLETED` with a completion date only after legacy
      owners and documentation are closed.

### Evidence map / sources checked 2026-07-17

| Claim / dependency | Source | Freshness / close point |
|---|---|---|
| Product has confirmed BaselineProfile and ServiceProfile language | `docs/reviews/feat-product-redesign/domain-model-2026-06-23.md` | Repo fact; re-check at WU-0 |
| Policy/config target is Git-managed group vars | `docs/reviews/feat-target-architecture/design-2026-05-26.md` §3.3 | Repo direction; reconcile at WU-0 |
| Inventory can carry variables and Ansible supports host/group vars | https://docs.ansible.com/projects/ansible/latest/inventory_guide/intro_inventory.html | Official current docs; pinned-runtime fixture at WU-0 |
| Variable precedence can override lower sources | https://docs.ansible.com/projects/ansible/latest/playbook_guide/playbooks_variables.html | Official current docs; design avoids implicit merge |
| `host_group_vars` is built in and loads host/group files | https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/host_group_vars_vars.html | Official current docs |
| Semaphore Inventory supports variables and multiple formats | https://semaphoreui.com/docs/user-guide/inventory | Official current docs; probe pinned `v2.18.2` at WU-0 |
| Key Store owns remote credentials/secrets | https://semaphoreui.com/docs/user-guide/key-store | Official current docs |
| Survey and Variable Group roles differ | https://semaphoreui.com/docs/user-guide/task-templates/survey-vars | Official current docs; feature/version probe at WU-0 |

## Next steps

- **Confirmed**: `BaselineProfile` is the higher-level design; identity,
  host-policy, and baseline software are its internal components.
- **Approved**: the revised full direction and the state-ownership split.
- **Next**: move work to the owner branch, execute WU-0, and present the carrier
  decision plus WU-1 child plan.
- **Blocked**: implementation and live VPS work until their scoped plans/gates
  are approved.
- **Deferrable**: ServiceProfile pilot and final legacy removal.
