# CF Worker — Deployment & Validation Runbook

Copy-paste procedure to deploy and validate the `cf-worker/` VPS lifecycle Worker
against the live Semaphore control plane. Written for someone who has **not**
touched this Worker before.

> **Convention:** every command below is run from the `cf-worker/` directory
> (after step 1). No `--prefix` is used — `cd cf-worker` once and stay there.

This runbook only covers the Worker. Semaphore itself (controller + inventories
+ Key Store) is assumed already running — see
[`hub-deployment.md`](hub-deployment.md).

---

## 0. Prerequisites

### Tools (install once)

| Tool | Check | If missing |
|---|---|---|
| Node ≥ 18 | `node -v` | install Node LTS (the Worker uses global `fetch`) |
| npm | `npm -v` | comes with Node |
| `curl` | `curl --version` | install via your OS package manager |
| wrangler | installed locally by step 1 (`npx wrangler ...`) | step 1 runs `npm ci` |

### Access you must have

- A **Cloudflare account** with Workers enabled (free tier is fine).
- **Semaphore** reachable over HTTPS, plus a **`static` inventory** and an **API token** (how to get both is in step 2).

---

## 1. One-time setup

```bash
# clone the repo (skip if you already have it) and enter the Worker dir
git clone -b feat/target-architecture <repo-url> ansispire
cd ansispire/cf-worker

# install dependencies (wrangler etc.); needs the committed package-lock.json
npm ci          # if npm ci fails, use: npm install
```

Authenticate wrangler to Cloudflare — pick the one that matches your machine:

```bash
# A) Local machine WITH a browser:
npx wrangler login

# B) Headless server / CI (no browser): create an API token in the Cloudflare
#    dashboard (My Profile → API Tokens → Create → "Edit Cloudflare Workers"),
#    then export it (do NOT commit it):
export CLOUDFLARE_API_TOKEN=<your-cloudflare-api-token>
# If your login has more than one account, also set:
export CLOUDFLARE_ACCOUNT_ID=<your-account-id>
```

Verify auth works:

```bash
npx wrangler whoami     # should print your account, not an auth error
```

---

## 2. Gather the values you need

You need five values. Four describe Semaphore; two you invent for the Worker login.

| Value | What it is | How to get it | This project |
|---|---|---|---|
| `SEMAPHORE_URL` | public Semaphore API base | the URL you open Semaphore at | `https://semaphore.saberu.com` |
| `SEMAPHORE_PROJECT_ID` | project number | Semaphore UI URL, or `curl .../api/projects` | `1` |
| `SEMAPHORE_INVENTORY_ID` | a **`static`** inventory id | step 2.2 below | `3` |
| `SEMAPHORE_API_TOKEN` | Bearer token | step 2.1 below | — |
| `WORKER_AUTH_USER` / `WORKER_AUTH_PASSWORD` | login you choose for the Worker | invent any non-empty strings | — |

### 2.1 Get the Semaphore API token

Either from the repo secret on the controller host:

```bash
# run from the repo ROOT, not cf-worker/
grep '^SEMAPHORE_API_TOKEN=' ../controller/semaphore/.secrets | cut -d= -f2-
```

…or in the Semaphore UI: top-right user menu → **API Tokens** → create one.

Export it for the next commands (back in `cf-worker/`):

```bash
export SEMAPHORE_API_TOKEN=<token-from-above>
export SEMAPHORE_URL=https://semaphore.saberu.com
export SEMAPHORE_PROJECT_ID=1
```

### 2.2 Find (or create) a `static` inventory and note its id

The Worker **only** works against a `static` inventory. List them (read-only):

```bash
curl -s -H "Authorization: Bearer $SEMAPHORE_API_TOKEN" \
  "$SEMAPHORE_URL/api/project/$SEMAPHORE_PROJECT_ID/inventory" \
  | python3 -c 'import sys,json;[print(i.get("id"),i.get("type"),i.get("name")) for i in json.load(sys.stdin)]'
```

Pick an entry whose type is `static` and note its id (this project: `3`,
`__probe_static_inventory__`). **Do not** use a `file` inventory (this project:
ids `1` and `2`) — the Worker rejects those with `412`.

If no `static` inventory exists, create one in the Semaphore UI
(Project → Inventory → New → type **Static**) and use its id.

---

## 3. Configure the Worker secrets (one-time; persist across deploys)

Run in `cf-worker/`. Each command prompts for the value:

```bash
npx wrangler secret put SEMAPHORE_API_TOKEN     # paste the token from 2.1
npx wrangler secret put WORKER_AUTH_USER        # type a username you choose
npx wrangler secret put WORKER_AUTH_PASSWORD    # type a password you choose
```

> If you skip `WORKER_AUTH_USER` / `WORKER_AUTH_PASSWORD`, every route except
> `/health` returns `503 Worker authentication is not configured` (fail-closed by
> design). Secrets stay set across future deploys — re-enter only when rotating.

---

## 4. Deploy

```bash
# pre-flight (no publish): bundles and runs unit tests
npm test
npm run deploy:dry-run

# publish. The checked-in wrangler.toml SEMAPHORE_URL is a non-routable
# placeholder, so you MUST override it here. INVENTORY_ID already defaults to 3.
npx wrangler deploy \
  --var SEMAPHORE_URL:https://semaphore.saberu.com \
  --var SEMAPHORE_INVENTORY_ID:3
# once real Job Templates exist, also pass:
#   --var SEMAPHORE_ONBOARD_TEMPLATE_ID:<id> --var SEMAPHORE_AUDIT_TEMPLATE_ID:<id>
```

> **Important:** `--var` applies to *this deploy only*. A later `wrangler deploy`
> without these flags reverts `SEMAPHORE_URL` to the placeholder and the Worker
> can no longer reach Semaphore. Always pass the `--var` overrides (or set them
> as dashboard environment variables). Secrets (step 3) are not affected.

On success wrangler prints the URL, e.g.
`https://ansispire-vps-worker.<your-subdomain>.workers.dev`. Copy it.

---

## 5. Validate the live deployment

Put the three env vars **on the same command** (the script fails fast with
`Missing required env vars: ...` if you run `npm run smoke:deployed` alone):

```bash
# URL = what wrangler printed in step 4; user/password = what you set in step 3
WORKER_URL=https://ansispire-vps-worker.<your-subdomain>.workers.dev \
WORKER_AUTH_USER=<the user you set> \
WORKER_AUTH_PASSWORD=<the password you set> \
  npm run smoke:deployed
```

Expected: all checks pass — `/health` 200, unauthenticated `/vps` 401, homepage
shows the create-mode selector, and `register-managed` rejects `root@22`.

Manual spot-checks (all read-only; the last one is rejected before any write):

```bash
curl -s -o /dev/null -w '%{http_code}\n' "$WORKER_URL/health"      # 200
curl -s -o /dev/null -w '%{http_code}\n' "$WORKER_URL/vps"         # 401
curl -s -u "$WORKER_AUTH_USER:$WORKER_AUTH_PASSWORD" "$WORKER_URL/config"
curl -s -u "$WORKER_AUTH_USER:$WORKER_AUTH_PASSWORD" "$WORKER_URL/vps"
```

---

## 6. Troubleshooting (error → cause → fix)

| Symptom | Cause | Fix |
|---|---|---|
| `wrangler: command not found` | deps not installed | run `npm ci` in `cf-worker/`, use `npx wrangler` |
| `npm test --prefix cf-worker` → `ENOENT .../cf-worker/cf-worker` | you already `cd cf-worker` | drop `--prefix`; just `npm test` |
| wrangler `Authentication error` / asks to log in | not authenticated | step 1: `wrangler login` or `CLOUDFLARE_API_TOKEN` |
| `wrangler` can't pick an account | multiple accounts | `export CLOUDFLARE_ACCOUNT_ID=<id>` |
| every route returns `503 Worker authentication is not configured` | auth secrets unset | step 3 (`WORKER_AUTH_USER` / `WORKER_AUTH_PASSWORD`) |
| `/vps` returns `401` during validation | smoke/curl creds ≠ the secrets you set | re-export the same `WORKER_AUTH_*` values |
| any `/vps*` returns `412 ... must be type static` | pointed at a `file` inventory | use the `static` inventory id (this project `3`) |
| `502 Semaphore API request failed` `upstreamStatus:401/403` | bad/expired Semaphore token | redo `wrangler secret put SEMAPHORE_API_TOKEN` |
| `502` / DNS / connection errors to Semaphore | deployed without `--var SEMAPHORE_URL` (using placeholder) | redeploy with the `--var` overrides (step 4) |
| smoke fails `homepage missing "Register managed node"` | deployed build lags the working tree | redeploy current code (step 4) |

---

## 7. Rollback

```bash
npx wrangler deployments list          # find a previous version id
npx wrangler rollback [<version-id>]   # revert Worker code/vars to it
```

Secrets and Semaphore data are independent of Worker deploys.

---

## 8. Limitations & references

- **No real onboard/audit Job Templates yet** — until `SEMAPHORE_ONBOARD_TEMPLATE_ID` / `SEMAPHORE_AUDIT_TEMPLATE_ID` are set, onboard-bare returns `412` and audit is disabled.
- **Credential mapping gap** — the Worker stores `ansible_ssh_private_key_id` as a custom var that standard Ansible does not consume; Semaphore-side credential wiring is still a follow-up before real onboard/audit execution authenticates.
- **Production inventory not migrated** — `targets-managed` (id `2`) is still `file`; do not target it until Phase 3 migrates it to `static`.

References:
[`cf-worker/README.md`](../../cf-worker/README.md) ·
[feature-map `vps-lifecycle.md`](../reference/feature-map/vps-lifecycle.md) ·
[`INDEX.md §3.5`](../reference/feature-map/INDEX.md) ·
[manual onboarding runbook](vps-onboard-runbook.md)
(one-time validation evidence: archived in the pre-0.0.1 `ansispire` repository)
