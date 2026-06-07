# Onboard Execution Model — CF Worker Wizard (Decision)

**Date**: 2026-06-07
**Branch**: `feat/target-architecture`
**Level**: [L2] Architecture — execution-model decision for browser-driven VPS onboard/audit.
**Status**: **Decision recorded** (revised 2026-06-07 after external review — see correction notes in §2/§4/§5/§6/§7). Supersedes the earlier "choose A / B / C" framing — the three are collapsed into **one UI entry with two backend execution paths**. Original A/B/C analysis is preserved in the Appendix for provenance.

---

## 1. Context — what "onboard" actually is

A freshly-provisioned VPS starts in a **bare state**: reachable only as `root` + password/initial-key on port `22`. The desired **managed state** is a dedicated user (default `ansible`) + key on a non-22 port (default `39222`), with firewall / fail2ban / SSH lockdown applied. Moving bare → managed is **onboard**.

The execution-model question is *who performs that transition, and when*. This document records the chosen answer.

---

## 2. Decision — one UI entry, two backend execution paths

Do **not** ship A, B, and C as three separate user-facing choices. Ship **one** Wizard entry. But internally it must dispatch to **two distinct backend paths** — "register a managed node" is *not* a degenerate onboard run (see the correction note below):

- **Register managed node** (input is an already-prepared target) → write/upsert inventory, and optionally trigger **`audit.yml`**. **Does not call `onboard.yml`.**
- **Onboard bare node** (input is a `root`/bootstrap target) → write bootstrap inventory, trigger **`onboard.yml`**, then promote the inventory record to managed state after success.

For inventory hygiene on failure we accept Model A's tradeoff (a stale record may linger and is cleaned up by deletion) rather than paying Model B's playbook-refactor cost — see §5 for why B's only advantage does not survive scrutiny.

> **Correction (external review, 2026-06-07).** An earlier draft claimed "C is a special case of A: running `onboard.yml` against an already-managed node becomes validate+audit-only, every mutating step a no-op." That is **wrong and unsafe**, verified against code:
> - `onboard.yml:80-553` always runs full convergence (packages, group/user, authorized_key, sudoers, firewall, fail2ban, sshd lockdown, UFW). These are idempotent *only* if the submitted payload exactly matches current state — it is **not** "validate+audit only".
> - `onboard.yml:110-119` installs authorized keys via `lookup('ansible.builtin.file', key_item.public_key)`, reading files **from the Semaphore execution environment**. If those paths are absent, an already-managed registration **fails despite the node being reachable**.
> - An already-managed node has **no bootstrap `root@22` channel**, yet `onboard.yml` juggles `vps_bootstrap.port` throughout (open/close UFW, transitional drop-in). Forcing it through onboard is semantically wrong.
>
> Therefore the register path runs **`audit.yml` (or inventory write only)**, never `onboard.yml`.

---

## 3. Defaults, not fixed constants

`ansible` (managed user) and `39222` (managed port), and `root`/`22` (bootstrap), are **defaults the operator can override**, never hard-coded values:

- Form fields are pre-filled defaults: `wizard.js:137-140` (`value="22"` / `value="root"` / `value="39222"` / `value="ansible"`).
- Submission falls back to those defaults only when the field is empty: `wizard.js:315-317` (`data.managed_port || 39222`, `data.managed_user || "ansible"`, `managed_private_key || ""`).

Any design, doc, or template that treats `ansible`/`39222` as constants is wrong. The playbook already reads them from `vps_task` (`vps_ssh.managed_port`, `vps_managed.user`) with no literal port/user baked in.

---

## 4. Safety ordering — verify the new channel *before* locking the old one (already implemented)

The required safety property is: **never disable the bootstrap path until the managed path has been proven to work.** `onboard.yml` already enforces this. Real execution order:

1. Create managed user, install keys, configure sudo.
2. Configure the managed port **but keep the bootstrap port open** — `onboard.yml:284-292` (`Keep bootstrap SSH port open until final validation`).
3. **Verify the new channel**: wait for the managed port, then actually `ssh ansible@<managed_port>` and run `sudo -n true` — `onboard.yml:437-469`. If this fails, lockdown below never runs.
4. **Only after verification**, install the locked-down sshd drop-in (disable root login, disable password auth) — `onboard.yml:470-494`, validated by `sshd -t`.
5. **Only then** close the bootstrap port — `onboard.yml:520-531` (`Close bootstrap SSH port after final validation`).
6. Final managed-login re-check — `onboard.yml:533-553`.

The transitional drop-in listens on **both** the bootstrap and managed ports while not locked down (`templates/sshd_ansispire.conf.j2:2-5`); the final lockdown drop-in listens on the managed port only and adds `AllowGroups` (`:12-19`).

**Consequence (corrected):** the staging *minimizes* lockout risk but does **not** guarantee "never locked out". There is a residual window: **bootstrap port closure happens at `onboard.yml:520`, but the final managed-login validation runs *after* it at `:533`.** If the lockdown reload regresses managed access — e.g. the managed user is not in the `AllowGroups` set, or socket-activation/reload behaves differently than the pre-lockdown check at `:446` — the final check can fail with the bootstrap channel already closed.

> **Code-improvement candidate (out of scope here):** move the bootstrap-port closure (`:520`) to *after* the final managed-login validation (`:533`), so closure only happens once lockdown-applied managed login is proven. Tracked as a follow-up, not part of this decision.

---

## 5. Failure semantics — what actually happens, and what to build

### There is no automatic rollback

`onboard.yml` is a linear play with no `rescue`/`always` rollback (only a local swap-level `failed_when`, `onboard.yml:159-204`). Ansible's default applies: a failed task **stops that host and ends with an error**; everything done *before* the failure point **remains on the server**. "The target VPS is unchanged after a failed onboard" is **false** — it sits in a partially-converted state (e.g. the port may already have moved).

### Deletion is not reversion

| Action | What it does | Server-side changes still present? |
|---|---|---|
| **Delete (inventory removal)** | System "forgets" the host | **All present** (user, keys, moved port remain) |
| **Revert (restore to bare)** | Undo server changes | **Not implemented** (see §7 TODO) |

`playbooks/vps/remove.yml` confirms this: it *intentionally keeps users and keys by default* and only removes an sshd drop-in when explicitly requested. So deletion ≈ "forget + optionally drop one config file", **never** "restore the box".

### Why we don't need auto-rollback (and why B's advantage evaporates)

Because of §4's ordering, a failed onboard *usually* leaves a usable channel — but the mapping is **not binary**. There are three phases, not two:

- Fails **before** new-channel verification (`:446`) → lockdown never happened, bootstrap path intact; reconnect via bootstrap and retry.
- Fails **in the lockdown window** (`:470-531`: lockdown applied, reload/socket/UFW transitions, bootstrap port closed) → **ambiguous** — the managed channel may or may not be working, and bootstrap may already be gone. This is the dangerous middle the §4 residual window lives in.
- Fails **after** the final managed validation passes (`:533`) → managed path proven, reconnect with managed creds.

The correct recovery is **fix the cause and re-run the same onboard** — idempotency skips completed steps and resumes, instead of unwinding. Crucially, the *server-side half-converted state is identical under old Model A and old Model B*; B only kept the **inventory** clean. Since B's sole benefit is approximated by A + "delete the stale record", and B's cost is a full refactor of a 530-line self-validating playbook, **B is not worth it** (decision §2).

### What to build

The one genuinely missing piece is a **live-channel hint on failure**, and it must be driven by **explicit task-phase markers**, not inferred from a before/after split (the middle phase above is exactly why inference is unsafe). Onboard should emit a phase marker as it crosses each boundary (bootstrap-verified → lockdown-applied → bootstrap-closed → managed-verified) so that on failure the system can tell the operator *which channel to reconnect with*. This replaces, and is cheaper than, automatic rollback.

---

## 6. Current blocker — credential material delivery model

The real blocker is broader than a single variable name. There are **three distinct credential surfaces**, and the onboard path needs all three solved (the audit path needs only the first — see §7):

1. **Bootstrap/managed inventory connection.** The Worker writes the Key Store entry id into inventory as a **custom variable** `ansible_ssh_private_key_id=<key-id>` (`index.js:49-51` → `inventory.js upsertHost({..., keyId})`). **Standard Ansible SSH does not understand that variable** — it must be mapped to a real credential (Semaphore template/inventory SSH key, environment, or wrapper).
2. **Bootstrap auth in the payload, never consumed.** `buildOnboardTask` passes `bootstrap.auth.key_id` (`index.js:219-222`), but `onboard.yml` **never reads `vps_bootstrap.auth.key_id`** — it only uses `vps_bootstrap.port`. So the bootstrap connection credential is effectively undefined from the playbook's side.
3. **Managed validation needs a file path on the execution environment.** `onboard.yml:451,538` validate managed SSH via `ssh -i {{ vps_managed.ansible_key.private_key }}` — a **file path** (`input.managed_private_key`, e.g. `~/.ssh/ansispire_ed25519`), not a Key Store object. That key file must exist on the Semaphore execution environment.

So the blocker is the **credential material delivery model for bootstrap connection AND managed validation**, not merely "Key Store ID → SSH mapping".

---

## 7. Implementation order

**Split the audit credential path from the onboard credential path** — they are not the same blocker. Audit (the register-managed path) needs only credential surface §6.1, and even that can be satisfied Semaphore-natively (a real SSH key attached to the audit template or static inventory), **without** the Worker's per-host `key_id` mapping. So register+audit can ship *before* the full onboard credential model is solved.

1. **Ship the register-managed path + audit first (§2)** — fastest path to a working "register + audit from browser". Needs the `VPS Audit` Job Template for `playbooks/vps/audit.yml` + `SEMAPHORE_AUDIT_TEMPLATE_ID`, and a Semaphore-native SSH credential reachable for already-managed hosts. **Does not call `onboard.yml`.** Not blocked by §6.2/§6.3.
2. **Solve the onboard credential model (§6.1–6.3)** — bootstrap connection credential + managed-validation key file on the execution environment; prerequisite for the onboard path only.
3. **Enable the onboard path (§2)** — needs the `VPS Onboard` Job Template, the **phase-marker-driven failure live-channel hint (§5)**, and post-success inventory promotion (bootstrap→managed record rewrite). Consider the §4 closure-ordering fix here.
4. **Defaults discipline (§3)** — ensure promotion/writeback uses submitted values, not literals.

---

## 8. Three entry points — current impact and required convergence

The VPS lifecycle now has three entry-point shapes, but they are not three
independent systems:

| Entry point | Carrier | Intended role |
|---|---|---|
| Browser Wizard | `GET /` in `cf-worker/` | Human-friendly form for register/edit/remove/audit/onboard. |
| Worker REST API | `GET/POST /vps`, `PUT/DELETE /vps/:alias`, `POST /vps/:alias/audit` | Same backend as the Wizard, callable by other applications once auth/authz is solved. |
| Manual Ansible CLI | `docs/operations/vps-onboard-runbook.md` + `ansible-playbook playbooks/vps/*.yml` | Bootstrap/emergency path; not durable fleet state. |

**Convergence rule:** Semaphore `static` inventory is the only managed-state
truth. Manual runtime inventory files (`runtime/onboard/hosts.ini`,
`runtime/onboard/hosts.managed.ini`) are local execution input only. A manually
onboarded host must be registered back into Semaphore through the
register-managed path (`POST /vps` without an onboard task, or its future
explicit mode), otherwise the Wizard list, REST API, audit template, and future
Semaphore lifecycle tasks cannot see it.

### D1 — dual inventory truth source

Current state:

- Manual CLI uses local, gitignored runtime inventory files.
- Web/REST writes the Semaphore `static` inventory blob.

Impact: hosts created by one entry point are invisible to the other until they
are manually copied/register-managed into the shared Semaphore inventory. This
does not block emergency CLI usage, but it blocks a coherent control-plane
story.

Implemented fix: "register managed node" is now a first-class Worker/Wizard
mode (`mode: "register-managed"`). It writes the managed channel with
`lifecycle_state=managed`, never calls `onboard.yml`, and rejects accidental
`root@22` records. This is the required post-manual step after emergency/manual
onboard work.

### D2 — `vps_task` schema drift

Current state:

- `onboard.yml` is the executable contract and asserts
  `vps_task.managed.ansible_key.private_key` is present and non-empty.
- `playbooks/vps/examples/onboard.minimal.yml` and
  `playbooks/vps/examples/onboard.standard.yml` now include that field.
- The Worker previously generated `managed.ansible_key.private_key: ""` when the
  Wizard/API omitted `managed_private_key`; this produced a late playbook
  failure. The Worker now rejects onboard-triggering `POST /vps` requests that
  omit `managed_private_key`.

Remaining fix: define a single authoritative `vps_task` schema/fixture and make
all three entry points validate against it. Until that exists, treat
`onboard.yml` + the checked examples as the closest practical contract.

### D3 — credential model split

Current state:

- Manual inventory uses standard Ansible
  `ansible_ssh_private_key_file=<path>`.
- Worker inventory writes the custom variable
  `ansible_ssh_private_key_id=<Semaphore key id>`.
- `onboard.yml` does not consume that custom variable or
  `vps_bootstrap.auth.key_id`; managed validation still needs a key file path in
  the Semaphore execution environment.

Required fix: choose one Semaphore execution credential model before enabling
real onboard tasks. Do not copy Manual CLI inventory rows into Worker inventory,
or Worker inventory rows into local Ansible runs, without translating the
credential fields.

### D4 — external REST API auth boundary

Current state: Worker `/vps` routes are protected by temporary Worker-native
Basic Auth using `WORKER_AUTH_USER` / `WORKER_AUTH_PASSWORD`; `/health` remains
public for uptime checks. The Worker fails closed for protected routes when
those secrets are not configured.

Remaining fix before advertising entry point 2 as an external integration API:
replace or augment the shared Basic Auth gate with Cloudflare Access/service
tokens or Worker-native per-client authorization. Otherwise one shared operator
credential remains too coarse for multi-client inventory mutation and task
triggering.

### D5 — shared Worker/inventory risks

The following risks live below both the Browser Wizard and REST API. They should
be fixed once, in the shared Worker/inventory layer, before production
inventory migration:

- Unknown inventory variables are not preserved by the current parser/serializer.
  **Updated 2026-06-07:** per-host unknown vars are now preserved by Worker
  update/remove flows; non-target sections and comments are still not a
  production-grade lossless INI model.
- `POST /vps` previously conflated register-managed with onboard-bare, so
  inventory-only browser adds could persist `root@22` bootstrap records.
  **Updated 2026-06-07:** `register-managed` and `onboard-bare` are explicit
  modes; register-managed writes the managed channel and onboard-bare requires
  an onboard template.
- Key Store entries can become orphaned when inventory mutation succeeds/fails
  asymmetrically. **Updated 2026-06-07:** Worker now best-effort deletes a newly
  created key when the following inventory update fails. Task-trigger failure
  after inventory update still needs a lifecycle state model.
- Inventory has no lifecycle state field, so bootstrap/managed/failed states are
  implicit.
- `ssh_key_id` update handling still depends on brittle numeric coercion.
  **Updated 2026-06-07:** `updateInventory()` now preserves nullable/missing
  `ssh_key_id` instead of coercing missing values to `NaN`; production migration
  still needs a real template credential decision.

### D6 — server-side behavior fixes from review

External review identified S1-S7. Current disposition:

| Finding | Disposition |
|---|---|
| S1 multi-step non-atomic side effects | Partially fixed: key creation is compensated if inventory update fails. Still open for task-trigger failure after inventory update; requires lifecycle state/pending marker or stronger orchestration. |
| S2 whole-blob last-write-wins | Open/deferred. Acceptable only for current single-operator dev/probe use. Do not expose multi-client REST use until an optimistic concurrency or lock model exists. |
| S3 no route auth | Fixed for immediate exposure risk with Worker Basic Auth on all routes except `/health`; still open for production-grade per-client authz / Cloudflare Access policy. |
| S4 error mapping | Fixed for invalid JSON (`400`), audit template precondition (`412`), and upstream error sanitization (`502` with upstream status only). |
| S5 `ssh_key_id` coercion | Fixed as noted in D5. |
| S6 unknown per-host vars | Fixed as noted in D5. |
| S7 hard-coded onboard policy payload | Still open except for `managed_private_key` prevalidation. Needs an authoritative `vps_task` schema/defaulting model before real onboard template enablement. |
| Mode conflation (`root@22` register records) | Fixed for current Worker/Wizard add flow: default `register-managed` writes managed user/port and rejects `root@22`; `onboard-bare` is explicit and requires an onboard template. Promotion after onboard success remains open. |

### D7 — deployed-inventory guardrail fixes from review

External review identified N1-N4 after the deployed Worker had briefly been
configured through checked-in vars to inventory id `2` (`targets-managed`),
which is a Semaphore `file` inventory. Current disposition:

| Finding | Disposition |
|---|---|
| N1 deployed Worker pointed at production file inventory | Fixed in checked-in config: `wrangler.toml` no longer defaults to `https://semaphore.saberu.com` + inventory `2`; live deploys must explicitly override non-secret vars to a dedicated static probe inventory. |
| N2 no static inventory write guard | Fixed in code: `SemaphoreClient.updateInventory()` refuses non-`static` inventory objects, and Worker routes validate static inventory before mutation. |
| N3 file inventory showed as empty VPS list | Fixed in code: `GET /vps` returns `412` for non-static inventories instead of parsing path strings as empty blobs. |
| N4 deployment vars contradicted README safety rule | Fixed in docs/config: README now documents the checked-in placeholder config and explicit live-probe override command. |

---

## 9. Out of scope (TODO)

- **Reverse / offboard playbook** — true "restore the box to bare" (or "remove a specific managed user"). Tracked in `TODO.md` as a Target-Architecture backlog item; independent of this decision, deferred.

---

## Appendix — original three-model analysis (decision provenance)

The models below were the decision inputs; §2 collapses them. Kept verbatim-in-summary so future agents see *why* the single-entry decision was reached.

### Model A — Two-Stage Inventory
Inventory itself is the state machine: write bootstrap state, onboard through it, rewrite to managed state on success. Fits `hosts: vps_targets` (current playbook shape); needs post-success promotion; inventory holds bootstrap state mid-run and may linger as `root@22` on failure. **Chosen as the basis** — it matches the existing self-validating playbook.

### Model B — Localhost Orchestrator / Dynamic Target
Template runs on localhost; `add_host` creates the bootstrap target inside the play; inventory only ever holds final managed nodes. Cleanest inventory semantics, **but** requires refactoring/wrapping the 530-line `onboard.yml` (which today starts at `hosts: vps_targets` with no `add_host`). **Rejected** — its only advantage (clean inventory on failure) is approximated by A + deletion, while the server-side half-converted state it cannot prevent is identical to A (§5).

### Model C — Register Already-Managed Nodes First
Wizard registers only nodes already reachable on the managed channel; onboard stays manual/out-of-band. Smallest step, matches current Worker CRUD. **Kept as a distinct backend path** under the single UI (§2) — it runs `audit.yml`/inventory-write only and must **not** be routed through `onboard.yml` (which would force full convergence, exec-env key-file lookups, and bootstrap-port juggling on a node that has no bootstrap channel).
