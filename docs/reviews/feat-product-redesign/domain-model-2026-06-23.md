# Domain Model - Product Redesign

**Status**: Confirmed by user on 2026-06-23 for short-term implementation
**Date**: 2026-06-23

## Model Overview

## Confirmation Note

Confirmed for short-term implementation:

- `Node`
- `NodeGroup`
- `Credential`
- `BaselineProfile`
- `ServiceProfile`
- `TaskPlan`
- `TaskRun`
- `AuditEvent`
- `Service`

These names are the working domain language for the new-VPS takeover feature
slice. Future provider/resource planning can add concepts without replacing
this baseline.

The redesigned platform should be modeled around standardized multi-VPS
operations: operator intent, managed infrastructure state, controlled execution,
service configuration, and audit evidence.

The foundation is deliberately conservative:

```text
Operator intent
  -> ResourcePlan / TaskPlan
  -> user confirmation
  -> Template execution
  -> TaskRun
  -> AuditEvent and updated managed state
```

AI can assist at the first and last steps, but the write path remains gated by a
reviewable plan and explicit confirmation.

## Core Entities

| Entity | Meaning | MVP status | Current repository mapping |
|---|---|---|---|
| User | Human operator or future service account | MVP | Existing auth is mostly implicit; future UI/API concern |
| Node | VPS/server under management | MVP | Semaphore static inventory host, `playbooks/vps/` target |
| NodeGroup | Provider, role, environment, OS, service, or custom grouping | MVP | Semaphore inventory groups plus future metadata |
| BaselineProfile | Standard security/software posture applied to selected nodes | MVP | `playbooks/vps/` hardening/install tasks |
| Credential | SSH key, provider token, or service token | MVP | Semaphore Key Store, runtime secret mount |
| Inventory | Grouping and runtime variables for nodes | MVP | Semaphore static inventory, current `inventory/` files as legacy/source inputs |
| Template | Approved operation definition | MVP | Semaphore Job Template, Ansible playbook |
| TaskPlan | Concrete proposed execution with parameters and risk | MVP | Not yet first-class; currently implicit in template environment/payload |
| TaskRun | One execution instance and its status/logs | MVP | Semaphore task record |
| AuditEvent | Durable answer to who/what/when/where/result | MVP | Semaphore task history plus `controller/audit/` direction |
| Service | Software/service running on a node | MVP | Docker/Nginx/DB/Agent playbooks; not yet durable product entity |
| ServiceProfile | Repeatable recipe for installing/configuring a service | MVP | Existing playbooks and future template catalog |
| ProviderAccount | Cloud/VPS provider account credentials and metadata | Phase 2 | Not implemented |
| ProviderResource | Provider-side VM, DB, object store, network, etc. | Phase 2 | Not implemented |
| ResourcePlan | Proposed provider resource create/change/delete plan | Phase 2 | Not implemented |
| Finding | Security, drift, exposure, or health issue | Phase 3 | Partial direction in dependency/security governance and EDA |
| Remediation | Approved action to resolve a Finding | Phase 3 | Existing EDA remediation direction |
| RelationshipGraph | Nodes, services, dependencies, and risk topology | Phase 3 | Not implemented |

## Platform Planes

### Experience Plane

Purpose: where the operator expresses intent and reviews outcomes.

MVP forms:

- Semaphore UI if retained as the first operator UI.
- Minimal custom wizard/API only if it reduces high-friction manual input.
- AI Copilot for parse/explain assistance.

Responsibilities:

- collect VPS/provider details,
- show generated TaskPlan,
- display risk and parameter diff,
- require explicit confirmation,
- present run status and logs.

### Control Plane

Purpose: durable product state and orchestration entry points.

Responsibilities:

- nodes and node groups,
- credentials references,
- inventories,
- templates,
- task plans,
- task run metadata,
- audit events,
- policy decisions.

Current foundation:

- Semaphore Inventory,
- Semaphore Key Store,
- Semaphore Task API,
- repository-controlled bootstrap.

Longer-term options:

- custom API/database if Semaphore cannot express product-level state cleanly,
- Cloudflare Worker or another API access layer,
- Cloudflare Access/service tokens for production auth.

### Execution Plane

Purpose: run approved actions against infrastructure.

Responsibilities:

- execute playbooks,
- stream logs,
- return status,
- preserve enough evidence for audit and debugging.

Current foundation:

- Semaphore runner,
- Ansible,
- `roles/`,
- `playbooks/vps/`,
- vendored Ansible collections.

Future option:

- custom runner only if Semaphore becomes a constraint after MVP evidence.

### Infrastructure Plane

Purpose: the resources being managed.

MVP:

- existing or newly acquired VPS nodes reachable by SSH,
- groups of nodes managed through shared baseline profiles,
- secure baseline settings on those nodes,
- installed services such as Docker, Nginx, Caddy, DB, and agents.

Phase 2:

- provider-created resources,
- managed cloud services,
- provider API lifecycle.

### Governance Plane

Purpose: make actions reviewable and risk-aware.

MVP:

- audit trail for execution,
- explicit confirmation before mutation,
- no unreviewed AI writes.

Phase 3:

- vulnerability audit,
- rule/approval engine,
- service relationship graph,
- remediation history.

## MVP Workflow

### Prepare VPS Nodes And Configure Services

1. Operator provides bootstrap SSH details for one or many VPS nodes and chooses
   grouping labels.
2. System generates a TaskPlan covering security baseline, software install,
   service configuration, and validation for the selected nodes.
3. Operator confirms the plan.
4. Template execution hardens the nodes and installs/configures software.
5. Node, NodeGroup, BaselineProfile, and Service state are written as durable
   managed state.
6. Audit and validation results are recorded as TaskRun and AuditEvent per node
   and per operation.

### Register Managed Node

1. Operator provides host, port, user, OS hints, tags, and credential reference.
2. System validates the managed SSH path.
3. Node is written to durable inventory.
4. Audit task is run.
5. Result is recorded as TaskRun and AuditEvent.

### Onboard Bare VPS

1. Operator provides bootstrap SSH path and desired managed user/port/key policy.
2. System generates a TaskPlan and highlights security/service-impact risk.
3. Operator confirms.
4. Template executes `playbooks/vps/onboard.yml`.
5. On success, durable Node state is promoted to managed connection details.
6. Optional software/service templates run through the managed path.
7. Audit task is rerun through the managed path.

### Audit Node

1. Operator selects Node or group.
2. System launches approved audit Template.
3. Execution logs and result are captured.
4. AI may explain warnings/failures, but remediation is a separate confirmed
   plan.

## Current Fit Assessment

### Good fit

- `playbooks/vps/` already maps to Template/action content.
- Semaphore maps to TaskRun, Template, Key Store, and Inventory well enough for
  the MVP.
- The audit/EDA work can become the later Governance Plane rather than being
  discarded.
- `saberu.drawio` already separates MVP, provider expansion, security expansion,
  AI capability, and external systems.

### Gaps

- TaskPlan is not first-class yet; payloads are mostly template environments.
- NodeGroup and BaselineProfile are not first-class yet; grouping and baseline
  policy are currently implicit in inventory and playbook choices.
- ServiceProfile is not first-class yet; service setup is represented by
  playbooks and examples rather than a product catalog.
- AuditEvent is not yet unified across Semaphore task history and the audit
  plane.
- Node state is split between repository inventories, Semaphore inventories, and
  Worker parser assumptions.
- Credential references still need a clear container/runtime contract for real
  onboard/audit execution.
- Product UI is not decided: Semaphore UI, Worker wizard, or a new custom UI.

## Design Rules

1. **Intent before execution**: every mutating operation should have a visible
   plan before it runs.
2. **Human confirmation**: AI can suggest, parse, and explain; it should not
   silently execute infrastructure changes.
3. **One managed-state truth**: Nodes and groups must not be durable only in
   local runtime files.
4. **Execution backend is replaceable**: Semaphore is the first backend, not the
   product identity.
5. **Audit is product surface, not an afterthought**: the platform must preserve
   who/what/when/where/result for every action.
6. **Start personal, but multi-node**: optimize for one operator managing real
   VPS fleets first; add team/provider/security abstractions when the earlier
   loop is useful.
7. **Provider resources converge into Nodes/Services**: provider adapters should
   not create a parallel management model.

## Recommended Near-Term Order

1. Close the product brief direction.
2. Choose the project/product name.
3. Keep current Semaphore-native onboard/audit as the first technical proof,
   then extend the proof to grouped nodes, software install, and service
   configuration.
4. After the proof, decide whether the MVP operator surface is:
   - Semaphore UI plus documentation,
   - Worker wizard/API,
   - or a new custom product UI.
5. Only then perform repository-wide rename and architecture docs sync.
