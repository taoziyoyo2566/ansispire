# IaC vs UI Boundary — Semaphore Resources

**Scope**: Where each kind of Semaphore resource is created / owned / mutated in the Ansispire control plane.
**Audience**: Operators and future agents deciding "should this go in `bootstrap.yml` / `rules.json` / etc., or should the user click through the Semaphore UI?"
**Sibling docs**: `controller/semaphore/bootstrap.yml` (the canonical IaC entry); `docs/reference/feature-map/eda-core.md`.

---

## 1. Why this boundary matters

Semaphore is BOTH a UI-driven product and an API-driven product. Ansispire deliberately keeps **declarative + repeatable + git-tracked** resources in IaC (`bootstrap.yml`) and lets the UI own **discretionary + per-user + per-instance** state. Crossing the line in either direction produces specific failure modes:

- **UI-mutated resources that IaC owns** are silently overwritten on the next `make controller-bootstrap` run. Operators lose work.
- **IaC-mutated resources that the UI owns** create drift the UI doesn't see — its in-memory caches don't refresh, and the next user action collides with a state it didn't expect.

The table in §3 below is the authoritative map. When in doubt, prefer IaC unless §4 lists an explicit exception.

## 2. Resource taxonomy

Semaphore exposes a small fixed set of object types. Mapping them to Ansispire IaC:

| Semaphore object | Multiplicity | Lifecycle |
|---|---|---|
| `project` | 1 main (`ansispire`) + 1 RBAC demo | created once, mutated rarely |
| `user` | 3 demo + 1 admin + future humans | admin is bootstrapped; humans added via UI |
| `inventory` | tied to project, multi-environment expected | created once per env; edited by both |
| `repository` | per project (`/workspace` mount) | one canonical IaC; new ones via UI |
| `environment` | per project, empty default | created once; extra-vars added via UI |
| `key` | SSH keys / login passwords / none-key | placeholders IaC-created; real values UI-imported |
| `template` | per project, multiple per project | `Auto Remediation:*` templates IaC-managed; ad-hoc operator templates UI |
| `token` | M2M API token (admin) | minted by IaC, persisted to `.secrets` / state |
| `runner` (future) | gated by IVG-EXECUTION-PLANE-RUNNER trigger conditions | when introduced: IaC mints registration token |

## 3. Ownership Map

| Resource | Owner | Rationale | Failure mode if crossed |
|---|---|---|---|
| `project: ansispire` | **IaC** (`bootstrap.yml`) | Main control-plane project; must exist for any deploy | UI rename → bootstrap recreates "ansispire" alongside; double projects |
| `project: round8-rbac-demo` | **IaC** | Demo / smoke-test fixture; deterministic for RBAC tests | UI deletion → `controller-rbac-smoke` fails |
| `project: <user-created>` | **UI** | Operator's exploration / one-off work | If migrated to IaC later, must be cherry-picked into bootstrap |
| `user: admin` | **IaC** (`semaphore user add` in role) | Single source of truth for hub admin | UI password change → `.env` mismatch → bootstrap re-login fails |
| `user: <3 demo users>` | **IaC** (`bootstrap.yml`) | Deterministic RBAC test fixture | UI deletion → RBAC smoke fails next run |
| `user: <human operator>` | **UI** | Per-team additions; not deterministic | None — operators are explicitly out of IaC scope |
| `inventory: <main>` | **IaC** | Bind to repository `/workspace`; required by templates | UI rename → template binding breaks |
| `inventory: <project-specific>` | **UI** | Operator-defined targets | Drift OK; not consumed by IaC |
| `repository: /workspace` | **IaC** | Bind-mounted from project root; pinned to project layout | UI rename → templates can't resolve repo |
| `environment: empty default` | **IaC** | Required slot for templates that take no extra-vars | UI deletion → template create fails |
| `environment: <user-defined extra-vars>` | **UI** | Per-job tweaks | Drift OK |
| `key: none` | **IaC** (placeholder) | Required for the workspace repo (no auth needed) | UI deletion → bootstrap recreates |
| `key: ssh_lab_key` | **IaC** placeholder + **UI** real value | IaC creates an empty SSH key entry; operator pastes real private key via UI; `ACCESS_KEY_ENCRYPTION` keeps it encrypted at rest | If `ACCESS_KEY_ENCRYPTION` rotates without backup, value becomes undecryptable |
| `key: vault_prod_password` | **IaC** placeholder + **UI** real value | Same pattern as `ssh_lab_key` | Same |
| `template: Auto Remediation: Disk Cleanup` | **IaC** (`bootstrap.yml` `Register remediation templates`) | Referenced by `extensions/eda/rules.json` → reactor needs deterministic name | UI rename → reactor logs "could not resolve template", remediation silently breaks |
| `template: Auto Remediation: DB Failover` | **IaC** | Same as above; currently disabled in `rules.json` (`_disabled_reason` set) | Same |
| `template: <operator ad-hoc>` | **UI** | Not part of EDA contract | None |
| `token: M2M admin` | **IaC** (minted) | reactor consumes via `.eda_token`; bootstrap stores via `.secrets` | Manual UI revocation → reactor 401 |
| `runner` (future) | **IaC** (when introduced) | Registration token + manifest feature flag are IaC; per-runner tags are operator-side | See `IVG-EXECUTION-PLANE-RUNNER` §6.3 6-Gate path |

## 4. Explicit exceptions / hybrid resources

### 4.1 Key placeholders (IaC stub + UI value)

`ssh_lab_key` and `vault_prod_password` follow a deliberate hybrid pattern: **IaC creates the entry; operator pastes the real value via the UI**. Reason: real secrets must never enter git (see workspace W-R13 credentials-never-tracked); the IaC stub guarantees that the slot exists with a stable name so EDA rules and templates can reference it deterministically.

The `SEMAPHORE_ACCESS_KEY_ENCRYPTION` env (set from `state/.security_keys`) is the encryption-at-rest backstop. Rotating that key without re-encrypting stored AccessKeys leaves them undecryptable — DO NOT rotate manually. If a forced rotation is required, follow the upstream key-rotation procedure (out of scope for Ansispire today).

### 4.2 Users (admin via IaC; operators via UI)

The `SEMAPHORE_ADMIN_PASSWORD` env IS authoritative for the admin user. If an operator changes the admin password through the UI, the next `controller-bootstrap` run will fail to log in. Either: (a) update `vault.yml` first then redeploy; or (b) do not rotate via UI on managed hosts.

### 4.3 Sessions

Active sessions (cookies) are NOT a tracked resource — they're a UI runtime concern. The `SEMAPHORE_COOKIE_HASH` + `SEMAPHORE_COOKIE_ENCRYPTION` envs determine cookie validity across restarts. Rotating them invalidates all live sessions (acceptable trade-off for a security incident; not acceptable as a routine action).

## 5. Decision flowchart (operator-facing)

```
Is the resource declarative + repeatable + needed by IaC consumers?
  ├─ YES → put it in bootstrap.yml (idempotent List → Find → Create)
  │       Operator MUST NOT mutate via UI; do PR against bootstrap.yml
  └─ NO  → is it a credential value (private key, prod password)?
            ├─ YES → IaC creates the placeholder name only; operator
            │        pastes real value via UI; ACCESS_KEY_ENCRYPTION
            │        keeps it safe at rest
            └─ NO  → UI-only; operator owns lifecycle (no IaC mirror)
```

## 6. Cross-references

- IaC source of truth: [`controller/semaphore/bootstrap.yml`](../../controller/semaphore/bootstrap.yml)
- EDA rule contract: [`extensions/eda/rules.json`](../../extensions/eda/rules.json) + [`rules.schema.json`](../../extensions/eda/rules.schema.json)
- Security keys lifecycle: [`roles/ansispire_hub/tasks/main.yml`](../../roles/ansispire_hub/tasks/main.yml) `Hub | Generate Security Keys`
- Operator runbook for adding a real SSH key value: TBD (when operator guide ships)
- Audit trail for cross-compare findings that motivated this doc: [`IVG-SEMAPHORE-CROSS-COMPARE`](../reference/investigations/IVG-SEMAPHORE-CROSS-COMPARE.md) §5.B

---
*This doc is the authoritative boundary contract. PRs that touch `bootstrap.yml` should update this table if they introduce a new resource type.*
