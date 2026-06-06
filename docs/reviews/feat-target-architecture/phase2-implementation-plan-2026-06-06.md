# Phase 2 Implementation Plan — CF Worker Wizard

**Date**: 2026-06-06
**Branch**: `feat/target-architecture`
**Owner topic**: Target Architecture — return to Semaphore Inventory + Key Store + Task API
**Status**: Draft-for-implementation; based on the approved target-architecture plan, Phase 2 design, and Round 7 runtime probe.

---

## Header

**Goal**: Implement the first usable CF Worker layer for VPS lifecycle management: route handlers, Semaphore API client, INI inventory parser/serializer, and a minimal same-origin wizard UI that can list/add/update/remove VPS records in a Semaphore `static` inventory and trigger lifecycle tasks with task-level `environment` payloads.

**Scope**:

- New Worker subproject under `cf-worker/`.
- Worker routes from `phase2-worker-design.md`: `GET /`, `GET /health`, `GET/POST /vps`, `PUT/DELETE /vps/:alias`, `POST /vps/:alias/audit`.
- Semaphore client wrappers for inventory GET/PUT, key creation, and task launch.
- INI blob parse/mutate/serialize for `[vps_targets]`.
- Unit tests for inventory parsing and mutation.
- Local config scaffolding (`wrangler.toml`, `package.json`) and ignore rules for Node/Wrangler artifacts.

**Out of scope**:

- Cloudflare account deployment, tunnel creation, or DNS changes.
- Storing real API tokens or SSH private keys in repo files.
- Migrating the live `targets-managed` inventory from `file` to `static`.
- Creating the real onboard / audit / modify / remove Semaphore templates.
- Reworking `playbooks/vps/*` behavior beyond reading the existing `vps_task` contract.
- Multi-tenant auth, external CORS, KV/Durable Objects, or concurrency locking beyond last-write-wins.

**Prerequisites**:

- Branch is `feat/target-architecture`, already synced from `dev` baseline PRs.
- Round 7 runtime probe closed the API blockers:
  - `static` inventory supports whole-blob CRUD.
  - `PUT /inventory/{id}` returns `204`.
  - task-level `environment` JSON string carries nested `vps_task` into Ansible.
- Local Node/npm are required for Worker tests and Wrangler checks.
- Real integration testing requires the user shell or another environment that can reach the live Semaphore instance and has the needed token/cookie; Codex shell cannot directly use Docker socket.

**Capability fit**:

- Use parallel read-only inspections for repo context and diff checks.
- Use official docs lookup for current Cloudflare/Wrangler behavior; Cloudflare currently recommends local project installation of Wrangler via `npm i -D wrangler@latest`.
- Use `itty-router` v5 `IttyRouter` for compact route matching, matching the approved Phase 2 design and current itty-router docs.
- Do not use sub-agents: this implementation is cohesive and benefits more from direct diff control than parallel independent agents.

**Expected effect**:

- `cf-worker/` becomes a self-contained Worker project that can run unit tests locally.
- Worker code can be configured with Semaphore URL/project/inventory/template IDs and token.
- The Worker implements the confirmed `environment: JSON.stringify({ vps_task })` task payload path.
- No live infrastructure changes occur from repository edits alone.

**Acceptance checks**:

- `npm test --prefix cf-worker` passes.
- If dependencies install successfully: `npm run typecheck --prefix cf-worker` or equivalent static check passes if configured.
- If Wrangler is installed: `npm run deploy:dry-run --prefix cf-worker` validates bundle/config without publishing.
- Repo checks: `git diff --check`, `make check-claude-links`.
- Manual integration path documented but not required for this implementation commit unless the user provides Worker secrets/runtime.

---

## Implementation Policy

Use a small, dependency-light JavaScript Worker. Keep Ansispire-specific logic explicit:

- `src/index.js`: route registration, request validation, response formatting.
- `src/semaphore.js`: fetch wrappers and upstream error normalization.
- `src/inventory.js`: pure INI parsing, serialization, and host mutations.
- `src/wizard.html`: minimal operator UI served same-origin by the Worker.

The Worker does not become a second control-plane database. Semaphore remains the source of truth:

- host records live in Semaphore `static` inventory blob;
- credentials live in Semaphore Key Store;
- task history lives in Semaphore Task API.

## Risks / Cautions

- **Secrets**: API token and private keys must never be logged or committed. Worker request handlers must avoid echoing private key/password values in errors.
- **Inventory concurrency**: last-write-wins is acceptable for single-tenant phase, but the code should isolate read/modify/write so future ETag or lock logic has a clear insertion point.
- **Key mapping**: `ansible_ssh_private_key_id` is project-specific metadata. It is useful for Worker bookkeeping, but actual Semaphore key attachment may need Phase 3 template wiring.
- **Onboard path**: `POST /vps` can trigger the onboard task using `environment`, but the real template ID must be provisioned later.
- **Wrangler/network**: dependency install and dry-run may fail in this sandbox due restricted network; record the gap instead of pretending validation passed.
- **Live cleanup**: temporary Semaphore probe inventory/template from Round 7 should be removed from the live instance after evidence capture.

## Specific Modifications

Expected files:

- `.gitignore`: add Node/Wrangler runtime artifacts.
- `cf-worker/package.json`
- `cf-worker/wrangler.toml`
- `cf-worker/src/index.js`
- `cf-worker/src/semaphore.js`
- `cf-worker/src/inventory.js`
- `cf-worker/src/wizard.html`
- `cf-worker/src/inventory.test.js`
- `docs/reference/feature-map/INDEX.md` and/or `docs/reference/feature-map/vps-lifecycle.md` if the new Worker surface needs index visibility.
- `docs/reviews/feat-target-architecture/round8-2026-06-06.changelog.md` after implementation.

## Verification

Local minimum:

1. `npm test --prefix cf-worker`
2. `git diff --check`
3. `make check-claude-links`

Conditional:

1. `npm install --prefix cf-worker` if `node_modules` is absent and network is available.
2. `npm run deploy:dry-run --prefix cf-worker` if Wrangler is installed.
3. Manual live integration against Semaphore only after user provides runtime env:
   - list VPS from a probe/static inventory;
   - add a non-sensitive test host;
   - confirm inventory blob mutation;
   - trigger a probe task with `environment` payload.

## Follow-up Handling

- If dependency install is blocked, implement code and tests but mark Node/Wrangler validation as blocked.
- If Worker implementation exposes a required Semaphore API not covered by Round 7, stop and add a focused runtime probe before committing that behavior as fact.
- If the first implementation passes local unit checks, Phase 3 remains deferred until Worker route behavior is reviewed and live-tested.

## Sources Checked

- Current repo truth: `ARCHITECTURE.md`, `TODO.md`, `docs/reference/feature-map/INDEX.md`, `docs/reference/feature-map/vps-lifecycle.md`.
- Active topic docs: `phase2-worker-design.md`, `round7-2026-06-06.changelog.md`, `IVG-SEMAPHORE-INVENTORY-API.md`.
- Cloudflare Workers docs: Wrangler local project install and Workers commands.
- itty-router docs: `IttyRouter` v5 routing model for serverless APIs.
