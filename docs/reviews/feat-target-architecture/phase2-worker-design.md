# Phase 2 — CF Worker Detailed Design

**Date**: 2026-06-06
**Branch**: `feat/target-architecture`
**Status**: Design-only — implementation begins after Phase 1 runtime probe closes `extra_vars` stub (§6).
**Refs**: [`plan-2026-05-25.md §4 Phase 2`](./plan-2026-05-25.md) · [`design-2026-05-26.md`](./design-2026-05-26.md) · [`IVG-SEMAPHORE-INVENTORY-API`](../../reference/investigations/IVG-SEMAPHORE-INVENTORY-API.md)

---

## 1. Language & Framework (Q4 Closed)

**Decision: JavaScript (Workers native)**

| Factor | JS | Python |
|---|---|---|
| Workers runtime stability | Stable, production-grade | Python Workers beta — not suitable for production |
| Router | itty-router (CF official template, ~450 B) | None equivalent |
| Community examples | Vast | Sparse |
| Existing repo code overlap | None (Worker is a new layer) | Low benefit from reuse |

No further Q4 discussion required. All Phase 2 implementation uses JS + itty-router.

---

## 2. Route Table

| Method | Path | Action |
|---|---|---|
| `GET` | `/vps` | List VPS — reads inventory blob, returns host list |
| `POST` | `/vps` | Onboard new VPS — add to inventory, create SSH key, trigger onboard task |
| `PUT` | `/vps/:alias` | Modify VPS — update host vars in inventory blob |
| `DELETE` | `/vps/:alias` | Remove VPS — remove host from inventory blob |
| `POST` | `/vps/:alias/audit` | Trigger audit task for a single host |
| `GET` | `/health` | Smoke-check (no Semaphore calls) |

All requests/responses are `application/json`. The Worker serves the wizard HTML at `GET /` (embedded in Worker bundle).

---

## 3. Request / Response Schemas

### `POST /vps` — Onboard
```json
{
  "alias":   "vps-01",
  "ip":      "203.0.113.10",
  "port":    22,
  "user":    "root",
  "auth": {
    "method":      "ssh",
    "private_key": "-----BEGIN OPENSSH PRIVATE KEY-----\n..."
  }
}
```
Response `201`:
```json
{ "alias": "vps-01", "keyId": 7, "taskId": 42 }
```

`auth.method` may also be `"password"`, in which case the auth object is:
```json
{ "method": "password", "password": "<bootstrap-password>" }
```
The Worker POSTs the appropriate Key Store object and discards credentials immediately after.

### `PUT /vps/:alias` — Modify
Only the fields provided are changed. Alias is matched in the inventory blob.
```json
{
  "ip":   "203.0.113.11",
  "port": 1156,
  "user": "ansible"
}
```
Response `200`: `{ "ok": true }`

### `DELETE /vps/:alias` — Remove
No body. Response `200`: `{ "ok": true }`

### `POST /vps/:alias/audit` — Trigger Audit
No body. Response `202`: `{ "taskId": 43 }`

### `GET /vps` — List
Response `200`:
```json
{
  "hosts": [
    {
      "alias": "vps-01",
      "ip":    "203.0.113.10",
      "port":  1156,
      "user":  "ansible"
    }
  ]
}
```

---

## 4. Semaphore API Client (`src/semaphore.js`)

Thin `fetch` wrappers around the four operations the Worker uses. All calls include `Authorization: Bearer ${TOKEN}` from env.

```
getInventory(projectId, inventoryId)
  → GET /api/project/{pid}/inventory/{iid}
  → Returns full inventory object; the `inventory` field holds the INI blob text.

updateInventory(projectId, inventoryId, name, blobText)
  → PUT /api/project/{pid}/inventory/{iid}
  → Body: { name, project_id, inventory: blobText, type: "static", ssh_key_id: 0 }
  → Whole-object replace (last-write-wins; acceptable for single-tenant).

createKey(projectId, name, type, payload)
  → POST /api/project/{pid}/keys
  → type "ssh":            { name, project_id, type: "ssh", ssh: { login, private_key, passphrase } }
  → type "login_password": { name, project_id, type: "login_password", login_password: { login, password } }
  → Returns { id: N }

triggerTask(projectId, templateId, overrides)
  → POST /api/project/{pid}/tasks
  → Body: { template_id, ... } — see §6 for the overrides stub.
  → Returns { id: N }
```

Error contract: any Semaphore non-2xx response → Worker returns `502 Bad Gateway` with `{ "error": "<upstream message>" }`.

---

## 5. Inventory Blob Algorithm (`src/inventory.js`)

The `static` inventory blob is INI text. The Worker owns a read-modify-write cycle:

```
1. GET inventory → extract .inventory (INI string)
2. Parse INI into: { groups: { [group]: { hosts: { [alias]: vars } }, vars: vars } }
3. Mutate:
     add:    append host to [vps_targets]; set vars (ansible_host, ansible_port, etc.)
     modify: update vars for the named host
     remove: delete host entry from [vps_targets]
4. Serialize back to INI string
5. PUT full inventory object (blobText = serialized INI)
```

Target blob structure (`vps_targets` group is the contract required by `playbooks/vps/*`):

```ini
[vps_targets]
vps-01 ansible_host=203.0.113.10 ansible_port=1156 ansible_user=ansible ansible_ssh_private_key_id=7

[vps_targets:vars]
ansible_python_interpreter=/usr/bin/python3
ansible_ssh_common_args=-o StrictHostKeyChecking=accept-new
```

**Key var `ansible_ssh_private_key_id`**: custom var carrying the Semaphore Key Store ID for the managed SSH key. The Task template maps this to `{{ lookup('env', ...) }}` or Semaphore-native key attachment — exact wiring is part of Phase 2 Session 1 implementation.

**Concurrency**: last-write-wins. Acceptable for single-tenant. If multi-tenant is triggered (Phase 5), add an ETag / `If-Match` round-trip.

---

## 6. Task Launch — ⚠️ STUB (Pending Phase 1 Runtime Probe)

The onboard task (`POST /vps`) requires passing `vps_task.bootstrap` (temporary connection info) to the Semaphore Task run before the managed user exists in inventory. This is the only operation that cannot be fully designed until Phase 1 live probe confirms which mechanism is available.

**Candidate paths (to be validated in Phase 1 probe):**

| Path | Description | Status |
|---|---|---|
| A | `POST /api/project/{id}/tasks` body includes an `extra_vars` field accepted by Semaphore | Unconfirmed — no public-contract evidence found in IVG |
| B | Semaphore template survey vars pre-configure `vps_task.bootstrap` fields | Requires exploring template survey API |
| C | Worker creates a one-shot template clone with `extra_vars` baked in, triggers it, then deletes the template | Possible but noisy |

**Design constraint until Phase 1 closes this stub:**
- `POST /vps` creates the Key Store entry and updates the inventory blob ✅
- `POST /vps` does **not** trigger the bootstrap task — that step returns `"taskId": null` with a `"note": "extra_vars mechanism pending Phase 1 probe"` ⚠️
- All other routes (modify, remove, audit) use `triggerTask(projectId, templateId)` with no overrides — this is confirmed working from `controller/audit/reactor.py` evidence.

---

## 7. SSH Key Flow

```
Browser (form input: PEM or password)
  │ HTTPS POST /vps body
  ▼
CF Worker memory (never logged, no persistence)
  │ POST /api/project/{id}/keys
  ▼
Semaphore Key Store (encrypted in SQLite volume)
  │ Returns key_id N
  ▼
Worker writes ansible_ssh_private_key_id=N into inventory blob
  │ PUT /api/project/{id}/inventory/{id}
  ▼
Inventory blob updated — key reference stored, not key material
```

Key material exists only in CF Worker memory for the duration of one request.

---

## 8. Worker Environment Variables

Configured via `wrangler.toml` (vars) and Cloudflare dashboard / `wrangler secret` (secrets):

| Name | Type | Value |
|---|---|---|
| `SEMAPHORE_URL` | var | `https://semaphore.saberu.com` (Cloudflare Tunnel public hostname; tunnel origin points to VPS-local `http://127.0.0.1:3300`) |
| `SEMAPHORE_PROJECT_ID` | var | Semaphore project integer ID |
| `SEMAPHORE_INVENTORY_ID` | var | ID of the `targets-managed` Semaphore inventory |
| `SEMAPHORE_AUDIT_TEMPLATE_ID` | var | ID of the audit task template |
| `SEMAPHORE_ONBOARD_TEMPLATE_ID` | var | ID of the onboard task template (task launch stub §6) |
| `SEMAPHORE_API_TOKEN` | **secret** | Semaphore Bearer token — never in source |

---

## 9. Error Handling

| Condition | HTTP Status | Body |
|---|---|---|
| Semaphore API non-2xx | 502 | `{ "error": "<Semaphore message>" }` |
| Missing required field | 400 | `{ "error": "field X is required" }` |
| Alias not found in inventory | 404 | `{ "error": "alias not found" }` |
| Alias already exists (POST /vps) | 409 | `{ "error": "alias already exists" }` |

---

## 10. Security

- **No CORS needed**: wizard HTML is served by the Worker itself (same-origin). External callers are not expected.
- **CF Tunnel**: Worker reaches Semaphore through the Tunnel public hostname in `SEMAPHORE_URL` (for now `https://semaphore.saberu.com`). The tunnel origin on the VPS points to local Semaphore (`http://127.0.0.1:3300`). No inbound port on the VPS.
- **Token scope**: use a Semaphore API token scoped to the single project (not admin).
- **SSH key**: never persisted in Worker KV, Worker cache, or logs. Request body → Key Store API → done.

---

## 11. Local Testing

| Scenario | Command |
|---|---|
| Unit: INI parser | `node --test src/inventory.test.js` |
| Integration: full routes | `wrangler dev` (local mode, real Semaphore instance) |
| CI gate | `wrangler deploy --dry-run` (validates bundle size, env bindings) |

No Semaphore mock is needed for unit tests; test `src/inventory.js` in isolation. Integration tests require a real (dev) Semaphore instance.

---

## 12. File Structure

```
cf-worker/
  src/
    index.js         ← itty-router setup + route handlers
    semaphore.js     ← Semaphore API client (fetch wrappers)
    inventory.js     ← INI blob parser + serializer
    wizard.html      ← Embedded wizard form (served at GET /)
  wrangler.toml
  package.json
```

`cf-worker/` lives at the repo root, parallel to `playbooks/`, `roles/`, `controller/`.

---

## 13. Open Questions Before Implementation

| # | Question | Blocks |
|---|---|---|
| 1 | What does `GET /inventory/{id}` actually return? Is `.inventory` the INI blob? | §4 getInventory, §5 algorithm |
| 2 | Is `PUT /inventory/{id}` a whole-object replace or a patch? | §5 concurrency note |
| 3 | Which task launch mechanism carries `vps_task.bootstrap`? | §6 stub (Phase 1 probe) |
| 4 | What is the `SEMAPHORE_ONBOARD_TEMPLATE_ID`? | §8 env vars |

Questions 1-3 are answered by the Phase 1 live probe. Question 4 is set during bootstrap.

---

*Phase 2 implementation starts in the first session after Phase 1 probe closes §6.*
