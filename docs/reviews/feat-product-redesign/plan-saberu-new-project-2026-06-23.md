> **Status**: DRAFT
> **Created**: 2026-06-23
> **Branch**: feat/product-redesign
> **Classification**: [L2] Architecture
> **Deferred**: 2026-06-23 - future blueprint only; not approved for execution. Blocked until Semaphore-native onboard/audit proof, D3 AI scope decision, and a concrete custom thin-layer gap exist.
> **Updated**: 2026-06-23 - downgraded from current execution plan after D2 closed as Semaphore UI first.

# Blueprint - Future Saberu Thin Layer / New Project

This document is **not** the current implementation plan.

It is a future blueprint for the case where Saberu needs a custom thin layer or
separate project after the current Semaphore-native path proves its execution
loop and exposes concrete gaps.

## §1 Why this plan exists

1. **What is missing**: if Semaphore UI later proves insufficient, Saberu will
   need a clean custom surface that does not inherit all historical `ansispire`
   complexity.
2. **Why it matters**: a future custom layer should be designed around the
   confirmed Saberu domain model instead of copying the old repository wholesale.
3. **Why not now**: D2 is closed as **Semaphore UI first** and the
   Semaphore-native onboard/audit loop has not yet been proven. Building a new
   TypeScript product shell now would pre-empt the active execution baseline.

## §2 Current state

### Confirmed decisions

- Product name: **Saberu**.
- Short-term product direction: personal multi-VPS standardized management.
- Short-term implementation target:
  `new-vps-takeover-implementation-steps-2026-06-23.drawio`.
- Confirmed implementation-step sequence:
  1. VPS input draft
  2. SSH preflight
  3. Generate execution plan
  4. User confirmation
  5. Takeover and security baseline
  6. Managed-channel validation
  7. Software and service configuration
  8. Validation, state recording, and audit
- Confirmed domain language:
  `Node`, `NodeGroup`, `Credential`, `BaselineProfile`, `ServiceProfile`,
  `TaskPlan`, `TaskRun`, `AuditEvent`, and `Service`.
- MVP operator surface: **Semaphore UI first**.

### Active work that takes precedence

Current active implementation should remain in `ansispire` and follow
`docs/reviews/feat-target-architecture/plan-semaphore-native-onboard-2026-06-10.md`:

1. audit through Semaphore first,
2. onboard runtime-contract fixes,
3. real onboard/audit template provisioning,
4. real onboard execution,
5. managed-channel audit rerun with `0 changed`.

This blueprint should not be executed before that proof exists.

### Current repository role

Treat `ansispire` as:

- reference implementation,
- playbook/role asset source,
- technical evidence archive,
- source of lessons learned.

Do **not** treat it as:

- the new product repository,
- the final product architecture,
- the naming source of truth,
- the runtime state source for Saberu.

### Assumptions for future use only

- New project location will be a separate repository or separate workspace
  directory, not a wholesale rewrite of the current repository.
- A future Saberu implementation should not depend on the full current
  governance stack.
- Ansible playbooks can remain execution content.
- Semaphore remains the first backend and UI for MVP. A future custom layer
  should usually sit on top of Semaphore REST/API first, not bypass it by
  default.
- SQLite is enough for the first local product database.
- AI should be optional in MVP and should not block the first execution loop.

## §3 Scope

### In scope

- Preserve a future blueprint for which modules a custom Saberu layer might
  contain.
- Define which current `ansispire` assets to reference, migrate, defer, or leave
  behind.
- Define acceptance gates that must be satisfied before this blueprint can
  become an executable plan.
- Identify current assets that should be reused if a future custom layer is
  justified.

### Out of scope

- No new repository creation in this plan.
- No code scaffolding in this plan.
- No file migration in this plan.
- No changes to current `ansispire` runtime behavior.
- No repository-wide rename of `ansispire`.
- No approval to build a custom UI/API now.
- No decision to bypass Semaphore now.
- No production deployment plan yet.
- No provider API automation yet.
- No Terraform-like resource planning yet.
- No full AI Copilot implementation in MVP.

## §4 Future Architecture Sketch

This section is intentionally non-authoritative until the onboard/audit loop is
proven and the need for a custom layer is re-evaluated.

### Possible repository shape

```text
saberu/
  apps/
    web/                      # User interface
    api/                      # HTTP API / backend service
  packages/
    core/                     # Domain model and business rules
    ssh-preflight/            # SSH reachability and host capability checks
    executor-ansible/         # Ansible execution adapter
    audit-log/                # Audit event writer and query helpers
  playbooks/
    vps/                      # Curated VPS playbooks migrated from ansispire
  docs/
    product/                  # Product brief, flows, naming
    architecture/             # Runtime architecture and ADRs
    operations/               # Operator docs
```

### Core modules

| Module | Purpose | MVP responsibility |
|---|---|---|
| `nodes` | VPS records | Store host, port, user, OS, provider, tags, lifecycle state |
| `node-groups` | Multi-VPS grouping | Group by provider, environment, role, OS, service, custom tags |
| `credentials` | Credential references | Store references and metadata, not raw secrets in git |
| `ssh-preflight` | Read-only validation | Check SSH reachability, auth, OS family, sudo capability |
| `task-plans` | Pre-execution plan | Show target nodes, proposed changes, risks, and parameters |
| `approvals` | Confirmation gate | Ensure no write operation runs before user confirmation |
| `baseline-profiles` | Standard security baseline | Managed user, SSH settings, firewall posture, package update |
| `service-profiles` | Software/service setup | Docker, Nginx/Caddy, Agent, Compose app, later DB/client tools |
| `executor-ansible` | Execution backend | Run curated playbooks and stream/record output |
| `task-runs` | Execution record | Track status, logs, exit code, start/end time |
| `audit-events` | Evidence record | Record who/when/where/what/result |
| `ui` | Operator surface | Drive the 8-step flow without exposing backend complexity |

### Initial data model

Minimum entities:

| Entity | Required fields for first version |
|---|---|
| `Node` | id, alias, host, bootstrapPort, managedPort, bootstrapUser, managedUser, osFamily, provider, tags, lifecycleState |
| `NodeGroup` | id, name, selector/tags, description |
| `CredentialRef` | id, kind, label, storageBackend, externalRef, createdAt |
| `BaselineProfile` | id, name, managedUserPolicy, sshPolicy, firewallPolicy, packagePolicy |
| `ServiceProfile` | id, name, kind, templateRef, requiredPorts, variables |
| `TaskPlan` | id, targetNodeIds, profileIds, changes, risks, status, createdAt |
| `TaskRun` | id, taskPlanId, status, startedAt, endedAt, logsRef, exitCode |
| `AuditEvent` | id, actor, action, targetType, targetIds, result, taskRunId, createdAt |
| `Service` | id, nodeId, profileId, name, status, ports, lastCheckedAt |

### Future technology options

No stack is approved yet. These are options to compare only if a custom layer is
needed after the Semaphore-first proof.

| Layer | Recommended choice | Reason |
|---|---|---|
| Language | TypeScript | Shared types across API/UI; good ecosystem for SSH, web, AI, queues |
| UI | React + Vite or Next.js | Fast product iteration; supports cockpit-style UI |
| API | Node.js HTTP service | Simple local/server deployment; easy executor integration |
| Database | SQLite first | Low operational overhead; enough for personal/small-team MVP |
| Execution | Semaphore REST first; Ansible adapter only if needed | Keeps MVP aligned with D2 and the proven runtime |
| Secrets | External file/key reference first | Avoid storing private keys in DB/git; later support Vault/Key Store |
| AI | Optional adapter interface | Do not block MVP on AI provider/config |

Decision still open before scaffolding:

- monorepo package manager: npm, pnpm, or bun;
- web framework: Vite React vs Next.js;
- API framework: Fastify, Hono, Express, or framework-native API routes;
- DB layer: raw SQL, Kysely, Drizzle, or Prisma.

## §5 Asset Strategy From Current Repository

### Migrate or adapt early

| Current asset | New role | Handling |
|---|---|---|
| `playbooks/vps/onboard.yml` | takeover/security baseline execution | Extract and simplify into `playbooks/vps/` after review |
| `playbooks/vps/audit.yml` | post-takeover audit | Extract early |
| `playbooks/vps/docker_host.yml` | software setup candidate | Extract when Step 7 starts |
| `playbooks/vps/deploy_compose.yml` | service setup candidate | Extract when service profile support starts |
| `roles/` needed by selected playbooks | execution dependency | Copy only required roles, not all roles |
| `requirements.yml` / vendored collection list | Ansible dependency reference | Convert to a minimal Saberu Ansible dependency set |

### Reference but do not migrate initially

| Current asset | Reason |
|---|---|
| `controller/semaphore/bootstrap.yml` | Useful reference for the current Semaphore-first backend and any future thin layer over Semaphore REST/API |
| `controller/audit/` | Useful later for audit plane, too large for first MVP |
| `cf-worker/` | Useful UI/API reference, but not the first implementation base |
| `docs/reviews/feat-target-architecture/*` | Technical evidence and risk reference only |
| `docs/governance/*` | Mature governance reference, not copied into new MVP repo |

### Leave behind

| Current asset/surface | Reason |
|---|---|
| Old `Ansispire` branding | New product name is Saberu |
| Historical review/changelog directories | Evidence remains in current repo |
| EDA remediation stack | Later governance/remediation feature, not takeover MVP |
| Dependency/security governance work | Later product hardening, not first app slice |
| Current inventory files | Do not become Saberu runtime state |
| Multi-environment dev/stag/prod deployment model | Too heavy for initial product |

## §6 Activation Gates

This blueprint can only become an executable plan after all gates below are
true:

1. `plan-semaphore-native-onboard-2026-06-10.md` reaches its proof gate:
   audit succeeds, onboard succeeds, managed-channel audit succeeds, and repeat
   audit is `0 changed`.
2. D2 remains insufficient after evidence: Semaphore UI first has been tried,
   and the missing product gap is specific enough to justify a thin layer.
3. D3 AI scope is closed if the custom layer is meant to expose AI behavior.
4. A user-facing gap is named precisely, for example:
   - input parsing UX,
   - plan/confirm UX,
   - profile catalog,
   - service state view,
   - API workflow composition over Semaphore.
5. A new executable plan is written and approved.

## §7 Deferred Implementation Sketch

The phases below are preserved as a future sketch only. They are not approved
work.

#### Future Phase 0 - Review and approval

**Goal**: approve this plan before creating the new project.
**Pre-condition**: all activation gates in §6 are true.
**Steps**:

1. Review this plan.
2. Decide project location and repository strategy:
   - separate repository, or
   - sibling workspace directory such as `~/workspace/saberu`.
3. Decide initial technology defaults:
   - Vite React or Next.js,
   - API framework,
   - DB layer,
   - package manager.
4. Decide whether the custom layer composes Semaphore REST first, or whether a
   direct Ansible adapter is genuinely required.

**Gate**: user explicitly approves a new executable plan and closes technology
decisions.
**Deliverables**: approved plan; no code.

#### Future Phase 1 - New project skeleton

**Goal**: create the minimal Saberu repository/app skeleton.
**Pre-condition**: Phase 0 approved.
**Steps**:

1. Create new project outside current `ansispire` repo.
2. Add base README with Saberu naming rules.
3. Add directory layout for `apps/`, `packages/`, `playbooks/`, and `docs/`.
4. Add empty domain package with core entity types.
5. Add local SQLite setup and migrations placeholder.

**Gate**: project installs, typechecks, and starts a minimal local app/API.
**Deliverables**: new repo skeleton.

#### Future Phase 2 - Step 1: VPS input draft

**Goal**: store one or many VPS draft records before any SSH action.
**Pre-condition**: Phase 1 passes.
**Steps**:

1. Implement `NodeDraft` form/API.
2. Capture host, port, user, auth method reference, provider, OS hint, tags.
3. Validate required fields and basic shape.
4. Save draft records in SQLite.
5. Show draft list in UI.

**Gate**: user can create/edit/delete VPS drafts locally.
**Deliverables**: `nodes` module MVP.

#### Future Phase 3 - Step 2: SSH preflight

**Goal**: run read-only checks against draft VPS nodes.
**Pre-condition**: Phase 2 passes and test VPS credentials are available.
**Steps**:

1. Implement `ssh-preflight` package.
2. Check host reachability, SSH auth, OS family, Python availability, sudo
   capability, and basic facts.
3. Store preflight result per node.
4. Mark unsupported OS families clearly.
5. Do not modify remote machines in this phase.

**Gate**: preflight succeeds on a known reachable VPS and fails clearly on a bad
host/credential.
**Deliverables**: `ssh-preflight` module and result UI.

#### Future Phase 4 - Step 3: Generate execution plan

**Goal**: generate a reviewable `TaskPlan` from node drafts and selected
profiles.
**Pre-condition**: Phase 3 passes.
**Steps**:

1. Define default `BaselineProfile`.
2. Define initial `ServiceProfile` set as placeholders or no-op templates.
3. Generate plan showing targets, changes, ports, users, risks, and expected
   validations.
4. Support one node and multiple selected nodes.
5. Add plan status: draft, ready, approved, rejected.

**Gate**: UI shows what will change before any write operation.
**Deliverables**: `task-plans`, `baseline-profiles`, and `service-profiles`
initial modules.

#### Future Phase 5 - Step 4: User confirmation

**Goal**: enforce a hard approval gate before remote mutation.
**Pre-condition**: Phase 4 passes.
**Steps**:

1. Add explicit approve/reject action.
2. Require confirmation phrase or checklist for risky changes.
3. Record actor, timestamp, approved plan hash/snapshot.
4. Prevent executor from running unapproved plans.

**Gate**: attempts to execute unapproved plans are rejected.
**Deliverables**: `approvals` module and audit event for approval.

#### Future Phase 6 - Step 5: Takeover and security baseline

**Goal**: apply the first write operation to a test VPS safely.
**Pre-condition**: Phase 5 passes; disposable or recoverable VPS available.
**Steps**:

1. Prefer invoking the proven Semaphore template/API path.
2. Migrate/adapt minimum `onboard.yml` behavior only if bypassing Semaphore is
   deliberately approved.
3. Create managed user.
4. Install managed SSH key.
5. Apply SSH settings.
6. Apply firewall baseline while preserving access.
7. Capture execution output as a `TaskRun`.

**Gate**: takeover completes on a test VPS without losing access.
**Deliverables**: first `executor-ansible` write path.

#### Future Phase 7 - Step 6: Managed-channel validation

**Goal**: prove that the post-takeover connection path works.
**Pre-condition**: Phase 6 passes.
**Steps**:

1. Validate login through managed user, managed port, and managed key.
2. Keep bootstrap recovery metadata until validation passes.
3. Mark node lifecycle state as `managed` only after validation.
4. Record failure hints if validation fails.

**Gate**: node only becomes managed after the managed SSH path works.
**Deliverables**: lifecycle-state transition and validation record.

#### Future Phase 8 - Step 7: Software and service configuration

**Goal**: install useful software and run the first service template.
**Pre-condition**: Phase 7 passes.
**Steps**:

1. Add first software profile, likely Docker/Compose.
2. Add one simple service profile.
3. Execute install/configuration playbook through managed channel.
4. Store `Service` record per node.
5. Support repeated execution with idempotent result.

**Gate**: selected service is deployed and repeat run is predictable.
**Deliverables**: first `ServiceProfile` and `Service` implementation.

#### Future Phase 9 - Step 8: Validation, state, and audit

**Goal**: close the loop with health checks and durable evidence.
**Pre-condition**: Phase 8 passes.
**Steps**:

1. Run health check for SSH, service port, HTTP endpoint if applicable, and
   process/container state.
2. Store `TaskRun` logs and summary.
3. Store `AuditEvent` for takeover, service config, and validation.
4. Add UI view for node state, service state, run history, and audit trail.
5. Add exportable or copyable diagnostic summary.

**Gate**: user can inspect what happened, when, on which VPS, and the final
state.
**Deliverables**: first end-to-end Saberu MVP slice.

#### Future Phase 10 - Stabilization and next decisions

**Goal**: decide whether to expand UI/API, executor, provider integrations, or
AI assistance after the first MVP slice works.
**Pre-condition**: Phase 9 passes.
**Steps**:

1. Review UX friction.
2. Review Ansible adapter constraints.
3. Decide whether the proven Semaphore backend is sufficient, or whether any
   direct Ansible execution path is still justified.
4. Decide first AI assist surface: input parsing, plan explanation, or log
   explanation.
5. Decide first multi-node/batch operation enhancements.

**Gate**: user chooses the next feature direction.
**Deliverables**: next-phase plan.

## §8 Verification Strategy

| Phase | Verification method | Pass condition |
|---|---|---|
| 1 | install/start/typecheck | clean local startup |
| 2 | UI/API manual test | VPS draft CRUD works |
| 3 | preflight against good/bad SSH targets | good target passes; bad target fails clearly |
| 4 | generated plan review | plan shows targets, changes, risks, and profiles |
| 5 | execution attempt before approval | rejected |
| 6 | disposable VPS takeover via proven execution path | managed user/key/SSH/firewall applied without lockout |
| 7 | managed SSH validation | node becomes `managed` only after new path works |
| 8 | service setup rerun | service deploy succeeds and repeat run is predictable; idempotency evidence is captured |
| 9 | audit/history inspection | node, service, run, and audit records visible |
| 10 | review closeout | next direction chosen from evidence |

## §9 Risks and fallbacks

| Risk | Likelihood | Impact | Mitigation | Fallback |
|---|---|---|---|---|
| SSH lockout during takeover | med | high | Use disposable VPS first; validate managed path before closing bootstrap assumptions | Provider console/reinstall; keep bootstrap path until validation |
| New project overbuilds UI before backend proof | med | med | Build around the 8 implementation steps only | Start with API/local UI and defer polish |
| Ansible playbooks are too coupled to old repo | med | med | Migrate only minimal playbook/role set | Rewrite smaller playbooks for Saberu |
| Credential handling gets unsafe | low-med | high | Use references and external secret files first; never commit keys | Rotate test keys and block raw-secret storage |
| Domain model becomes too abstract | med | med | Implement entities only when a step needs them | Keep unused entities as docs until needed |
| Custom layer bypasses Semaphore without evidence | med | high | Treat Semaphore REST/API as the default future integration point | Require a new approved plan before any direct Ansible bypass |
| Blueprint is mistaken for active plan | high | high | Keep status DRAFT and activation gates explicit | Do not create new repo until a new approved executable plan exists |

## §10 Future Approval Questions

Before this blueprint can become executable, the user should approve or revise:

1. New project location: separate repo or sibling workspace directory.
2. Candidate stack only after the thin-layer gap is known.
3. Vite React vs Next.js.
4. API framework and DB layer.
5. Semaphore REST first vs direct Ansible vs executor abstraction.
6. Whether the first custom layer covers AI input parsing, plan/confirm UX,
   profile catalog, or service state.
7. Which current playbook/template path is reused first, after the
   Semaphore-native loop proves it works.

## §11 Deferred checklist

- [ ] Keep this blueprint deferred until activation gates pass.
- [ ] Execute `plan-semaphore-native-onboard-2026-06-10.md` first.
- [ ] Capture audit/onboard/managed-audit `0 changed` evidence.
- [ ] Reassess D3 AI scope.
- [ ] Decide whether a thin layer is still needed.
- [ ] If yes, create a new executable plan.
- [ ] Create the new project location only after that plan is approved.
- [ ] Add Saberu README and naming conventions.
- [ ] Scaffold selected tech stack.
- [ ] Implement Phase 2 first; do not jump directly to takeover writes.
- [ ] Keep current `ansispire` unchanged except as reference.
- [ ] Record implementation evidence in the new project, not in old historical
      review docs unless cross-reference is needed.
