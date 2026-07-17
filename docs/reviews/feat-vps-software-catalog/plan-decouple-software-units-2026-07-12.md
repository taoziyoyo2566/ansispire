> **Status**: SUPERSEDED
> **Created**: 2026-07-12
> **Branch**: feat/vps-software-catalog
> **Classification**: [L2] Architecture
> **Superseded by**:
> [`../feat-vps-profile-catalog/plan-software-profile-pilot-2026-07-17.md`](../feat-vps-profile-catalog/plan-software-profile-pilot-2026-07-17.md)
> **Updated**: 2026-07-17 — review found that a software-only catalog did not
> solve the wider configuration-ownership and discoverability problem. The
> replacement is a child of the composable VPS profile direction and includes
> per-host BaselineProfile assignment, migration, validation, test wiring, and
> safe live gates.

# Plan — Decouple VPS software into named, composable units

Historical draft retained as evidence. Do not implement from this document.

---

## 0. Best-practice pre-check (W-R18)

**Question**: does Ansible already have a native way to express "each software is an
independent, named, config-carrying unit; per-host you compose which units apply"?

**Yes — and this repo already uses it, in one path but not the other.**

- Native mechanism: **role task-files + `include_tasks`/`include_role` (loopable) + `tags:` for runtime subsetting + host/group data for selection.** A role/task-file *is* "a named unit with its own install + config + handlers".
- The repo **already realizes this** in `roles/common/tasks/security.yml`: fail2ban / UFW+firewalld / SSH-hardening / limits / async-upgrade, each organized under `tags: [fail2ban] / [firewall] / [ssh] / [limits] / [upgrade]`. This is exactly the "fail2ban belongs to a security tag" model the request describes — it lives here, applied via `site.yml → hosts: all`.
- The Saberu VPS path (`playbooks/vps/onboard.yml`, `modify.yml`) **diverged**: it re-implements the same software inline as hardcoded `vps_task.*` sections, with its own copies of fail2ban, limits.conf, SSH hardening, and firewall.

**Conclusion**: do **not** invent a bespoke catalog DSL. Realize the request with native
constructs, and **converge the divergent Saberu inline implementation toward the
role/tag pattern that already exists** — one reusable software-unit mechanism, not a
third parallel one. The selection ("which units on this host") is **data**; the unit
definition ("how to install/configure") is **data-plane role logic** (repo §3
control/data decoupling).

---

## 1. Problem statement

The intent (from the request) is **decoupling**: today the software logic is *mixed into
one file and duplicated*, so per-VPS software management is inflexible and drift-prone.

Concrete evidence:

- `playbooks/vps/onboard.yml` is ~476 task-lines that interleave the **takeover skeleton**
  (identity, SSH cutover, firewall port choreography, validation) with **independent
  software units** (fail2ban, unattended-upgrades, swap, network tuning, limits) as inline
  blocks gated by ad-hoc `when` conditions.
- **fail2ban is duplicated**: onboard.yml (lines 255–288: EPEL → install → jail template →
  enable) and modify.yml (its own install → jail template → enable) — same template
  `templates/fail2ban_sshd.local.j2`, two copies of the logic.
- **limits.conf is duplicated across paths**: onboard writes `99-ansispire.conf`;
  `roles/common/security.yml` writes `99-ansible.conf` — same content, two owners.
- **docker is duplicated**: `roles/geerlingguy.docker` is vendored, yet `docker_host.yml`
  installs docker inline with `ansible.builtin.package`.
- **No selection-by-name/tag** in the Saberu path: sections are hardcoded; adding a new
  software means editing the skeleton playbook and adding a special-case `when`.

## 2. Scope

### In scope (this initiative)
- Establish **one reusable, named, composable software-unit mechanism** for the VPS
  lifecycle, consumed by both `onboard.yml` and `modify.yml`.
- **Pilot: fail2ban** — extract to a unit; both playbooks consume it; delete both inline
  copies; encapsulate the RHEL/EPEL divergence inside the unit.
- **Selection-as-data**: a `vps_task.software` list (+ optional per-unit `software_config`
  overrides), validated by extending the existing `vps_task.schema.json`.
- Additional generic units after the pilot: **unattended-upgrades, swap, network_tuning,
  system_limits**.

### Out of scope (explicit — do NOT touch this round)
- **The takeover skeleton stays coupled and ordered**: UFW/firewall **port choreography**
  (allow managed port before lockdown, keep bootstrap port open until validated, close it
  after) and the **SSH cutover sequence** (drop-ins, transitional→locked-down, socket
  activation, managed-channel validation). These are order-critical and are **not**
  decomposed into freely-composable units. A thin *firewall-policy* unit may be revisited
  later, but port management remains in the skeleton.
- **Wholesale reconciliation of `roles/common/security.yml` + `site.yml`** — align new
  units to its conventions, but converging the two paths fully is a separate track (§8-2).
- **Big service roles** (webserver / database / docker) — already role-based. Fix the
  `docker_host.yml` inline-vs-vendored duplication only if trivially cheap, else defer.
- **Semaphore template wiring for `modify`** and **offboard (TASK-010)** — separate backlogs.

## 3. Level & review focus

[L2] Architecture. Review lens (workspace §1 architecture row):

| Lens | Applied to this change |
|---|---|
| Control / data split | Catalog + unit tasks = data-plane logic; per-host selection = control data (host_vars / Semaphore Environment JSON). |
| Consistency | One implementation per software; kill the fail2ban / limits.conf / docker duplication and the site-vs-vps drift. |
| Testability | Each unit independently molecule-testable; a schema gate on selection. |
| Scale | Adding a software = new unit file + one catalog row; **zero edits to the takeover skeleton**. |
| Audit | Selection is schema-validated declarative data — readable per host, diffable. |

## 4. Current-state gap analysis

### 4.1 onboard.yml — skeleton vs decouplable units

| Block (onboard.yml lines) | Classification | Decouple? |
|---|---|---|
| pre_tasks: asserts + SSH facts/socket probe (25–84) | Skeleton | No |
| Base packages install/remove (87–99) | Generic package layer | Keep as-is (trivial pkgs) |
| Managed user / group / keys / sudo (101–146) | Skeleton (identity) | No |
| system_limits (147–159) | **Unit** | Yes → `limits` unit |
| unattended-upgrades (161–168) | **Unit** (Debian) | Yes |
| swap (170–221) | **Unit** | Yes |
| network_tuning BBR/TFO/MTU (222–253) | **Unit** | Yes |
| **fail2ban (255–288)** | **Unit** (+EPEL on RHEL) | **Yes — PILOT** |
| UFW install + port choreography + enable (290–366) | **Skeleton-coupled** | No (port mgmt is takeover-critical) |
| SSH cutover: drop-ins → transitional → validate → locked-down → close bootstrap → validate (368–560) | Skeleton (order-critical) | No |

### 4.2 Cross-file duplication / drift

| Concern | Impl A | Impl B | Gap |
|---|---|---|---|
| fail2ban | `onboard.yml` 255–288 (jail template + enable + EPEL) | `modify.yml` (install + jail template + enable) | Two copies, one template; drift risk |
| limits.conf | `onboard.yml` → `99-ansispire.conf` | `roles/common/security.yml` → `99-ansible.conf` | Same content, two files/owners |
| SSH hardening | `onboard.yml` drop-in `sshd_config.d/00-ansispire.conf` | `roles/common/security.yml` `lineinfile` on main config | Different mechanisms, same intent |
| firewall | `onboard.yml` UFW w/ port choreography | `roles/common/security.yml` UFW+firewalld generic | vps one is takeover-aware; common is generic |
| docker | `roles/geerlingguy.docker` (vendored) | `docker_host.yml` inline package | Role unused on vps path |

### 4.3 Path context
- `roles/common/security.yml` runs via `site.yml` (`hosts: all`) — the classic hub/app
  deploy path. Tag-organized (`[fail2ban]`, `[firewall]`, `[ssh]`, `[limits]`, `[upgrade]`).
- `playbooks/vps/*` run against `vps_targets` — the Semaphore takeover path. Section-based.
- They do **not** co-apply in one run today, so duplication is not an active runtime
  collision — but it **is** two divergent sources of truth for the same software intent.

## 5. Target model

### 5.1 Two layers
1. **Takeover skeleton** (fixed order, unchanged behavior): asserts → identity →
   **[software units applied at a single well-defined point]** → firewall port
   choreography → SSH cutover → validation.
2. **Software units** — independent, named, each self-contained (install + config +
   handler + OS divergence). Applied by iterating the host's selection list.

### 5.2 Unit form — RECOMMENDED, but see §8-1 (open decision)
A dedicated role `roles/vps_software/` with `tasks/<name>.yml` (one file per software) +
`templates/` + `defaults/main.yml`, invoked from the skeleton by a loop:

```yaml
# in onboard.yml / modify.yml, replacing the inline blocks:
- name: Apply selected software units
  ansible.builtin.include_role:
    name: vps_software
    tasks_from: "{{ item }}.yml"
  loop: "{{ vps_task.software | default([]) }}"
```

Rationale: gets molecule coverage like the other roles; aligns with the repo's role
pattern and with `roles/common`'s tag conventions; keeps "one file per software"; the
unit encapsulates OS divergence (e.g. fail2ban's EPEL step) so the skeleton stops
special-casing it.

### 5.3 Selection = data
```yaml
vps_task:
  software:                     # WHICH units — pure data (Semaphore Env JSON can drive it)
    - fail2ban
    - unattended_upgrades
  software_config:              # optional per-unit overrides; unit ships defaults
    fail2ban:
      sshd: { bantime: 7200, findtime: 600, maxretry: 5 }
```
- **Selection is data, not ansible `tags:`.** Ansible `tags:` are for runtime subsetting
  (`--tags fail2ban`) and will be *aligned* to unit names (mirroring `roles/common`), so
  `--tags security` style runs still work — but "which host gets what" is the `software`
  list, never a `tags:` decision.

### 5.4 Catalog + schema
- `roles/vps_software/catalog.yml` (or `defaults`): name → `{ category, os_support,
  default params, template }`. Category enables coarse "install everything in `security`"
  selection as a **data filter**, not an ansible tag.
- Extend `playbooks/vps/examples/vps_task.schema.json`: add `software` (array of enum'd
  unit names) + `software_config` (object keyed by unit name). Reuse the just-built
  `make test-vps-examples-schema` gate.

## 6. Per-change rationale (summary)

| Change | Why |
|---|---|
| Extract fail2ban → `vps_software` unit | Kill the onboard/modify duplication; encapsulate EPEL; prove the pattern. |
| `vps_task.software[]` + `software_config{}` | Selection-as-data; per-host flexibility without editing the skeleton. |
| Skeleton loops over selection | Adding software = new file + catalog row, zero skeleton edits. |
| Schema extension + gate | Keep selection declarative + validated (continuity with round `8c816f0`). |
| Align unit tags to `roles/common` | One convention across both paths; groundwork for eventual convergence. |

## 7. Phased roadmap

> Each phase ends with: 3-gate (direction / syntax / functional), molecule where
> applicable, a `roundN` changelog, and a Next-Steps block. Phases are separately
> approvable; **do not auto-continue past a phase that changes the proven takeover path
> without re-validation (§9).**

- **Phase 0** — this plan → approval. *(no code)*
- **Phase 1 (PILOT: fail2ban)** — create `roles/vps_software/` + `tasks/fail2ban.yml`
  (+ move `fail2ban_sshd.local.j2`); wire the selection loop into `onboard.yml` and
  `modify.yml`; **delete both inline fail2ban copies**; add `software`/`software_config` to
  examples + schema; molecule scenario for the unit. **Re-validate onboard on u24 + d13**
  (managed re-audit `changed=0`) — the acceptance gate.
- **Phase 2 (generic units)** — unattended_upgrades, swap, network_tuning, system_limits;
  resolve the limits.conf double-write (choose one filename/owner).
- **Phase 3 (catalog + categories)** — formal `catalog.yml`, category-based selection,
  schema hardening (enum unit names).
- **Phase 4 (reconcile with `roles/common`)** — align or share units across the
  site/vps paths; OR formally defer as a documented separate track.
- **Phase 5 (wiring + docs)** — `modify` Semaphore template (ties to the earlier backlog);
  operator-guide §11 + feature-map/INDEX + CHANGELOG sync.

## 8. Open decisions (need input at/before Phase 1)

1. **Unit form**: `roles/vps_software/` with `tasks/<name>.yml` (recommended) vs plain
   task-files under `playbooks/vps/software/<name>.yml` vs one mini-role per software.
2. **Reconcile with `roles/common/security.yml`**: converge now / align-conventions-only /
   defer to a separate track. (Recommend: align-only this initiative; full convergence later.)
3. **UFW**: keep entirely in the skeleton (recommended) or later extract a policy-only unit
   (ports stay in skeleton regardless).
4. **Selection key name**: `software` vs `features` — must not clash with the existing
   `vps_task.packages.install` (trivial packages stay there).
5. **Pilot breadth**: fail2ban only, or fail2ban + one more (e.g. unattended_upgrades) to
   exercise the loop with 2 units.

## 9. Test strategy & the re-validation risk

- **Risk**: Phase 1 edits `onboard.yml`, which is **real-VPS-proven** (u24 + d13, managed
  re-audit `changed=0`). A refactor that changes task identity/order can regress the
  takeover. **Mandatory acceptance**: after Phase 1, re-run the full onboard→managed→
  re-audit loop on u24 + d13 and require `success` + `changed=0`; `make controller-vps-smoke`
  green. Treat any diff in the proven behavior as a stop-and-surface.
- Per-unit **molecule** scenario (install + config + idempotent re-run).
- **Schema gate** `make test-vps-examples-schema` extended to cover `software`.
- `make vps-lifecycle-syntax` + a second-run idempotency check on the units.

## 10. Not in this plan

- Offboard / true revert (TASK-010).
- Full `site.yml`/`roles/common` convergence (Phase 4 only aligns; full merge is separate).
- docker_host inline→role reconciliation (noted as debt; optional, cheap-only).

## Next steps

- **Immediately doable**: approve, adjust scope, or answer §8 open decisions.
- **Blocked-on-approval**: Phase 1 implementation (needs sign-off per CLAUDE.md §1; 3+ tasks).
- **Deferrable**: Phases 3–5; the `roles/common` convergence track.
