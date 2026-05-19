# Plan — Round 7: rsync preflight UX (cross-compare follow-up)

> **Status**: DRAFT — awaiting user approval
> **Created**: 2026-05-19
> **Branch**: `fix/codex-cross-compare-hygiene` (continues Round 6)
> **Parent plan**: [`plan-2026-05-17.md`](./plan-2026-05-17.md) — this is an ad-hoc round, not one of the original 7 WUs. Round 6 changelog Follow-Up explicitly listed it as deferrable.

---

## §0. Pre-Execution Checklist

### A. Intent Clarification
- **System type**: ① engineering improvement (UX) — not a correctness fix; the underlying `ansible.posix.synchronize` already fails on missing rsync, just with a cryptic stderr.
- **Boundaries**: `roles/ansispire_hub/tasks/main.yml` only. No other roles, playbooks, or compose files touched.
- **NFR priorities**: maintainability (≤ 4 tasks added) > diagnosability (clear actionable `fail_msg`) > scalability (n/a) > cost (n/a).
- **Authorization**: implement after this plan is approved. No remote SSH actions; only local edits + dry-run.

### B. Level Declaration
**[L1] Engineering** — single-role refactor. Workflow: Strategy → Act → Verification. No architecture review needed.

### C. Cost Budget
- **Plan + implement + verify + changelog**: small (< 30 min).
- No usage-limit risk.

### D. Framework Best-Practice Pre-Check (W-R18)

| Direction | Source consulted | Conclusion |
|---|---|---|
| `ansible.posix.synchronize` failure surface | Real-world: rsync exit 12 / "command not found" comes through as `msg: "Warning: Permanently added 'host'..." + cryptic stderr` | ⚠ confirmed: failure mode is opaque. Preflight is a legitimate UX improvement. |
| Best way to probe "is binary available" in Ansible | Ansible docs: `ansible.builtin.command` searches `PATH`; returns `Could not find the requested executable` with explicit module-level error when absent. | ✅ `ansible.builtin.command: rsync --version` is the canonical probe — clearer than `stat` on hardcoded paths because it works on macOS Homebrew (`/usr/local/bin/rsync`), Alpine `/usr/bin/rsync`, Debian `/usr/bin/rsync`, etc. without hard-coding. |
| Hardcoded-path `stat` (Codex's approach) | Codex's `fix/ansible-docs-review-remediation` branch — stats `/usr/bin/rsync` + `/bin/rsync` then asserts | ⚠ portable on Linux VPS, but conflates "binary exists at fixed path" with "binary is usable". Misses non-FHS paths. Diagnostic `fail_msg` is the only real benefit. |
| Sudo-availability preflight | Codex's task 5: `sudo -n test -x /usr/bin/rsync` | ⚠ unnecessary here. `deploy_hub.yml` already sets `become: true` at play level (line 6); the **remote** preflight runs with become, so if sudo's broken the remote preflight fails with sudo's own (already clear) error. |

**Conclusion**: direction matches Codex's intent (preflight is the right UX fix) but **the binary check should be done via `ansible.builtin.command: rsync --version`, not hardcoded `stat` paths.** Plan body may proceed.

---

## §1. Purpose / Scope / Out-of-Scope

### Purpose
When `ansible.posix.synchronize` runs without `rsync` on either side, the failure surface is opaque:
- Missing on controller: `Failed to find required executable "rsync"` (Ansible-level — already clear).
- Missing on remote: `rsync error: error in rsync protocol data stream (code 12)` (cryptic).

Add a preflight that fails *fast* with a `fail_msg` pointing operators at the install command.

### Scope (in)
- Add 4 tasks to `roles/ansispire_hub/tasks/main.yml`, inserted between the "Ensure state directory" task and the "Hub | Sync Code" task:
  1. Probe rsync on controller (`delegate_to: localhost`)
  2. Assert controller probe succeeded (with install-hint fail_msg)
  3. Probe rsync on remote target
  4. Assert remote probe succeeded (with install-hint fail_msg)

### Scope (out)
- Codex's task 5 (sudo preflight) — see §0-D, redundant.
- Codex's hardcoded `/usr/bin/rsync` + `/bin/rsync` stat paths — replaced by `command -V`-style probe.
- Codex's other branch divergences (Dockerfile ARG, pyproject 3.11→3.12, audit test rewrites, bootstrap_preflight removal) — explicitly **NOT** in scope. Round 6 already documented refusal of the ARG pattern; pyproject pin is a separate decision; bootstrap_preflight removal contradicts our WU-4 commit `d179fac`.

### Judgment Criteria
- Round 7 lands cleanly when:
  1. `ansible-lint --offline --profile production roles/ansispire_hub/tasks/main.yml` → pass.
  2. `ansible-playbook playbooks/deploy_hub.yml --syntax-check` → pass.
  3. `ansible-playbook playbooks/deploy_hub.yml --check --connection=local --inventory inventory/local/` → the new tasks appear in the dry-run plan in the right order.
  4. **Negative case**: simulate missing rsync (controller side, via `PATH=/tmp ansible-playbook --check …` OR by overriding `command` to point at a nonexistent path) → the new `assert` task fires with the actionable `fail_msg`.

---

## §2. Current-State Assessment

- `roles/ansispire_hub/tasks/main.yml:38-72` — single `Hub | Sync Code` task with full `rsync_opts` exclude list. No preflight.
- `infra_baseline/tasks/main.yml:23-31` installs rsync on the Debian path of the target, but `infra_baseline` runs as a **separate play** in `deploy_hub.yml`. RHEL/Alpine paths in `infra_baseline` are still stubbed (TASK-007 backlog) — so on those families, rsync is **not** auto-installed. Preflight is genuinely useful.
- Controller-side rsync is not auto-managed by Ansispire at all; assumed pre-installed on the workstation. Preflight catches macOS-with-no-Homebrew-rsync, fresh Debian without `rsync`, etc.

---

## §3. Decision Rationale

### Why `command: rsync --version` (not Codex's `stat /usr/bin/rsync`)

| Aspect | `command: rsync --version` | `stat /usr/bin/rsync + /bin/rsync` |
|---|---|---|
| Works on macOS Homebrew | ✅ | ❌ (rsync is `/usr/local/bin/rsync` or `/opt/homebrew/bin/rsync`) |
| Works on Alpine | ✅ | ✅ (`/usr/bin/rsync`) |
| Works on Debian/RHEL | ✅ | ✅ (`/usr/bin/rsync`) |
| Confirms binary is **usable**, not just present | ✅ (actually invokes it) | ⚠ stat checks `+x` but not whether `--version` runs |
| Diagnostic message on failure | Generic Ansible "command not found" | Custom `fail_msg` — better |
| Task count | 4 (probe + assert × 2) | 5 (stat + assert + sudo-probe) |

Combine the strengths: use `command: rsync --version` for the **probe** (so it works on non-FHS layouts and confirms usability), and pair it with an `assert` that has a rich `fail_msg` (so operators get the actionable hint). Best of both.

### Why insert before "Hub | Sync Code", inside the existing `Hub | Initialize Environment` block

- The block already handles "ensure everything is ready before the first mutating step" — preflight fits the block's intent.
- Keeps `become: true` from the play-level setting in effect for the remote probe → also implicitly validates sudo.
- Failure aborts before any directory mutation, which is the right behavior.

---

## §4. File-level changes (proposed)

### `roles/ansispire_hub/tasks/main.yml`

Insert after line 36 (after "Hub | Ensure state directory"), before line 38 ("Hub | Sync Code"):

```yaml
    - name: Hub | Preflight - rsync available on controller
      ansible.builtin.command:
        cmd: rsync --version
      delegate_to: localhost
      become: false
      changed_when: false
      check_mode: false
      register: ansispire_hub_local_rsync_probe
      failed_when: false

    - name: Hub | Preflight - assert rsync on controller
      ansible.builtin.assert:
        that:
          - ansispire_hub_local_rsync_probe.rc == 0
        fail_msg: >-
          ansible.posix.synchronize requires rsync on the Ansible controller (localhost).
          Install: apt install rsync (Debian/Ubuntu) / brew install rsync (macOS) /
          apk add rsync (Alpine).
        quiet: true

    - name: Hub | Preflight - rsync available on target
      ansible.builtin.command:
        cmd: rsync --version
      changed_when: false
      check_mode: false
      register: ansispire_hub_remote_rsync_probe
      failed_when: false

    - name: Hub | Preflight - assert rsync on target
      ansible.builtin.assert:
        that:
          - ansispire_hub_remote_rsync_probe.rc == 0
        fail_msg: >-
          ansible.posix.synchronize requires rsync on {{ inventory_hostname }}.
          Run 'make hub-baseline HUB_NODE={{ inventory_hostname }}' first
          (the infra_baseline role installs rsync via the OS package manager),
          or install manually: apt install rsync.
        quiet: true
```

That's the only edit. **No other file in this round.**

### Sync Guard sweep (after the implementation)

Per CLAUDE.md §0:
1. `ARCHITECTURE.md` — no change (no new contract).
2. `README.md` — no change (no operator-visible CLI change).
3. `docs/reference/feature-map/hub-deployment.md` — one-line addition under "Lifecycle" or "Operator Diagnostics" noting the preflight tasks.
4. `CHANGELOG.md [Unreleased]` — add a one-line entry under the Round 6 cross-pollination block: *"Round 7 follow-up: rsync preflight on controller + target with diagnostic fail_msg."*
5. `docs/reference/feature-map/INDEX.md` — no change (no scope shift).

---

## §5. Phased roadmap (n/a)

Single-task round. No phasing needed.

---

## §6. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Preflight noise on every deploy (4 extra tasks) | Acceptable — they're `changed_when: false`, so PLAY RECAP shows changed=0; they only add ~1–2 s. |
| `rsync --version` requires reading version output, which writes to stdout — does `ansible.builtin.command` capture it? | Yes, captured in `register`. No issue. |
| `become: false` on the local probe but `become: true` from play level on remote — does ansible-lint complain? | Allowed pattern; lint accepts `become: false` when explicit. Will verify in Gate 2. |
| Negative-case verification on the controller side breaks the actual workstation | Use a throwaway test inventory + override `command:` to point at a missing binary OR run the assert against a synthesised failed register — see §1 Judgment Criteria #4 for the safer simulation approach. |

---

## §7. Acceptance / Closure

- All 4 judgment-criteria items pass.
- Changelog `round7-2026-05-19.changelog.md` lands with Gate 1/2/3 evidence and Sync Guard sweep.
- TODO.md's "📌 当前分支可发 PR" block has its Round 7 status reflected.

---

## §8. Out-of-band

This plan is **subordinate** to `plan-2026-05-17.md` (the 7-WU parent). Per workspace W-R10, all rounds for this topic stay inside `docs/reviews/feat-semaphore-cross-compare/`; the parent plan does not need to be edited (this is captured as an ad-hoc deferred-from-Round-6 item, mentioned in Round 6 Follow-Up).
