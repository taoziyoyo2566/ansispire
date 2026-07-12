# Ansispire CF Worker

Cloudflare Worker surface for the Semaphore-driven VPS lifecycle wizard.

> **Deferred surface (2026-07-12):** Semaphore UI is the active Saberu MVP
> entry point. Inventory CRUD probes remain useful, but `onboard-bare` still
> requires and emits the superseded `managed_private_key` payload while the
> current `onboard.yml` reuses the task transport key from Semaphore Key Store.
> Keep `SEMAPHORE_ONBOARD_TEMPLATE_ID` unset until Worker code, Wizard fields,
> tests, and post-success promotion are updated together.

> **Full deploy/config/validate procedure:** [`docs/operations/cf-worker-deployment.md`](../docs/operations/cf-worker-deployment.md).
> This README covers local checks, auth, and conventions only.

## Local Checks

```bash
npm test --prefix cf-worker
npm run deploy:dry-run --prefix cf-worker
```

## Deployed Smoke (verify the live build, not local code)

`integration:live` imports the local handler, so it cannot detect a deployment
that lags the working tree. After `wrangler deploy`, run the deployed smoke
against the real URL to confirm the live build is current (homepage exposes the
create-mode selector; `register-managed` rejects `root@22`). All checks are
read-only / non-writing:

```bash
WORKER_URL=https://ansispire-vps-worker.<acct>.workers.dev \
WORKER_AUTH_USER=... WORKER_AUTH_PASSWORD=... \
  npm run smoke:deployed --prefix cf-worker
```

## Authentication

All routes except `GET /health` require Worker-native Basic Auth. This is the
current temporary safety gate for the browser wizard and `/vps` REST routes
while the Worker points at a real Semaphore API.

The checked-in `wrangler.toml` intentionally uses a non-routable placeholder
`SEMAPHORE_URL` and the probe inventory id. Do not change the checked-in default
to the production `targets-managed` inventory. For live probe deploys, override
the non-secret vars explicitly:

```bash
npx wrangler deploy \
  --var SEMAPHORE_URL:https://semaphore.saberu.com \
  --var SEMAPHORE_INVENTORY_ID:3
```

Only point the Worker at an inventory whose Semaphore `type` is `static`.
`file` inventories are rejected with `412` before listing or mutation.

Configure the credentials as Cloudflare Worker secrets:

```bash
npx wrangler secret put WORKER_AUTH_USER
npx wrangler secret put WORKER_AUTH_PASSWORD
```

`SEMAPHORE_API_TOKEN` remains a separate secret:

```bash
npx wrangler secret put SEMAPHORE_API_TOKEN
```

After deploy, browser access to `/` prompts for the configured username and
password. API callers must send the same credentials:

```bash
curl -u "${WORKER_AUTH_USER}:${WORKER_AUTH_PASSWORD}" \
  https://ansispire-vps-worker.example.workers.dev/vps
```

For local `wrangler dev`, put development-only values in `cf-worker/.dev.vars`.
That file is ignored and must not be committed.

## Live Integration Probe

Use a dedicated Semaphore `static` probe inventory. Do not point this command at
the production `targets-managed` inventory until Phase 3 migration is planned.

Required environment:

```bash
export SEMAPHORE_URL="https://semaphore.example.com"
export SEMAPHORE_PROJECT_ID="1"
export SEMAPHORE_INVENTORY_ID="<probe-static-inventory-id>"
export SEMAPHORE_API_TOKEN="<token>"
export WORKER_AUTH_USER="<worker-basic-auth-user>"
export WORKER_AUTH_PASSWORD="<worker-basic-auth-password>"
```

Read-only smoke:

```bash
WORKER_LIVE_READ_ONLY=1 npm run integration:live --prefix cf-worker
```

Mutation probe:

```bash
WORKER_LIVE_CONFIRM=mutate-static-inventory npm run integration:live --prefix cf-worker
```

The mutation probe calls the Worker handler for `/health`, `GET /vps`,
`POST /vps`, `PUT /vps/:alias`, and `DELETE /vps/:alias`. It uses a temporary
host alias and restores the original Semaphore inventory blob in a `finally`
block. It intentionally leaves `SEMAPHORE_ONBOARD_TEMPLATE_ID` and
`SEMAPHORE_AUDIT_TEMPLATE_ID` empty so it does not trigger real lifecycle tasks.

## Wizard Query Prefill

The wizard can prefill non-sensitive fields from query parameters:

```text
/?mode=register-managed&alias=hkhy-d&ip=82.152.164.153&port=39222&user=ansible
```

Do not put passwords, SSH keys, or other secrets in URLs. The wizard ignores a
`secret` query parameter and requires the secret field to be entered manually.

## Wizard Modes

The wizard reads `GET /config` on load and shows the current runtime mode:

- `register-managed` is the default add mode. It records an already-managed
  SSH channel in Semaphore `static` inventory and never calls `onboard.yml`.
- `onboard-bare` exists in the deferred implementation but is currently
  incompatible with the playbook's Key Store key-reuse contract. Keep it
  disabled by leaving `SEMAPHORE_ONBOARD_TEMPLATE_ID` unset.
- `audit disabled` means `SEMAPHORE_AUDIT_TEMPLATE_ID` is not configured; Audit
  buttons are disabled instead of sending a request that must fail.

Only non-sensitive config state is returned by `/config`; the Semaphore API
token is never exposed to the browser.

## Browser Node Management

The browser wizard supports the first management workflow:

- Add VPS / Register managed node: creates an optional Semaphore key and writes
  the already-managed host into the configured `static` inventory using the
  managed port/user fields.
- Add VPS / Onboard bare node: deferred; the current UI/payload still carries
  an obsolete managed key path and must not trigger a live onboard.
- Edit VPS: updates inventory host fields (`ip`, `port`, `user`) through
  `PUT /vps/:alias`.
- Remove VPS: removes the host from the configured inventory through
  `DELETE /vps/:alias`.
- Audit VPS: enabled only when `SEMAPHORE_AUDIT_TEMPLATE_ID` is configured.

In register-managed mode, the main port/user fields describe the reachable
managed channel. The deferred onboard-bare implementation still sends a
`managed_private_key` path and `managed.ansible_key.private_key`, but the current
playbook no longer consumes either field: managed validation reuses the task's
transport key. Without an onboard template, the Wizard disables onboard-bare
mode and Add VPS remains a register-managed operation; that is the required
configuration until the deferred contract is redesigned.

## REST API Boundary

The `/vps` routes are the same backend used by the browser wizard and can be
called by other applications when they send Basic Auth credentials. This is a
temporary route-level safety gate, not a full external API authorization model:
there is still only one shared operator credential and no per-client scope.
Before advertising the Worker as a public multi-client API, replace or augment
this with Cloudflare Access/service tokens or Worker-native per-client authz.

## Server-Side Safeguards

Current development safeguards:

- All routes except `/health` require Basic Auth and fail closed when
  `WORKER_AUTH_USER` / `WORKER_AUTH_PASSWORD` are not configured.
- The configured Semaphore inventory must be `type: "static"`; `GET /vps`,
  create, update, delete, and audit fail closed with `412` for `file`
  inventories instead of parsing path strings as empty inventory blobs.
- `POST /vps` separates `register-managed` from `onboard-bare`; the default is
  register-managed and `root@22` is rejected in that mode.
- Invalid JSON bodies return `400`.
- Audit requires `SEMAPHORE_AUDIT_TEMPLATE_ID` and returns `412` when the
  template is not configured.
- Audit checks that the alias exists in the configured inventory before
  triggering a Semaphore task.
- If `POST /vps` creates a Semaphore key but the following inventory update
  fails, the Worker best-effort deletes the newly-created key.
- Per-host unknown inventory variables are preserved when updating known host
  fields.
- Upstream Semaphore errors return a generic Worker error with the upstream HTTP
  status, not the raw upstream response body.

Remaining development limits:

- Onboard-bare payload/key handling is stale against the current playbook and is
  intentionally disabled in the supported configuration.
- Inventory mutation is still whole-blob last-write-wins.
- Onboard-bare task-trigger failure after inventory update still needs lifecycle
  state handling and post-success promotion from onboarding to managed.
- Basic Auth is a temporary shared-credential gate; full API authz is still a
  production/API exposure step.
