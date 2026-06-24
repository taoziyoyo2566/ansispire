# Product Brief - AI Ops Control Platform

**Status**: Direction confirmed by user on 2026-06-23
**Date**: 2026-06-23
**Source inputs**: `saberu.drawio`, `ARCHITECTURE.md`, `TODO.md`,
`docs/reviews/feat-target-architecture/plan-semaphore-native-onboard-2026-06-10.md`

## Working Positioning

The redesigned product starts as an AI-assisted operations cockpit for an
individual operator managing multiple VPS nodes and self-hosted services. It
should be designed so it can later grow toward small-team operations, provider
resource management, security governance, and Terraform-overlapping resource
planning, but those later capabilities should not be required for the first
usable product.

The first practical promise is simple: make it easy to take many VPS nodes and
manage them through the same standard lifecycle: onboard, harden, install
software, configure services, validate, audit, and repeat.

## Confirmation Note

Confirmed product direction:

> Start with personal multi-VPS management. The point is not managing only one
> server, but using one standardized deployment, hardening, software install,
> service configuration, validation, and audit workflow across many VPS nodes.

This confirms the product brief direction only. Naming was later closed as
`Saberu`; diagram v2 and repository-wide rename remain separate decisions.

The product can use AI in several places. The following is an example workflow,
not a fixed final design:

1. describe or paste infrastructure intent,
2. let the system parse useful fields and suggest a concrete plan,
3. review parameters, risks, and expected changes,
4. execute approved automation for hardening, software install, and service
   configuration,
5. keep an auditable record of the result,
6. use logs and history for later troubleshooting, improvement, and remediation.

## Target Users

- First target: a personal infrastructure operator with several VPS nodes,
  several VPS providers, or several self-hosted services.
- Later target: small teams running self-hosted services across rented VPS
  nodes.
- Operators who know SSH and Docker, but do not want every recurring operation
  to become a bespoke shell session.
- Maintainers who want AI assistance for parsing, planning, and log explanation
  without giving AI direct unreviewed write access.

## Core Problem

Small infrastructure operators usually have the same operational needs as larger
platform teams, but without the staff or internal tooling:

- Turning a fresh VPS into a usable service host requires many repeated steps:
  SSH access, user setup, firewall/SSH hardening, package updates, Docker or web
  server install, service configuration, and validation.
- Those steps need to be standardized across many machines; otherwise each VPS
  becomes a special case with drift, unknown state, and inconsistent security
  posture.
- VPS credentials and provider details are scattered.
- Repeated tasks such as onboarding, audit, service deployment, and remediation
  are run manually or through ad hoc scripts.
- It is difficult to answer who changed what, on which server, when, and why.
- Logs are hard to interpret during failure recovery.
- Provider APIs, server state, service templates, and security findings are not
  connected into one decision workflow.

## Product Promise

Make multi-VPS setup and ongoing operations standardized, reviewable,
repeatable, and gradually more automated:

> The platform helps an operator turn VPS intent into a concrete execution plan,
> confirms the risky parts, runs approved automation across selected nodes, and
> keeps enough evidence to explain and repeat the result.

The important product distinction is not "AI runs servers". The distinction is
"AI helps the operator prepare, review, execute, and understand a controlled
operation".

## MVP

The MVP should prove a repeatable standard loop: take one or many VPS nodes from
raw access to secure, managed, service-ready state.

1. Add VPS nodes using bootstrap SSH details.
2. Group and label nodes so standard baselines can be applied consistently.
3. Apply a security baseline: managed user, SSH settings, firewall posture, and
   key policy.
4. Install common software such as Docker, Nginx/Caddy, database/client tools,
   or an agent.
5. Configure and validate services from templates.
6. Store node and service state as durable managed state.
7. Show task status, logs, and audit history per node and per operation.
8. Let AI assist with parsing input, choosing templates, and explaining output,
   while keeping execution behind explicit user confirmation.

### MVP Capabilities

| Capability | Product behavior | Likely foundation |
|---|---|---|
| VPS setup flow | turn bootstrap SSH access into managed nodes | `playbooks/vps/onboard.yml`, Semaphore templates |
| Fleet grouping | group nodes by provider, role, environment, OS, or service | Semaphore static inventory groups plus platform metadata |
| Standard baseline | apply SSH/user/firewall/package defaults consistently across selected nodes | `playbooks/vps/` hardening tasks |
| Software install | install Docker, web server, DB/client tools, or an agent | existing roles/playbooks plus service templates |
| Service configuration | configure services from repeatable templates | `playbooks/vps/`, future service templates |
| Node/VPS management | store SSH endpoint, OS family, tags, groups, lifecycle state | Semaphore static inventory plus platform metadata |
| Credential handling | keep SSH private key material out of git and chat | Semaphore Key Store and mounted runtime secrets |
| Template catalog | expose approved operations such as onboard, audit, install Docker, deploy Compose | `playbooks/vps/` and Semaphore templates |
| Task execution | launch, retry, schedule, and inspect runs | Semaphore Task API |
| Audit log | record who did what and when | Semaphore task history plus existing audit plane direction |
| AI assist | parse pasted VPS/provider/service details, suggest templates, explain logs | future Copilot surface |

## Phase 2

Phase 2 should expand after the standardized multi-VPS setup loop is useful. It
can improve the same product before becoming a provider-control platform:

- Better fleet views, filtering, drift detection, and batch operations.
- A richer service/template catalog.
- Safer rollback/offboard flows.
- Better scheduling, retries, notifications, and performance.
- Extension points for custom templates and provider integrations.

Provider automation can then expand from "manage existing servers" to "plan and
create resources".

Provider-oriented capabilities:

- Provider adapters for Netcup, OVH, AWS, Bandwagon, Spartan, and later others.
- Provider account management.
- Resource plans for create/change/delete before execution.
- User confirmation before provider-side mutation.
- Newly created resources flow into the same managed node lifecycle.

The key rule: provider adapters create or discover resources, but the managed
state still converges into the same Node/Inventory/Task/Audit model.

## Phase 3

Phase 3 expands from automation to governance, remediation, and deeper resource
planning:

- Vulnerability and exposure audit: CVEs, OS versions, package versions, open
  ports, and risky service configuration.
- Rules and approval engine: AI recommends, humans approve, automation remediates.
- Service relationship graph: nodes, services, dependencies, and risk topology.
- Remediation workflows that can be explained and replayed.
- Possible overlap with Terraform-like planning for selected resource types,
  if the product has already proven its operational workflow.

## Non-Goals

- Do not become a general cloud console in the MVP.
- Do not start by replacing Terraform for full infrastructure-as-code state
  management. Some overlap may be valid later.
- Do not let AI execute infrastructure changes without explicit confirmation.
- Do not build a custom runner before Semaphore/Ansible proves the execution
  loop is insufficient.
- Do not rename the whole repository until product name and migration plan are
  approved.

## Relationship To Current Repository

The current repository should be treated as the execution foundation, not as the
whole product definition.

Keep:

- Ansible playbooks and roles as the action implementation layer.
- Semaphore as the first task runner, template registry, and key store.
- Existing audit and EDA work as Phase 3-compatible foundations.
- `playbooks/vps/` as the first product workflow surface.
- Existing Docker/Nginx/service-deployment playbooks as candidates for the
  first service setup templates.

Reframe:

- `Ansispire` as the old project name unless retained by explicit decision.
- `cf-worker/` as one possible access layer, not the product boundary.
- `Semaphore` as backend infrastructure, not the product identity.

Defer:

- Full custom UI/API unless the MVP requires it.
- Custom runner.
- Provider-side resource creation.
- Repository-wide rename.

## Success Metrics

The first product milestone is successful when a user can:

- take fresh or known VPS nodes,
- group them for standardized management,
- harden and onboard them through the product workflow,
- install required software consistently,
- configure and validate at least one useful service,
- run audits through the controlled execution backend,
- inspect logs and status,
- see a durable record of the action,
- repeat the operation or audit across selected nodes with predictable results.

For the current repo, the nearest measurable technical proxy remains:

```text
Semaphore-native VPS onboard succeeds for the first verification node,
managed SSH path works,
security baseline is applied,
software/service setup can be triggered from an approved template,
VPS audit succeeds,
repeat audit reports 0 changed,
and the same pattern can be applied to additional nodes without changing the
workflow design.
```

## Naming Criteria

A suitable name should:

- work as a brand name first, not as a literal feature label;
- not bind the product only to Ansible, VPS, infrastructure, or any one
  implementation detail;
- have enough room for the product to evolve from personal multi-VPS operations
  into broader automation, provider, security, and planning capabilities;
- be easy to spell from speech;
- be short enough for CLI, service names, and docs;
- not imply unsafe autonomous operation;
- leave room for security/audit features;
- preferably fit the existing owned domain direction around `saberu.com`, if
  that name remains acceptable.

## Initial Name Shortlist

| Name | Fit | Caution |
|---|---|---|
| Saberu | Brand-like, short, already backed by the owned `saberu.com` domain, and flexible enough to avoid feature lock-in | Easy to misspell; meaning is not obvious to many users |
| Runweave | Strong fit for templates, tasks, and audit flows | Too function-descriptive for the revised naming preference |
| Opsmith | Practical and memorable for operational tooling | Too close to a role/function label |
| Stackwarden | Strong for security, governance, and managed services | Too descriptive and security-heavy for a broad product brand |
| Nodewright | Good fit for node lifecycle management | Too tied to nodes/VPS |
| Fleetbase | Clear for fleet management | Too generic and functional |

Updated naming decision: **Saberu** is the product name. It is short,
brandable, not tied to implementation details, and backed by the owned
`saberu.com` domain. Readability and naming-surface rules are recorded in
`name-decision-saberu-2026-06-23.md`.
