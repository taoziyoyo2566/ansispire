# Plan - Saberu VPS Takeover Execution Work Breakdown

> **Status**: APPROVED (2026-07-11)
> **Created**: 2026-06-24
> **Branch**: feat/target-architecture
> **Classification**: [L2] Architecture / Execution
> **Plan type**: Detail addendum
> **Approval scope**: named details
> **Parent plan**: [`plan-semaphore-native-onboard-2026-06-10.md`](plan-semaphore-native-onboard-2026-06-10.md)
> **Blocks implementation**: only execution details in this addendum
> **Does not supersede**: the parent plan remains the approved scope source. This document standardizes the execution work breakdown, gates, evidence, and closeout path for later implementers.

---

## §1 Why this plan exists

1. **What is missing**: the approved Jun-10 Semaphore-native onboard plan defines the technical path, but future executors need a standard work-breakdown document with task IDs, role boundaries, phase gates, evidence requirements, and closeout criteria.
2. **Why it matters**: this work touches a real VPS through Semaphore and can change SSH access, firewall rules, users, and service state. Ambiguous execution order or missing evidence can leave the target in an unknown state or make the product direction hard to resume later.
3. **Trigger**: on 2026-06-24, the user requested an implementer-grade plan that Codex, another agent, or a human operator can follow later, not a chat-only explanation.

The execution objective is the first Saberu MVP proof chain:

```text
Semaphore UI
  -> vps-fleet static inventory
  -> VPS Audit
  -> VPS Onboard
  -> managed-channel VPS Audit
  -> repeat audit = success + 0 changed
```

---

## §2 Current state

### Confirmed facts

- Product name and short-term direction are confirmed as **Saberu**: personal multi-VPS standardized takeover, hardening, software installation, service configuration, validation, and audit.
- D2 is closed as **Semaphore UI first** for the MVP operator surface. New custom UI/API work is deferred until this execution loop is proven.
- The active implementation path stays in `ansispire`, not a new repository.
- Parent execution plan [`plan-semaphore-native-onboard-2026-06-10.md`](plan-semaphore-native-onboard-2026-06-10.md) is approved and names the current proof chain.
- Existing lifecycle playbooks are under `playbooks/vps/`:
  - `playbooks/vps/audit.yml`
  - `playbooks/vps/onboard.yml`
  - `playbooks/vps/modify.yml`
  - `playbooks/vps/remove.yml`
- Semaphore provisioning code exists in:
  - `controller/semaphore/bootstrap.yml`
  - `controller/semaphore/bootstrap_preflight.yml`
  - `controller/semaphore/docker-compose.yml`
- Existing command surfaces include:
  - `make controller-bootstrap`
  - `make test-api-contract`
  - `make vps-lifecycle-syntax`
  - `make lint`
  - `make controller-loop-smoke`
  - `make detect-secrets`
- Prior investigations showed Semaphore `static` inventory whole-blob CRUD works, and task-level `environment` can carry nested `vps_task`.

### Evidence map

This addendum was updated after the rules reflection on 2026-06-24 to separate
repo facts from current external knowledge. Phase executors must re-check the
external claims when they become load-bearing.

| Claim / dependency | Evidence type | Freshness requirement | Close point |
|---|---|---|---|
| Semaphore can keep web-edited static inventory and bind a credential to an inventory | Semaphore UI official Inventory docs + local Phase 1 preflight | Re-check if Semaphore version/API changes | Phase 1 |
| Semaphore Key Store can hold SSH credentials for remote hosts | Semaphore UI official Key Store docs + operator UI confirmation | Re-check before changing credential model | Phase 1/2 |
| Semaphore task status and logs are acceptable live evidence | Semaphore UI official Tasks docs + actual task id/log | Re-check if evidence parser changes | Phase 1/3 |
| Semaphore API can launch tasks using a bearer token | Semaphore UI official API docs + smoke implementation | Re-check during `controller-vps-smoke` implementation | Phase 4 |
| Ansible check/diff modes can validate behavior, but diff output can reveal sensitive data | Ansible official docs | Re-check before adding diff output around secret-bearing tasks | Phase 1/2 |
| Runtime secret material should not be stored in images or source control | Docker official secrets docs + repo `secrets-handling.md` | Re-check if moving from gitignored mount to formal secret store | Phase 2 |
| Security-sensitive workflow rules should be evidence-backed and integrated into the development lifecycle | NIST SSDF + local rules reflection | Re-check when changing governance rules | Closeout |

Sources checked on 2026-06-24:

- Semaphore Inventory: https://semaphoreui.com/docs/user-guide/inventory
- Semaphore Key Store: https://semaphoreui.com/docs/user-guide/key-store
- Semaphore Tasks/logs: https://semaphoreui.com/docs/user-guide/tasks
- Semaphore API: https://semaphoreui.com/docs/admin-guide/api
- Ansible check/diff mode: https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_checkmode.html
- Docker secrets / runtime sensitive data: https://docs.docker.com/engine/swarm/secrets/
- NIST SSDF: https://csrc.nist.gov/pubs/sp/800/218/final

### Assumptions that must be re-verified

- Docker and the `ansispire-semaphore` container may still be available on the executor host.
- The Semaphore container may still resolve repo-vendored Ansible collections.
- A disposable or recoverable test VPS is available with bootstrap/root SSH access.
- The operator can inject real SSH private key material through Semaphore UI.

Per `.agents/rules/environment-truth.md`, none of these environment claims may be treated as current until re-probed in Phase 0.

### Constraints

- No secret material may be committed, pasted into chat, or stored in repo files.
- The agent does not handle private key contents directly. The operator injects private keys into Semaphore UI or a gitignored host secret path.
- Supported target OS scope is inherited from `TODO.md`: only Debian-family and RHEL-family systems are in scope.
- The first real onboard must use a disposable or easily recoverable VPS with provider console/VNC fallback.
- Initial live execution must limit blast radius. For the first run, `vps-fleet` should contain only the target VPS unless the executor has explicit operator approval for more hosts.
- Worker R3-R12, custom Saberu web/API, direct Ansible-first replacement, production inventory migration, offboard, and batch import remain out of scope.

### Unknowns and investigation register

Unknowns are allowed at plan time, but each must close before the phase that
depends on it.

| Unknown | Classification | Close at | Method | If contradicted |
|---|---|---|---|---|
| Exact Semaphore API payload/resource ids for new inventory/key/environment/templates | Needs web research before implementation + runtime probe | Phase 1 | Official API/OpenAPI if needed, existing `bootstrap.yml` pattern, live preflight | Update bootstrap/preflight before live VPS work |
| Whether `playbooks/vps/audit.yml` is truly side-effect free for the target state being audited | Needs repo review/runtime probe | Phase 1 before first live audit | Inspect tasks; if useful, run check/diff on one host with sensitive diff disabled | Split/rename audit path or document expected changes before proceeding |
| How the fleet public key is trusted by the bootstrap target account | Needs operator decision | Phase 1 before inventory entry | Confirm provider image/cloud-init/manual authorized_keys path | Stop; audit/onboard cannot run with the fleet private key until trust is established |
| Test VPS OS family | Needs operator decision + runtime probe | Phase 1 before live audit | Operator states OS; audit/preflight confirms Debian/RHEL family | Stop or create a separate OS support decision |
| Whether the same fleet private key must exist in both Semaphore Key Store and a container-mounted file | Needs implementation investigation | Phase 2 | Check whether Semaphore exposes a task-time key file path suitable for managed validation; otherwise document duplication | Amend secret lifecycle and rotation plan before onboard |
| Machine-readable source for repeat audit `0 changed` | Needs implementation detail | Phase 3/4 | Use Ansible recap from Semaphore raw log or a parser in `controller-vps-smoke` | Do not close idempotence gate until observable source is defined |
| Exact live target and external resource ids | Needs runtime/UI record | Phase 3/5 | External resource ledger and live go/no-go gate | Stop live run until ids/scope are recorded |

---

## §3 Scope

### In scope

- Standardize execution of the approved Saberu MVP proof chain.
- Re-probe Docker/Semaphore/runtime capability before relying on it.
- Add Semaphore-native `vps-fleet` resources for audit/onboard execution.
- Add and validate `VPS Audit` and `VPS Onboard` Semaphore templates.
- Fix `onboard.yml` runtime credential contracts required by the Semaphore container.
- Run audit first against a real test VPS.
- Run real onboard against a recoverable test VPS.
- Switch inventory to the managed channel and prove repeat audit `0 changed`.
- Add a commandized smoke target for the Semaphore-to-VPS path.
- Add TSVS documentation and round changelog evidence.
- Update task ledger and close the parent plan when all gates pass.

### Out of scope

- Creating a new Saberu repository.
- Building a custom TypeScript/React/API product shell.
- Re-enabling Worker as the active MVP path.
- Migrating production `targets-managed` file inventory to static inventory.
- Provider API automation for VPS creation.
- Offboard/reverse playbook implementation.
- Batch import and multi-key concurrent onboard support.
- AI Copilot scope.
- Postgres/HA migration.
- General service-profile catalog UX.

### Required operator inputs

| Input | Owner | Required by | Notes |
|---|---|---|---|
| Test VPS | Operator | Phase 1 | Must be safe to modify or reinstall. |
| Test VPS OS family | Operator | Phase 1 | Must be Debian-family or RHEL-family unless a separate support decision changes scope. |
| Bootstrap SSH access | Operator | Phase 1 | Root SSH on port 22 for the first audit/onboard path unless the environment explicitly uses another bootstrap user/port. The bootstrap account must trust the fleet public key or another declared credential. |
| Fleet keypair | Operator | Phase 1 | Private key is injected through Semaphore UI or a gitignored host secret path; target-side public key trust must be confirmed. Public key examples in repo must be demo/non-sensitive only. |
| Provider console/VNC fallback | Operator | Phase 3 | Required before running `VPS Onboard`. |
| Approval to proceed past gates | Operator/reviewer | Every phase gate | If a gate fails, stop and record the reason instead of continuing. |

### Start gate

Implementation must not begin from this document until:

1. this plan is approved and its status is changed to `APPROVED`;
2. the executor has read the parent plan and current `TODO.md`;
3. the executor has confirmed there are no newer branch changes that alter this scope.

---

## §4 Implementation plan

### Execution controls for all phases

- Keep each phase independently reviewable and committable.
- Do not silently expand scope. New product/UI/Worker/provider automation work needs a separate plan.
- Do not proceed past a failed gate. Record the failure and either apply the listed fallback or ask for operator decision.
- Redact real IPs, hostnames, usernames if needed, task log snippets, and credential-adjacent values before committing evidence.
- Prefer command checks over manual UI checks. When UI is required, record the task id/status and a sanitized log excerpt.
- The initial live `vps-fleet` inventory must contain only the intended test host unless the operator explicitly approves multiple hosts.
- Use the next available target-architecture round changelog name at execution time. `round10` is expected only if no intervening round lands before this plan executes.
- At the start of each phase, re-check external facts or unresolved unknowns that become load-bearing in that phase.

### Phase 0 - Execution readiness and runtime probe

**Goal**: prove the local/Semaphore runtime can execute the VPS playbooks before changing workflow resources.

**Pre-condition**: this plan is approved; parent plan remains active; no newer plan supersedes it.

**Steps**:

1. **P0.1 - Baseline repo state**
   - Run `git status --short --branch`.
   - Run `git log --oneline --decorate --max-count=5`.
   - Read `TODO.md`, this plan, and the parent plan.
   - If resuming after a different machine/session, perform the repo freshness check per `.agents/rules/session-bootstrap.md` and `.agents/rules/git.md`.
2. **P0.2 - Environment registry**
   - Run `make env-probe-check`.
   - If missing/stale, run `make env-probe`.
   - Read the generated `.agents/env/<hostname>.yml` and note Docker/Semaphore capability status.
3. **P0.3 - Controller runtime**
   - Run `make controller-up`.
   - Identify the Semaphore container name with `docker ps`.
   - Confirm the container has `ansible-playbook`.
4. **P0.4 - Repo checkout and collection resolution**
   - From the Semaphore container, run:
     ```bash
     docker exec -w /workspace <semaphore-container> \
       ansible-playbook --syntax-check playbooks/vps/onboard.yml
     ```
   - If `/workspace` does not exist or does not contain the repo, trigger a safe existing Semaphore task to force checkout, or document the missing checkout and stop for review.
5. **P0.5 - Evidence note**
   - Capture sanitized command results for the next target-architecture round changelog.

**Runtime decision table**:

| Probe result | Next action |
|---|---|
| Syntax check passes | Proceed to Phase 1. |
| `couldn't resolve module` or missing collection | Implement the parent-plan Dockerfile fallback: install collections from `requirements.yml` into the Semaphore image, rebuild, and repeat Phase 0. |
| Docker daemon unavailable | Stop and record environment blocker with fresh probe evidence. Do not mark Phase 0 passed. |
| Semaphore container unavailable | Run the documented controller startup path; if it still fails, stop and record blocker. |
| Repo checkout missing in container | Trigger or fix the checkout path, then repeat syntax check. |

**Gate**: Phase 0 passes only when container-side syntax check exits 0 and no unresolved collection error remains.

**Deliverables**:

- Fresh environment probe evidence.
- Optional Dockerfile/compose fallback diff if collection resolution fails.
- Sanitized Phase 0 evidence reserved for the next target-architecture round changelog.

### Phase 1 - Semaphore audit resources and first audit

**Goal**: prove Semaphore can connect to a real VPS and execute `playbooks/vps/audit.yml` without performing takeover changes.

**Pre-condition**: Phase 0 gate passed; operator has a recoverable VPS and fleet key material ready.

**Steps**:

1. **P1.1 - Extend Semaphore bootstrap**
   - Edit `controller/semaphore/bootstrap.yml` to create:
     - `vps-fleet-key` placeholder SSH key with `REPLACE-VIA-UI`;
     - `vps-fleet` static inventory bound to `vps-fleet-key`;
     - `vps-audit-env` with audit defaults from `playbooks/vps/examples/audit.yml`;
     - `VPS Audit` template using `playbooks/vps/audit.yml`, the existing repository resource, and `vps-fleet`.
2. **P1.2 - Extend preflight**
   - Edit `controller/semaphore/bootstrap_preflight.yml` to assert:
     - `vps-fleet` exists;
     - inventory type is `static`;
     - `vps-fleet-key` exists;
     - `VPS Audit` template exists;
     - audit environment exists.
3. **P1.3 - Audit side-effect check**
   - Inspect `playbooks/vps/audit.yml` before first live use.
   - Confirm it does not intentionally modify SSH, firewall, users, packages, or service state.
   - If check/diff mode is used for validation, disable or redact sensitive diff output.
   - If the audit path has expected changes, document them and stop for reviewer/operator approval before live execution.
4. **P1.4 - Run controller bootstrap checks**
   - Run `make controller-bootstrap`.
   - Run `make test-api-contract`.
   - Re-run `make controller-bootstrap` to check idempotence if the command supports safe repeat.
5. **P1.5 - Operator key injection**
   - Operator replaces `vps-fleet-key` placeholder in Semaphore UI with the real private key.
   - Agent must not receive or store private key content.
6. **P1.6 - Operator inventory entry**
   - Confirm the target is Debian-family or RHEL-family.
   - Confirm the bootstrap account trusts the fleet public key or another declared bootstrap credential.
   - Operator adds exactly one first-test host to `vps-fleet`, for example:
     ```ini
     [vps_targets]
     test-vps ansible_host=<redacted-ip> ansible_user=root ansible_port=22
     ```
7. **P1.7 - Run `VPS Audit`**
   - Run the task from Semaphore UI.
   - Capture task id, final status, and sanitized log excerpt.
8. **P1.8 - Start external resource ledger**
   - Record `vps-fleet`, `vps-fleet-key`, `vps-audit-env`, and `VPS Audit` names/ids in the changelog draft or operator runbook.

**Gate**: `VPS Audit` task completes with `status=success`, and logs show expected audit checks against the target VPS.

**Deliverables**:

- `controller/semaphore/bootstrap.yml` diff.
- `controller/semaphore/bootstrap_preflight.yml` diff.
- Audit side-effect decision.
- Sanitized task evidence and resource ids for the next target-architecture round changelog.

### Phase 2 - Onboard runtime contract and template wiring

**Goal**: make `playbooks/vps/onboard.yml` runnable from the Semaphore container with explicit credential inputs.

**Pre-condition**: Phase 1 gate passed.

**Steps**:

1. **P2.1 - Add inline public-key support**
   - Edit `playbooks/vps/onboard.yml` so managed `authorized_keys` can use `public_key_content`.
   - Keep the existing `public_key` file-path branch as compatibility behavior.
   - Avoid a Jinja `default(lookup(...))` pattern that eagerly evaluates file lookup when inline content exists.
2. **P2.2 - Add managed private-key container path**
   - Edit `controller/semaphore/docker-compose.yml` to support a read-only gitignored secret mount for the fleet private key, for example:
     ```text
     controller/semaphore/secrets/vps-fleet-key -> /etc/ansispire/keys/vps-fleet-key:ro
     ```
   - Update `.gitignore` to exclude the host secret path.
   - Update any example env or README note needed to document the path without exposing key material.
   - Document why the same fleet private key is needed in Semaphore Key Store and as a mounted file, who can access each copy, how rotation works, and what later change could remove duplication.
   - Re-check `onboard.yml` secret-handling tasks for `no_log`/`diff: false` where key material or secret-adjacent content may be exposed.
3. **P2.3 - Update onboard examples**
   - Edit:
     - `playbooks/vps/examples/onboard.minimal.yml`
     - `playbooks/vps/examples/onboard.standard.yml`
   - Use `public_key_content` in examples.
   - Set `vps_task.managed.ansible_key.private_key` to the container path convention.
4. **P2.4 - Add onboard Semaphore resources**
   - Extend `controller/semaphore/bootstrap.yml` with:
     - `vps-onboard-env`;
     - `VPS Onboard` template using `playbooks/vps/onboard.yml`, the existing repository resource, and `vps-fleet`.
   - Extend `controller/semaphore/bootstrap_preflight.yml` to assert both resources exist.
5. **P2.5 - Static validation**
   - Run `make vps-lifecycle-syntax`.
   - Run `make lint`.
   - Run `make detect-secrets`.
   - Run `make controller-bootstrap`.
   - Run `make test-api-contract`.

**Gate**: all Phase 2 checks pass, and the diff shows no secret material.

**Deliverables**:

- `playbooks/vps/onboard.yml` diff.
- Onboard example diffs.
- `controller/semaphore/docker-compose.yml` and ignore/doc updates.
- Bootstrap/preflight diffs for `VPS Onboard`.
- Secret lifecycle note for Key Store + mounted file handling.
- Validation command results for the changelog.

### Phase 3 - Real onboard and managed-channel audit

**Goal**: complete the live Saberu MVP takeover proof on a recoverable VPS.

**Pre-condition**: Phase 2 gate passed; operator confirms the target VPS is recoverable and console/VNC fallback is available.

**Steps**:

1. **P3.1 - Safety confirmation**
   - Confirm `vps-fleet` contains only the intended target host unless explicit multi-host approval is recorded.
   - Confirm provider console/VNC fallback.
   - Confirm the fleet private key is installed in Semaphore Key Store and available at the configured container path.
2. **P3.2 - Bootstrap latest Semaphore resources**
   - Run `make controller-bootstrap`.
   - Confirm `VPS Audit` and `VPS Onboard` exist in Semaphore UI.
3. **P3.3 - Run pre-onboard audit**
   - Run `VPS Audit` against the bootstrap channel.
   - Confirm `status=success`.
4. **P3.4 - Final live go/no-go gate**
   - Record exact target host(s), expected host count, inventory id/content summary, `VPS Onboard` template id, environment id, credential id/name, expected SSH/firewall/user/package/service impact, fallback owner, and evidence capture path.
   - Obtain explicit operator approval for this specific live run.
5. **P3.5 - Run `VPS Onboard`**
   - Start the task from Semaphore UI.
   - Monitor logs until final state.
   - Stop if the task fails; do not manually continue with later phases until the failure is understood.
6. **P3.6 - Validate managed SSH**
   - Confirm the managed user exists.
   - Confirm managed SSH port is reachable.
   - Confirm the fleet key logs in through the managed channel.
7. **P3.7 - Switch inventory to managed channel**
   - Update the host entry in `vps-fleet`, for example:
     ```ini
     [vps_targets]
     test-vps ansible_host=<redacted-ip> ansible_user=<managed-user> ansible_port=<managed-port>
     ```
8. **P3.8 - Run managed-channel audit**
   - Run `VPS Audit`.
   - Confirm `status=success`.
9. **P3.9 - Prove idempotence**
   - Run `VPS Audit` again on the managed channel.
   - Confirm `status=success` and `0 changed` from a named observable source: Ansible recap in Semaphore raw log, Semaphore API log artifact, or the future `controller-vps-smoke` parser.
10. **P3.10 - Optional second-host proof**
   - If the operator provides a second recoverable VPS, repeat P1.6 through P3.9 for that host to prove the inventory supports more than one node.
   - This is recommended but not required for closing the first MVP proof chain.

**Gate**: `VPS Onboard` succeeds, managed SSH works, and repeat managed-channel `VPS Audit` reports `success + 0 changed`.

**Deliverables**:

- Sanitized Semaphore task ids/statuses.
- Sanitized audit/onboard log excerpts.
- Final live go/no-go record.
- Managed-channel proof summary.
- If Phase 3 fails, a blocker note that names the exact failed step and recovery state.

### Phase 4 - Commandized regression and TSVS

**Goal**: convert the proven path into repeatable regression coverage.

**Pre-condition**: Phase 3 gate passed.

**Steps**:

1. **P4.1 - Add `controller-vps-smoke`**
   - Add a Make target that triggers the `VPS Audit` template through Semaphore API and polls task status.
   - Prefer the existing `controller-loop-smoke` pattern for API launch and polling.
   - The smoke target should fail non-zero if the task fails or times out.
   - Document required environment variables, target selection, timeout behavior, skip/blocker semantics, and the exact parser used for `0 changed`.
2. **P4.2 - Add TSVS**
   - Create `docs/reference/test-specs/vps-semaphore-native-e2e.md`.
   - Use `docs/reference/test-specs/TEMPLATE.md` as the structure source.
   - Include preconditions, commands, manual UI steps if unavoidable, pass/fail criteria, and redaction rules.
3. **P4.3 - Register the test surface**
   - Update `docs/reference/test-specs/INDEX.md`.
   - Update `docs/governance/testing-governance.md` so future executors know when to run `controller-vps-smoke`.
4. **P4.4 - Run regression set**
   - Run:
     ```bash
     make vps-lifecycle-syntax
     make lint
     make test-api-contract
     make controller-vps-smoke
     ```

**Gate**: `controller-vps-smoke` passes against the managed-channel target, and the TSVS/index/governance references are committed-ready.

**Deliverables**:

- `Makefile` diff.
- Smoke implementation helper script, if needed.
- `docs/reference/test-specs/vps-semaphore-native-e2e.md`.
- `docs/reference/test-specs/INDEX.md` update.
- `docs/governance/testing-governance.md` update.

### Phase 5 - Closeout and handoff

**Goal**: turn the live proof into durable project truth and make the next work item clear.

**Pre-condition**: Phase 4 gate passed.

**Steps**:

1. **P5.1 - Write round changelog**
   - Add `docs/reviews/feat-target-architecture/round<N>-YYYY-MM-DD.changelog.md` using the next available round number.
   - Include:
     - Phase 0 runtime probe result;
     - Phase 1 audit evidence;
     - Phase 2 code/resource changes;
     - Phase 3 onboard and managed audit evidence;
     - Phase 4 smoke/TSVS evidence;
     - external resource ledger;
     - closeout reflection: plan contradictions, rules gaps, and what the next executor must re-check;
     - known limitations and deferred work.
2. **P5.2 - Update source-of-truth docs**
   - Update `TODO.md`:
     - mark Phase 0-3 complete;
     - replace immediate next step with post-proof options.
   - Update `ARCHITECTURE.md` if operator entry points changed.
   - Update `docs/reference/feature-map/vps-lifecycle.md` and `docs/reference/feature-map/INDEX.md` if the feature map needs new resource/test entries.
   - Update `CHANGELOG.md [Unreleased]` for user-visible make target and onboard contract changes.
   - Update `docs/operations/` with an operator runbook if one does not already exist.
3. **P5.3 - Close plans**
   - Change this plan status to `COMPLETED` and add `> **Completed**: YYYY-MM-DD`.
   - Change the parent plan status to `COMPLETED` only after its §7 checklist is done.
4. **P5.4 - Publish recommendation**
   - Propose a docs/code commit split if changes are large.
   - Propose push only after the operator approves the exact commit state.

**Gate**: all closeout docs are updated, the task ledger is consistent, and final verification commands are recorded.

**Deliverables**:

- Next target-architecture round changelog.
- Updated `TODO.md`.
- Updated user/operator docs as applicable.
- Completed status on this plan and parent plan.
- Final handoff note naming next recommended work.

---

## §5 Verification

### Phase verification matrix

| Phase/WU | Verification method | Pass condition | Evidence artifact |
|---|---|---|---|
| Phase 0 | `make env-probe-check` or `make env-probe`; container-side `ansible-playbook --syntax-check playbooks/vps/onboard.yml` | Fresh environment record exists; syntax check exits 0; no unresolved collection error | next round changelog Phase 0 section; optional `.agents/env/<host>.yml` diff |
| Phase 1 | `make controller-bootstrap`; `make test-api-contract`; audit side-effect review; Semaphore UI `VPS Audit` task | Bootstrap/preflight pass; audit side-effect status is documented; audit task `status=success` against supported test VPS | next round changelog Phase 1 section with sanitized task id/log/resource ids |
| Phase 2 | `make vps-lifecycle-syntax`; `make lint`; `make detect-secrets`; `make controller-bootstrap`; `make test-api-contract`; diff review | All commands pass; no secret material in diff; secret lifecycle is documented; `VPS Onboard` resources exist | next round changelog Phase 2 section |
| Phase 3 | Final live go/no-go record; Semaphore UI `VPS Onboard`; managed SSH login check; two managed-channel `VPS Audit` runs | Onboard task success; managed SSH reachable; repeat audit `status=success` and `0 changed` from named observable source | next round changelog Phase 3 section with sanitized evidence |
| Phase 4 | `make controller-vps-smoke`; TSVS/index/governance review | Smoke exits 0; new TSVS registered; testing governance names the target; smoke docs define target/timeout/skip semantics | next round changelog Phase 4 section |
| Phase 5 | Documentation diff review; final command summary; reflection | `TODO.md`, changelog, test specs, operations/feature docs, and plan statuses are consistent; contradictions/rules gaps are recorded | next round changelog closeout section |

### Overall acceptance criteria

This execution plan is done only when all of the following are true:

1. A real recoverable VPS was audited through Semaphore before takeover.
2. The VPS is confirmed to be Debian-family or RHEL-family, or a separate OS support decision exists.
3. The audit side-effect contract is documented.
4. The same VPS was onboarded through Semaphore using `VPS Onboard`.
5. The same VPS is reachable through the managed SSH channel.
6. Managed-channel `VPS Audit` succeeds.
7. Repeat managed-channel `VPS Audit` reports `0 changed` from a named observable source.
8. External Semaphore/VPS resources are recorded in a ledger.
9. Secret lifecycle for Key Store + mounted key handling is documented.
10. `make controller-vps-smoke` passes.
11. TSVS and testing-governance entries exist for the new smoke path.
12. The next target-architecture round changelog records sanitized evidence.
13. `TODO.md` no longer points to this work as pending.
14. This plan and the parent plan are marked `COMPLETED`.

### Failure classification

| Failure type | Required handling |
|---|---|
| Environment unavailable | Re-probe, record fresh evidence, and stop. Do not mark gate passed. |
| External docs/API contradict the plan | Stop, classify the contradiction, and update the plan/addendum before implementation. |
| Semaphore resource creation fails | Keep code changes, record failing API response/status, fix bootstrap/preflight before live VPS work. |
| Target OS is unsupported | Stop and request a support-scope decision instead of forcing onboard. |
| Audit cannot connect | Treat as credential/inventory/network issue. Do not proceed to onboard. |
| Onboard fails before SSH lockdown | Diagnose playbook/task failure and rerun only if idempotence/safety is understood. |
| Onboard fails after SSH/ firewall changes | Use provider console/VNC or reinstall target VPS; record failure state. |
| Repeat audit is not `0 changed` | Treat as idempotence defect; do not close plan until explained or fixed. |

---

## §6 Risks and fallbacks

| Risk | Likelihood | Impact | Mitigation | Fallback |
|---|---|---|---|---|
| Semaphore container cannot resolve vendored Ansible collections | Medium | Medium | Phase 0 container-side syntax check before live work | Build Semaphore image with `ansible-galaxy collection install -r requirements.yml`, then repeat Phase 0 |
| Target VPS SSH is locked out during onboard | Medium | High | Use disposable VPS; require console/VNC fallback; keep first run single-host | Recover through console or reinstall; record blocker and do not continue blindly |
| Private key material leaks into repo/chat/logs | Low | High | Operator injects keys through UI or gitignored mount; diff review for secrets | Rotate fleet key; purge leaked material; rerun secret checks |
| First `vps-fleet` inventory accidentally includes multiple hosts | Medium | High | Require single-host initial inventory unless operator approves multi-host run | Stop task if possible; restore inventory; record incident and tighten preflight/operator runbook |
| `onboard.yml` changes are syntactically valid but behaviorally wrong | Medium | High | Run audit first, then one disposable onboard, then managed audit | Reinstall VPS and fix playbook; do not promote to smoke until repeat audit is stable |
| `controller-vps-smoke` depends on live mutable state | Medium | Medium | Document preconditions in TSVS and testing governance | Mark smoke as L4/live-gated; provide skip/blocker language when environment is unavailable |
| Test VPS is outside Debian/RHEL support scope | Low-Medium | Medium | Confirm OS before live audit/onboard | Stop and create a separate support decision if needed |
| Fleet key duplication becomes permanent architecture debt | Medium | Medium | Record lifecycle and exit path during Phase 2 | Revisit credential model before expanding beyond first proof |
| Existing docs drift from this plan after later edits | Medium | Medium | Close with TODO/changelog/feature-map/testing-governance sync | Add a new dated follow-up plan rather than silently rewriting this one |

---

## §7 Post-completion checklist

- [ ] Next `docs/reviews/feat-target-architecture/round<N>-YYYY-MM-DD.changelog.md` records all phase evidence.
- [ ] The round changelog includes an external resource ledger.
- [ ] The round changelog includes closeout reflection: plan contradictions, rules gaps, and next re-check items.
- [ ] `TODO.md` marks this proof chain complete and names the next active work.
- [ ] `ARCHITECTURE.md` reflects current Saberu/Semaphore operator entry points if changed.
- [ ] `docs/reference/feature-map/vps-lifecycle.md` reflects `vps-fleet`, `VPS Audit`, `VPS Onboard`, and smoke coverage if changed.
- [ ] `docs/reference/feature-map/INDEX.md` remains consistent with feature-map changes.
- [ ] `docs/reference/test-specs/vps-semaphore-native-e2e.md` exists.
- [ ] `docs/reference/test-specs/INDEX.md` registers the new TSVS.
- [ ] `docs/governance/testing-governance.md` includes `controller-vps-smoke` in the relevant decision tree and command table.
- [ ] `docs/operations/` has an operator runbook for fleet key preparation, Semaphore UI injection, inventory update, and smoke execution.
- [ ] `CHANGELOG.md [Unreleased]` records user-visible workflow/command changes.
- [ ] This plan status is `COMPLETED` with a completion date.
- [ ] Parent plan [`plan-semaphore-native-onboard-2026-06-10.md`](plan-semaphore-native-onboard-2026-06-10.md) status is `COMPLETED` only after its own §7 checklist is satisfied.

### Work unlocked after completion

- TASK-010 offboard/reverse playbook.
- Batch import for multiple VPS records.
- Profile catalog for baseline/software/service bundles.
- AI Copilot scope decision D3, now grounded in a real workflow.
- Reassessment of whether a thin Saberu UI/API layer is justified.
- Worker R3-R12 only if native Semaphore UI becomes the limiting factor.
