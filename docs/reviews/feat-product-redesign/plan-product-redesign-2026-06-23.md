> **Status**: DRAFT
> **Created**: 2026-06-23
> **Branch**: feat/product-redesign
> **Classification**: [L2] Architecture
> **Updated**: 2026-06-23 - user feedback shifted MVP wording toward incremental personal VPS deployment, hardening, software install, service configuration, and standardized multi-VPS management.
> **Updated**: 2026-06-23 - product brief direction confirmed by user; domain model, naming, diagram v2, and rename plan remain open.
> **Updated**: 2026-06-23 - `saberu.drawio` clarified as overview; added separate module-level diagram for standardized multi-VPS management.
> **Updated**: 2026-06-23 - added narrower new-VPS takeover flow diagram focused on bootstrap-to-managed setup.
> **Updated**: 2026-06-23 - added simplified implementation-step diagram for turning the takeover flow into buildable feature increments.
> **Updated**: 2026-06-23 - user confirmed the simplified implementation-step diagram as the short-term implementation target.
> **Updated**: 2026-06-23 - user confirmed the domain model for short-term implementation.
> **Updated**: 2026-06-23 - user selected `Saberu` as the product name; added readability and naming-surface rules.
> **Updated**: 2026-06-23 - D2 closed: MVP operator surface is Semaphore UI first; custom UI/API deferred until after onboard/audit proof.
> **Updated**: 2026-06-23 - round1 changelog written; `plan-saberu-new-project` downgraded to deferred blueprint.

# Plan - Product Redesign and Rename Direction

## §1 Why this plan exists

1. **What is missing**: the repository currently describes `ansispire` as an
   Ansible/Semaphore-centered multi-server management system, while
   `saberu.drawio` sketches a broader AI-assisted infrastructure and service
   automation platform. The product boundary, MVP, domain model, and name are
   not yet aligned.
2. **Why it matters**: without a clear product model, implementation work can
   keep oscillating between "Semaphore wiring", "VPS manager", "Worker API",
   "AI Copilot", and "security governance" without a stable user-facing shape.
3. **Why now**: the user explicitly wants to reconsider the current project
   design and choose a new name before continuing deeper implementation work.
   The first redesign pass needs to keep the roadmap evolutionary rather than
   pretending the full later platform is already designed.

## §2 Current state

### Confirmed facts

- `saberu.drawio` exists at the repository root and is currently untracked.
- The diagram title is "AI 辅助基础设施与服务自动化编排平台 - 架构全景图".
- The diagram frames a staged product:
  - MVP control plane: Web UI, backend API, node/VPS management, inventory
    probing, service templates, task management, execution logs, audit records.
  - Execution base: Semaphore, Ansible, playbook repository, optional future
    runner.
  - Phase 2: provider adapters and resource planning.
  - Phase 3: vulnerability audit, rules/approval engine, service relationship
    graph.
  - AI capability: natural-language input, provider/VPS info parsing, template
    recommendation, log explanation.
- Current repository truth in `ARCHITECTURE.md` still presents the project as
  `Ansispire`, a multi-server management control system built around Ansible,
  Semaphore, audit, and EDA remediation.
- Current target-architecture execution plan remains
  `docs/reviews/feat-target-architecture/plan-semaphore-native-onboard-2026-06-10.md`.

### Assumptions

- The redesign should define a product direction first and avoid immediate code,
  file, branch, package, or project-wide rename churn.
- The product can start with one-person operations, but the product problem is
  still multi-VPS management: one standard workflow should apply consistently
  across many nodes.
- The first runnable technical milestone should prove the path from raw or
  newly acquired VPS nodes to hardened, usable service hosts. A single node can
  be the atomic verification unit, but the MVP must preserve grouping,
  standardization, and repeatability for many nodes. Semaphore-native
  onboard/audit remains the nearest repository-level execution foundation, but
  the product MVP is broader than audit alone.

### Confirmed direction

- Product Brief direction is accepted as of 2026-06-23: start with personal
  multi-VPS standardized management, using repeatable deployment, hardening,
  software install, service configuration, validation, and audit workflows.
- This confirmation did not itself choose the final product name. The name was
  later closed as `Saberu`; repository-wide rename remains separate.
- `saberu.drawio` remains the product overview diagram. The current MVP module
  receives a separate deep-design diagram instead of replacing the overview.
- The standardized multi-VPS diagram is still a module overview. New VPS
  takeover receives a narrower flow diagram focused on bootstrap SSH, hardening,
  software/service setup, validation, and state recording.
- The implementation-step diagram is the starting point for feature execution:
  it breaks new-VPS takeover into small independently buildable and verifiable
  increments instead of drawing another architecture overview.
- Short-term implementation target confirmed on 2026-06-23:
  `new-vps-takeover-implementation-steps-2026-06-23.drawio`.
- Domain model confirmed on 2026-06-23 for short-term implementation:
  `Node`, `NodeGroup`, `Credential`, `BaselineProfile`, `ServiceProfile`,
  `TaskPlan`, `TaskRun`, `AuditEvent`, and `Service`.
- Product name confirmed on 2026-06-23: `Saberu`. Use `Saberu` for brand
  display and `saberu` for machine-readable identifiers. Keep the name stable
  across languages; localize descriptors and pronunciation helpers instead.
- MVP surface decision confirmed on 2026-06-23: **Semaphore UI first**. A
  custom Saberu UI/API remains deferred until the Semaphore-native onboard/audit
  loop is proven and the remaining gaps are concrete. See
  `decision-mvp-surface-semaphore-ui-first-2026-06-23.md`.

### Branch-management note

This document is authored while the working tree is on
`feat/target-architecture`, but the proposed owner branch is
`feat/product-redesign`. Before committing or implementing product-wide rename
work, create or switch to the dedicated owner branch so the redesign does not
become hidden inside the target-architecture transition branch.

## §3 Scope

### In scope

- Define the product brief for the redesigned project.
- Define the first-pass domain model and platform planes.
- Extract an MVP/Phase 2/Phase 3 boundary from `saberu.drawio`.
- Produce naming criteria and a shortlist.
- Decide what existing work remains part of the foundation.
- Identify follow-up documents and implementation gates.

### Out of scope

- No repository-wide rename yet.
- No package/module/path rename yet.
- No changes to `saberu.drawio` in this round; module-level diagramming is
  allowed as separate evidence.
- No changes to executable code or runtime configuration.
- No change to the existing target-architecture onboard/audit implementation
  plan.
- No trademark, domain, or package-name availability claim.

### Open decisions

| ID | Decision | Owner | Blocks |
|---|---|---|---|
| D1 | Final product name | **Closed 2026-06-23: Saberu** | Repository-wide rename plan deferred |
| D2 | MVP product surface | **Closed 2026-06-23: Semaphore UI first** | Custom UI/API deferred until after onboard/audit proof |
| D3 | AI Copilot scope in MVP: which concrete assistive moments are worth building first | User | AI subsystem plan |
| D4 | Whether `saberu.drawio` should become the canonical architecture diagram | User | Diagram rewrite and architecture sync |

## §4 Implementation plan

#### Phase 1 - Product definition

**Goal**: create a stable written product definition that can be reviewed
without touching runtime behavior.
**Pre-condition**: `saberu.drawio`, `ARCHITECTURE.md`, `TODO.md`, and current
target-architecture plan have been inspected.
**Steps**:

1. Add `product-brief-2026-06-23.md` under this topic.
2. State target users, problem, product promise, MVP, non-goals, and success
   metrics.
3. Make the initial MVP personal-operator focused and evolutionary: convenient
   standardized VPS deployment, security baseline, software install, service
   configuration, and multi-node management first; provider automation and
   Terraform-like overlap later.
4. Preserve the Semaphore-native onboard/audit loop as the near-term execution
   foundation unless the user explicitly rejects it.

**Gate**: user confirms the product brief direction or requests changes.
**Deliverables**: `product-brief-2026-06-23.md`.

#### Phase 2 - Domain model and architecture direction

**Goal**: define the product concepts and platform planes before implementation
renames.
**Pre-condition**: Phase 1 draft exists.
**Steps**:

1. Add `domain-model-2026-06-23.md` under this topic.
2. Define core entities such as Node, Credential, Inventory, Template, Task,
   AuditEvent, Service, ProviderAccount, ResourcePlan, Finding, and
   Remediation.
3. Map those entities onto current repository surfaces and likely future
   surfaces.
4. Mark which entities are MVP, Phase 2, or Phase 3.

**Gate**: user confirms the model is the intended product shape.
**Deliverables**: `domain-model-2026-06-23.md`.

#### Phase 2a - Module deep-design diagram

**Goal**: draw the confirmed MVP module without replacing the overview diagram.
**Pre-condition**: user confirms `saberu.drawio` is a high-level overview and
the standardized multi-VPS management flow should be drawn as a module.
**Steps**:

1. Add `multi-vps-standardized-management-2026-06-23.drawio`.
2. Model the flow across entry/intake, planning/standardization, execution,
   target fleet, and evidence/feedback.
3. Keep Phase 2 provider and Phase 3 security/governance as hooks, not MVP
   requirements.

**Gate**: user confirms the module diagram is the right deep-design view.
**Deliverables**: `multi-vps-standardized-management-2026-06-23.drawio`.

#### Phase 2b - New VPS takeover flow diagram

**Goal**: draw the concrete new-VPS takeover slice inside the multi-VPS module.
**Pre-condition**: user clarifies that the needed diagram should cover taking
over one or more new VPS nodes and applying related setup.
**Steps**:

1. Add `new-vps-takeover-flow-2026-06-23.drawio`.
2. Model the flow from new VPS list/bootstrap SSH input through preflight,
   confirmation, managed-user/key/SSH/firewall setup, software install, service
   configuration, health checks, state recording, audit, and AI explanation.
3. Keep multi-fleet grouping visible only as input metadata; avoid expanding
   into the full multi-VPS management overview again.

**Gate**: user confirms the takeover flow matches the desired module slice.
**Deliverables**: `new-vps-takeover-flow-2026-06-23.drawio`.

#### Phase 2c - New VPS takeover implementation-step diagram

**Goal**: reduce the takeover flow into feature-sized implementation steps.
**Pre-condition**: user wants to start implementation from the takeover module
and needs a simpler diagram at implementation-step granularity.
**Steps**:

1. Add `new-vps-takeover-implementation-steps-2026-06-23.drawio`.
2. Keep the diagram to the smallest build sequence:
   input draft, SSH preflight, plan generation, confirmation, takeover/security
   baseline, managed-channel validation, software/service setup, and
   validation/state/audit.
3. Avoid drawing the whole module or whole product again.

**Gate**: user confirms this is the right implementation starting diagram.
**Deliverables**: `new-vps-takeover-implementation-steps-2026-06-23.drawio`.

#### Phase 3 - Naming decision

**Goal**: select one project/product name before any rename migration.
**Pre-condition**: Phase 1 and Phase 2 are accepted or narrowed.
**Steps**:

1. Add a naming decision note or extend the product brief with the chosen name.
2. Check spelling risk, pronunciation, product fit, and likely namespace risk.
3. If external availability matters, run a separate manual trademark/domain/npm
   or package lookup; do not infer availability from memory.

**Gate**: user explicitly chooses the name.
**Deliverables**: `name-decision-saberu-2026-06-23.md` and follow-up rename
plan.

#### Phase 4 - Rename and repo alignment plan

**Goal**: plan the actual migration from `Ansispire` to the chosen name.
**Pre-condition**: D1 is closed.
**Steps**:

1. Create a separate rename plan under this topic.
2. Inventory all user-facing names in docs, Make targets, config, service names,
   directories, generated artifacts, and diagrams.
3. Separate cosmetic rename from behavior changes.
4. Define verification commands for docs, links, and runtime surfaces.

**Gate**: user approves the rename plan before execution.
**Deliverables**: future `plan-rename-YYYY-MM-DD.md`.

## §5 Verification

| Phase | Verification method | Pass condition | Evidence artifact |
|---|---|---|---|
| 1 | Review product brief against `saberu.drawio` labels | MVP/Phase 2/Phase 3 from the diagram are represented without inventing runtime facts | Product brief |
| 2 | Cross-check domain model against `ARCHITECTURE.md` and `TODO.md` | Existing Semaphore/Ansible/audit work maps to foundation roles, not discarded by accident | Domain model |
| 2a | Manual inspection of module diagram labels and flow | Diagram shows multi-VPS standardization module and does not replace `saberu.drawio` overview | Module drawio |
| 2b | Manual inspection plus XML parse of takeover diagram | Diagram shows bootstrap-to-managed new VPS takeover flow and parses as XML | Takeover drawio |
| 2c | Manual inspection plus XML parse of implementation-step diagram | Diagram shows small buildable feature steps, not a full overview | Implementation-step drawio |
| 3 | User confirmation | `Saberu` is selected and naming-surface/readability rules are recorded | Naming decision note |
| D2 | Official docs + local architecture review | Semaphore UI first is recorded and custom UI/API is deferred | MVP surface decision note |
| 4 | Future docs/link/runtime checks | No stale `Ansispire` user-facing references remain except intentional history | Rename changelog |

## §6 Risks and fallbacks

| Risk | Likelihood | Impact | Mitigation | Fallback |
|---|---|---|---|---|
| Redesign derails the current execution baseline | med | high | Keep Semaphore-native onboard/audit as the near-term technical milestone | Freeze redesign to docs until execution loop is proven |
| Repository rename starts before execution proof | med | med | Keep `Saberu` name decision separate from repo/service/package rename | Defer rename plan until onboard/audit proof is complete |
| Repository-wide rename mixes cosmetic and behavior changes | med | high | Require a separate rename plan with explicit verification | Split rename into docs-only, service-name, and code/package rounds |
| `saberu.drawio` is treated as final architecture too early | low-med | med | Treat it as design input until D4 closes | Produce a v2 diagram after product brief approval |

## §7 Post-completion checklist

- [x] User approves or revises `product-brief-2026-06-23.md`.
- [x] User approves or revises `domain-model-2026-06-23.md`.
- [ ] User approves or revises `multi-vps-standardized-management-2026-06-23.drawio`.
- [ ] User approves or revises `new-vps-takeover-flow-2026-06-23.drawio`.
- [x] User approves or revises `new-vps-takeover-implementation-steps-2026-06-23.drawio`.
- [x] D1 final product name is closed.
- [x] D2 MVP product surface is closed as Semaphore UI first.
- [ ] If D4 closes yes, create a v2 diagram update plan for `saberu.drawio`.
- [ ] Create a dedicated `feat/product-redesign` owner branch before committing
      or implementing rename work.
- [ ] Create follow-up rename plan after the name is selected.
- [ ] Update `TODO.md` only after the redesign direction becomes active work,
      not while it is still exploratory.
- [x] Write `round1-2026-06-23.changelog.md` after the first approved design
      round lands.
- [ ] Advance this plan to `COMPLETED` only after product brief, domain model,
      name decision, and follow-up rename plan are all closed.
