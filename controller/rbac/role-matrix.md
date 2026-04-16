# RBAC Role Matrix — Round 8

Four-role permission model implemented on top of Semaphore's built-in
project-role primitive. Scope: **one project**; users can hold different
roles on different projects.

## Role definitions

| Role | Intended persona | Can read | Can run jobs | Can edit templates/inv | Can edit users/teams | Can delete project |
|------|------------------|----------|--------------|------------------------|----------------------|--------------------|
| **owner** | Project admin, also the primary incident responder | ✅ | ✅ | ✅ | ✅ | ✅ |
| **manager** | Senior operator; owns templates and inventory | ✅ | ✅ | ✅ | ❌ | ❌ |
| **task_runner** | Day-to-day operator; triggers runbooks, not authoring | ✅ | ✅ | ❌ | ❌ | ❌ |
| **guest** | Read-only (auditors, stakeholders, new hires) | ✅ | ❌ | ❌ | ❌ | ❌ |

## Mapping to Semaphore's native roles

Semaphore v2.10.x exposes four project-level roles in its API: `owner`,
`manager`, `task_runner`, `guest`. This round adopts them 1:1 rather than
inventing new names — the matrix above documents the semantics so role
choice at bootstrap time is deliberate rather than default.

## Principle of least privilege — enforced defaults

- **Default new user role on a project = `guest`.** Elevating is an
  explicit act, recorded in the audit stream (Round 8 scope).
- **Templates that mutate production** are placed in a project where the
  dev team holds only `task_runner`, so editing requires an owner action.
- **Secret material** (vault password, SSH keys) is bound to the
  keystore, not to a template — revoking a user's role revokes access
  to everything the template uses.

## Demo user ↔ role binding (Round 8 bootstrap)

> **API deviation from plan**: Semaphore OSS v2.10 does not expose a
> `/api/teams` endpoint (verified 2026-04-14, returns 404). "Team" in this
> round is therefore a **conceptual grouping** documented here; each
> demo user binds directly to the project with its intended role. The
> effect on the least-privilege demonstration is identical — this is a
> shape change, not a capability change. If Semaphore adds teams later,
> bootstrap can switch from per-user bindings to per-team bindings without
> altering the role matrix.

Bootstrap seeds one independent project `round8-rbac-demo` (so we do not
experiment with permissions on the existing `ansispire` project from
Round 7) and binds three demo users directly:

| Demo user | Conceptual team | Role on `round8-rbac-demo` | Rationale |
|-----------|-----------------|----------------------------|-----------|
| `demo_platform` | platform | `owner` | Owns the demo project end to end |
| `demo_dev` | dev | `task_runner` | Can run but not edit |
| `demo_audit` | — | `guest` | Read-only path (auditors, stakeholders) |

## Evidence this round must produce

- Triggering a job as a `guest`-role user returns HTTP 403.
- Creating a template as a `task_runner`-role user returns HTTP 403.
- A `manager`-role user can edit a template but cannot delete the project.
- An `owner`-role user can do everything on this project but has no
  access to the original `ansispire` project (scoping is per-project).

Audit events covering these attempts are captured by the Round 8 audit
sink (see `controller/audit/`) — the fail-closed paths (403) are the
primary "least privilege" evidence.

## Out of scope for Round 8

- Cross-project RBAC inheritance (org/folder-level roles) — not in Semaphore OSS.
- SSO / OIDC group → role mapping — Round 11.
- Temporal permissions (just-in-time access, expiring grants) — future.
- Attribute-based access control — future.
