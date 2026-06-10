# Phase A Plan — Enable Real Ansible Onboard via the Worker (R1 + R2)

**Date**: 2026-06-07
**Branch**: `feat/target-architecture`
**Level**: [L2] Architecture
**Status**: **PLAN — awaiting approval + an R1 decision.** No implementation until approved (`CLAUDE.md §1`).
**Backlog source**: [`backlog-2026-06-07.md`](backlog-2026-06-07.md) items R1 + R2 (the P1 critical path).

---

## 0. Best-practice pre-check (W-R18)

Semaphore's native execution model (confirmed from `controller/semaphore/bootstrap.yml` + IVG):

- A **Job Template** binds `project_id` + `inventory_id` + `repository_id` + `playbook` + app `ansible`. Semaphore pulls the repo to `/workspace` and runs the playbook from there.
- Semaphore authenticates to target hosts using the **inventory's `ssh_key_id`** (a Key Store entry), *not* per-host inventory variables.
- Therefore the right approach is to use Semaphore's **native key attachment**, and to **stop relying on** the Worker's custom `ansible_ssh_private_key_id` var (standard Ansible never consumes it).

Conclusion: R2 follows the existing `bootstrap.yml` IaC pattern; R1 must resolve the credential through Semaphore-native key attachment (or a deliberate playbook-level mechanism). No new non-standard variable scheme.

---

## 1. Purpose

Make the wizard's **"Onboard bare node"** path actually run `playbooks/vps/onboard.yml` end-to-end against a fresh VPS — i.e., move from "register a record" to "Ansible configures the box".

## 2. Scope / Out-of-scope

**In scope**
- **R2**: provision `onboard` + `audit` Job Templates and wire their ids into the Worker.
- **R1**: choose and implement the SSH credential model so (a) Semaphore can connect to the target and (b) `onboard.yml`'s managed-channel validation works.

**Out of scope** (tracked elsewhere in `backlog-2026-06-07.md`)
- R4 production inventory migration (`file`→`static`) — use the probe static inventory id `3` for first real onboard.
- R6 post-success inventory promotion + failure phase markers.
- R7/R8 Access auth / observability. R5 key-cleanup-on-delete. Offboard (TASK-010).

## 3. Current-state gap

- Onboard path is **disabled**: `SEMAPHORE_ONBOARD_TEMPLATE_ID` / `…AUDIT…` are empty → onboard-bare returns `412`, audit disabled.
- Credential is **not wired**: Worker writes the dead `ansible_ssh_private_key_id` var; `onboard.yml` managed validation shells `ssh -i <file path>` expecting a key file on the exec env.
- Execution-environment collection availability for `ansible.posix.*` / `community.general.ufw` must be confirmed (vendored under `collections/`, but the run env's `ANSIBLE_COLLECTIONS_PATH` must include it).

---

## 4. R2 — Template provisioning (concrete steps)

**Prereqs (verify first)**
1. The project's **repository** resource exists and points at the repo (`bootstrap.yml` already creates one → `/workspace`).
2. The Semaphore **execution environment resolves the vendored collections** (`ANSIBLE_COLLECTIONS_PATH` includes `./collections`, or they are installed in the image). Quick check: run the existing `site.yml (check mode)` template, or a one-off, and confirm `community.general` / `ansible.posix` load.

**Provisioning (IaC preferred, UI as quick-start)**

- **Preferred — extend `controller/semaphore/bootstrap.yml`** (reuses the existing `POST /templates` pattern at the "Create job template" task): add two templates
  - `VPS Onboard` → `playbook: playbooks/vps/onboard.yml`, inventory = the static inventory, repo = existing repo, app `ansible`.
  - `VPS Audit` → `playbook: playbooks/vps/audit.yml`, same inventory/repo.
  This keeps provisioning reproducible (UI-zero-touch, per `ARCHITECTURE.md`).
- **Quick-start alt — Semaphore UI**: Project → Task Templates → New, fill the same fields. Faster for a first manual test, but record it back into `bootstrap.yml` afterward.

**Wire into the Worker**
```bash
cd cf-worker
npx wrangler deploy \
  --var SEMAPHORE_URL:https://semaphore.saberu.com \
  --var SEMAPHORE_INVENTORY_ID:3 \
  --var SEMAPHORE_ONBOARD_TEMPLATE_ID:<onboard-id> \
  --var SEMAPHORE_AUDIT_TEMPLATE_ID:<audit-id>
```

**Verify**: hard-refresh the wizard → "Onboard bare node" enabled; `npm run smoke:deployed` still green; `GET /config` shows `onboardConfigured:true`.

---

## 5. R1 — Credential model (DECISION REQUIRED)

Onboard needs **two** credentials, and Semaphore resolves the connection via the **inventory `ssh_key_id`**, which is single-valued per inventory. The decision is how to supply them.

| Option | How it works | Pros | Cons | Effort |
|---|---|---|---|---|
| **A — Fleet-wide single key (recommended first cut)** | One Ansible keypair: its **public** key is pre-seeded on every fresh VPS's `root` (cloud-init / provider image / manual). Attach its **private** key as the static inventory's `ssh_key_id` *and* place it on the exec env at the path `onboard.yml` validates. Onboard installs the **same** public key for the managed user, so the one key works for `root@22` *and* later `ansible@39222`. | Trivial; uses Semaphore-native key attachment; no custom var; no playbook refactor; works across the bootstrap→managed transition with one key. | Every new VPS must already trust that one public key (you control provisioning). Browser-supplied per-host bootstrap creds are unused. | **Low** |
| **B — Per-host key, dynamic target** | Worker keeps creating a per-host Key Store entry; `onboard.yml` is refactored (localhost first play + `add_host` with runtime `ansible_ssh_private_key_file`/password from `vps_task.bootstrap.auth`). | Per-host bootstrap creds; matches the browser key/password flow; production inventory never holds bootstrap state. | Refactor of the 530-line self-validating `onboard.yml`; secure temp-key handling; this is the "Model B" the decision doc rejected on cost. | **High** |
| **C — Password bootstrap via Semaphore** | Browser submits a bootstrap **password**; Worker stores it as a `login_password` Key Store entry; that entry is the inventory `ssh_key_id` for the onboard run; onboard switches to key auth and lockdown. | Per-host; supports password-only fresh VPSs. | Still single-valued per inventory (one host onboarding at a time, or per-host inventory swap); password handling; needs the same lifecycle-transition handling as A. | **Medium** |

**Recommendation: Option A** for the first real onboard — it is the smallest change that makes the native model work end-to-end, and it pairs naturally with a **fleet-wide managed keypair** (public installed by onboard, private on the exec env for the `ansible_key.private_key` validation file). B/C can come later if per-host browser-supplied bootstrap creds become a hard requirement.

> Sub-decision regardless of option: the **managed-validation key file** (`vps_task.managed.ansible_key.private_key`) must exist on the Semaphore execution environment. With Option A this is the same fleet private key, baked into the exec env (or mounted as a secret) at a fixed path.

---

## 6. Phased roadmap

1. **A1 — Prereqs**: confirm repo resource + exec-env collections; create/identify the fleet Ansible keypair (Option A) and load it into Semaphore Key Store + exec env.
2. **A2 — R1**: implement the chosen credential model; attach the key as the static inventory `ssh_key_id`; ensure the validation key file is present.
3. **A3 — R2**: add onboard/audit templates (bootstrap.yml), capture ids, redeploy Worker `--var`.
4. **A4 — First real onboard**: against a **throwaway VPS** and the **probe static inventory (id 3)**, submit "Onboard bare node" from the wizard → watch the Semaphore task run `onboard.yml` → verify the box is reachable as `ansible@39222`.

## 7. Risks

- `onboard.yml` is **destructive on the target** (creates users, moves the SSH port, disables root/password login, closes port 22). **Test on a throwaway VPS first**, keep provider VNC/console as fallback.
- Credential material must not be logged (Worker already discards; keep playbook `no_log` on key tasks).
- Single inventory `ssh_key_id` means concurrent onboards of hosts needing *different* keys is not supported under Option A — acceptable for now (single-tenant).

## 8. Acceptance criteria

- Wizard "Onboard bare node" submit triggers a Semaphore task that **completes successfully**.
- The target is reachable as `ansible@39222` with key auth; root/password login disabled.
- `GET /config` shows `onboardConfigured:true`; `smoke:deployed` green.
- (Promotion of the inventory record to managed state is **R6**, out of scope here — the managed channel working is the bar for Phase A.)

## 9. Decision required before implementation

1. **R1 option: A / B / C** (recommended **A**).
2. Confirm the static inventory to use for the first onboard (**id 3 probe** recommended; production via R4 later).
3. Confirm provisioning route: **IaC `bootstrap.yml`** (preferred) vs UI quick-start.

---

## References

- Backlog: [`backlog-2026-06-07.md`](backlog-2026-06-07.md) (R1/R2)
- Decision: [`onboard-execution-models-2026-06-07.md`](onboard-execution-models-2026-06-07.md) (§6 credential surfaces, Model A/B)
- IaC: `controller/semaphore/bootstrap.yml` (template/repo/key/inventory creation pattern)
- Deploy: [`../../operations/cf-worker-deployment.md`](../../operations/cf-worker-deployment.md)
- Playbook contract: [`playbooks/vps/README.md`](../../../playbooks/vps/README.md) · onboard safety order in `onboard-execution-models §4`
