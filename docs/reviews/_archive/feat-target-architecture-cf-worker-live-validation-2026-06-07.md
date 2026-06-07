# feat-target-architecture — CF Worker Live Validation Archive

**Date**: 2026-06-07
**Branch**: `feat/target-architecture`
**Purpose**: Preserve the validation sequence used to prove that the `cf-worker/` implementation works locally, under Cloudflare Workers remote preview, and after formal Cloudflare deployment.
**Related evidence**:

- [`round9-2026-06-07.changelog.md`](../feat-target-architecture/round9-2026-06-07.changelog.md)
- [`round8-2026-06-06.changelog.md`](../feat-target-architecture/round8-2026-06-06.changelog.md)
- [`phase2-implementation-plan-2026-06-06.md`](../feat-target-architecture/phase2-implementation-plan-2026-06-06.md)
- [`Semaphore runtime probe archive`](./feat-target-architecture-semaphore-runtime-probe-2026-06-06.md)

---

## Why This Validation Existed

Round 8 proved the Worker implementation locally, but it left three real runtime questions unanswered:

1. Whether the Worker could read and mutate a live Semaphore `static` inventory through the confirmed API contract.
2. Whether the same code worked in the Cloudflare Workers runtime, not only in Node-based tests.
3. Whether a formally deployed Worker could reach Semaphore through `https://semaphore.saberu.com` and Cloudflare Tunnel.

The validation therefore progressed from local Semaphore API checks, to Worker handler integration, to Cloudflare remote preview, and finally to a deployed `workers.dev` URL.

---

## Runtime Context

| Item | Value | Why it mattered |
|---|---|---|
| Semaphore image | `semaphoreui/semaphore:v2.18.2` | Same live controller version used by the earlier runtime probe. |
| Local Semaphore URL | `http://127.0.0.1:3300` | Used from the `saberu` host where DNS resolution for `semaphore.saberu.com` initially failed. |
| Tunnel/public Semaphore URL | `https://semaphore.saberu.com` | Used by Cloudflare remote preview and deployed Worker. |
| Project | `ansispire`, project id `1` | Scope for inventory API calls. |
| Production-facing inventory | `targets-managed`, inventory id `2` | Not mutated; still a `file` inventory at this stage. |
| Probe static inventory | `__probe_static_inventory__`, inventory id `3` | Safe target for Worker live CRUD validation. |
| Deployed Worker URL | `https://ansispire-vps-worker.taoziyoyo.workers.dev` | Formal Cloudflare deployment used for final smoke tests. |

---

## Safety Boundaries

- The validation used `SEMAPHORE_INVENTORY_ID=3`.
- The production-facing `targets-managed` inventory id `2` was not used for mutation.
- Real onboard/audit template ids were left empty during Worker handler and remote preview validation.
- The Bearer token came from `controller/semaphore/.secrets`; the token value was not recorded in this archive.
- Probe hosts used documentation IP ranges (`192.0.2.0/24`) or loopback values and were deleted after mutation checks.

---

## Variables Used

These were the effective variables used for local and Worker-side checks:

| Variable | Value | Purpose |
|---|---:|---|
| `SEMAPHORE_PROJECT_ID` | `1` | Semaphore project scope. |
| `SEMAPHORE_INVENTORY_ID` | `3` | Probe `static` inventory for read/write validation. |
| `SEMAPHORE_URL` | `http://127.0.0.1:3300` locally, `https://semaphore.saberu.com` for Cloudflare runtime | Selects local direct access vs tunnel/public access. |
| `SEMAPHORE_API_TOKEN` | Loaded from `controller/semaphore/.secrets` | Bearer token for Worker and curl API calls. |

Token extraction command:

```bash
export SEMAPHORE_API_TOKEN="$(grep '^SEMAPHORE_API_TOKEN=' controller/semaphore/.secrets | cut -d= -f2-)"
```

The trailing `-` in `cut -d= -f2-` is required because the token can contain `=` padding.

---

## Validation 1: Local Worker Bundle And Unit Checks

### Question

Does the Worker still pass local unit checks and Wrangler bundling after adding the live integration harness?

### Commands

```bash
npm test --prefix cf-worker
XDG_CONFIG_HOME=/tmp/codex-wrangler npm run deploy:dry-run --prefix cf-worker
```

### Result

- `npm test --prefix cf-worker` passed.
- Wrangler dry-run passed with an upload estimate around `32.70 KiB / gzip 7.70 KiB`.

### Meaning

The live integration harness and `fetch` runtime fix did not break local tests or Worker bundling.

---

## Validation 2: Confirm Probe Static Inventory Locally

### Question

Is inventory id `3` still the safe `static` probe inventory?

### Command

```bash
export SEMAPHORE_URL="http://127.0.0.1:3300"
export SEMAPHORE_PROJECT_ID="1"
export SEMAPHORE_INVENTORY_ID="3"
export SEMAPHORE_API_TOKEN="$(grep '^SEMAPHORE_API_TOKEN=' controller/semaphore/.secrets | cut -d= -f2-)"

curl -sS \
  -H "Authorization: Bearer ${SEMAPHORE_API_TOKEN}" \
  "${SEMAPHORE_URL}/api/project/1/inventory/3"
```

### Result

Semaphore returned:

```json
{
  "id": 3,
  "name": "__probe_static_inventory__",
  "project_id": 1,
  "inventory": "[vps_targets]\nprobe2 ansible_host=127.0.0.2 ansible_user=ansible ansible_port=1156\n",
  "ssh_key_id": 2,
  "become_key_id": null,
  "type": "static",
  "template_id": null,
  "repository_id": null
}
```

### Meaning

The probe inventory was still present, DB-backed, and compatible with the Worker `updateInventory()` body, which includes `ssh_key_id`.

---

## Validation 3: Live Integration Harness Against Local Semaphore

### Question

Can the Worker handler read, mutate, and restore the probe `static` inventory using the live Semaphore API?

### Commands

```bash
WORKER_LIVE_READ_ONLY=1 npm run integration:live --prefix cf-worker
WORKER_LIVE_CONFIRM=mutate-static-inventory npm run integration:live --prefix cf-worker
```

### Result

Read-only run:

```text
GET /vps ok (1 hosts)
Read-only live integration completed.
```

Mutation run:

```text
GET /vps ok (1 hosts)
POST /vps ok (worker-live-probe-1780788854696)
PUT /vps/worker-live-probe-1780788854696 ok
DELETE /vps/worker-live-probe-1780788854696 ok
Live integration completed. Original inventory will be restored.
Restored original Semaphore inventory blob.
```

### Meaning

The Worker route handlers and Semaphore client work against the live API. The harness verified read, create, update, delete, and restore behavior without depending on Cloudflare deployment.

---

## Validation 4: Public Semaphore DNS / Tunnel Reality Check

### Question

Can the `saberu` host and external hosts resolve `semaphore.saberu.com`?

### Observations

On another VPS:

```bash
dig A semaphore.saberu.com +short
getent hosts semaphore.saberu.com
```

returned Cloudflare IPs.

On `saberu`:

```bash
getent hosts semaphore.saberu.com
```

returned no output, and `curl https://semaphore.saberu.com/...` initially failed with:

```text
curl: (6) Could not resolve host: semaphore.saberu.com
```

Browser access to `https://semaphore.saberu.com/auth/login?return=%2F` worked.

### Meaning

The DNS problem was local to the `saberu` host resolver and did not block Cloudflare Worker runtime validation. Worker-side validation depends on Cloudflare's runtime resolving the public Tunnel hostname.

---

## Validation 5: Cloudflare Remote Preview

### Question

Does the Worker function in the Cloudflare Workers runtime before formal deploy?

### Command Shape

```bash
cd cf-worker

npx wrangler dev --remote \
  --var SEMAPHORE_URL:https://semaphore.saberu.com \
  --var SEMAPHORE_PROJECT_ID:1 \
  --var SEMAPHORE_INVENTORY_ID:3
```

### First Result

`GET /health` passed:

```json
{"ok":true}
```

`GET /vps` failed:

```json
{
  "status": 500,
  "error": "Illegal invocation: function called with incorrect `this` reference. See https://developers.cloudflare.com/workers/observability/errors/#illegal-invocation-errors for details."
}
```

### Fix

`cf-worker/src/semaphore.js` changed from storing the raw runtime function:

```js
this.fetch = fetchImpl;
```

to storing a bound function:

```js
this.fetchImpl = fetchImpl.bind(globalThis);
```

and then calling:

```js
await this.fetchImpl(`${this.url}${path}`, init);
```

### Second Result

After restarting remote preview:

```bash
curl -sS http://127.0.0.1:8787/health
curl -sS http://127.0.0.1:8787/vps
```

returned:

```json
{"ok":true}
```

and:

```json
{"hosts":[{"alias":"probe2","ip":"127.0.0.2","port":1156,"user":"ansible"}]}
```

### Meaning

This exposed and fixed a real Cloudflare Workers runtime issue that Node unit tests and local handler integration did not catch.

---

## Validation 6: Remote Preview CRUD Smoke

### Question

Can Cloudflare remote preview mutate the live Semaphore probe inventory through the Worker routes?

### Commands

```bash
curl -sS -X POST http://127.0.0.1:8787/vps \
  -H 'Content-Type: application/json' \
  -d '{"alias":"edge-probe","ip":"192.0.2.77","port":2222,"user":"ansible"}'

curl -sS http://127.0.0.1:8787/vps

curl -sS -X DELETE http://127.0.0.1:8787/vps/edge-probe

curl -sS http://127.0.0.1:8787/vps
```

### Result

The intermediate `GET /vps` included:

```json
{"alias":"edge-probe","ip":"192.0.2.77","port":2222,"user":"ansible"}
```

The delete returned:

```json
{"ok":true}
```

The final `GET /vps` returned only `probe2`.

### Meaning

Cloudflare remote preview could perform live read/write/delete operations through the public Tunnel URL and Semaphore API.

---

## Validation 7: Worker Secret And Formal Deploy

### Question

Can the Worker be formally deployed with the Semaphore Bearer token stored as a Cloudflare Worker secret?

### Commands

The secret was written with:

```bash
cd cf-worker

grep '^SEMAPHORE_API_TOKEN=' ../controller/semaphore/.secrets | cut -d= -f2- \
  | npx wrangler secret put SEMAPHORE_API_TOKEN
```

The Worker was deployed with probe inventory `3`:

```bash
npx wrangler deploy \
  --var "SEMAPHORE_URL:https://semaphore.saberu.com" \
  --var "SEMAPHORE_PROJECT_ID:1" \
  --var "SEMAPHORE_INVENTORY_ID:3"
```

### Result

Formal Worker URL:

```text
https://ansispire-vps-worker.taoziyoyo.workers.dev
```

### Meaning

The Worker secret path was validated without committing or recording the actual token.

---

## Validation 8: Formal Worker URL Read Smoke

### Question

Does the deployed Worker respond from `workers.dev` and read live Semaphore inventory?

### Commands

```bash
curl -sS https://ansispire-vps-worker.taoziyoyo.workers.dev/vps
curl -sS https://ansispire-vps-worker.taoziyoyo.workers.dev/health
```

### Result

`/vps` returned:

```json
{"hosts":[{"alias":"probe2","ip":"127.0.0.2","port":1156,"user":"ansible"}]}
```

`/health` returned:

```json
{"ok":true}
```

### Meaning

The formally deployed Cloudflare Worker can reach live Semaphore through the Tunnel and read the probe static inventory.

---

## Validation 9: Formal Worker URL CRUD Smoke

### Question

Can the formally deployed Worker mutate the live probe static inventory?

### Commands

```bash
curl -sS -X POST https://ansispire-vps-worker.taoziyoyo.workers.dev/vps \
  -H 'Content-Type: application/json' \
  -d '{"alias":"deploy-probe","ip":"192.0.2.88","port":2222,"user":"ansible"}'

curl -sS https://ansispire-vps-worker.taoziyoyo.workers.dev/vps

curl -sS -X DELETE https://ansispire-vps-worker.taoziyoyo.workers.dev/vps/deploy-probe

curl -sS https://ansispire-vps-worker.taoziyoyo.workers.dev/vps
```

### Result

The POST returned:

```json
{"error":"alias already exists"}
```

The follow-up GET showed the alias was already present:

```json
{
  "hosts": [
    {"alias":"probe2","ip":"127.0.0.2","port":1156,"user":"ansible"},
    {"alias":"deploy-probe","ip":"192.0.2.88","port":2222,"user":"ansible"}
  ]
}
```

The delete returned:

```json
{"ok":true}
```

The final GET returned:

```json
{"hosts":[{"alias":"probe2","ip":"127.0.0.2","port":1156,"user":"ansible"}]}
```

### Meaning

The deployed Worker was able to read current state, reject a duplicate alias, delete the probe host, and confirm the final inventory state. This closes the deployed CRUD smoke for the probe inventory.

---

## Final Confirmed Chain

The following end-to-end chain was confirmed:

```text
Cloudflare Worker
  -> https://semaphore.saberu.com
  -> Cloudflare Tunnel
  -> live Semaphore v2.18.2
  -> project 1
  -> static inventory 3
```

---

## Still Open

- `targets-managed` inventory id `2` is still production-facing and still not migrated to a Worker-managed `static` blob.
- `SEMAPHORE_ONBOARD_TEMPLATE_ID` and `SEMAPHORE_AUDIT_TEMPLATE_ID` still need real values.
- No real VPS onboard/audit task execution was validated in this round.
- Dedicated TSVS for the Worker-to-Semaphore lifecycle chain is still missing.
- Temporary Semaphore probe resources can be cleaned later when no longer useful:
  - inventory `3`
  - template `5`
