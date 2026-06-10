---
name: env-sync
description: Probe this host's environment capabilities and sync them into the per-host registry (.agents/env/<host>.yml). Use at session start on a new/changed machine, when env-probe-check reports stale, or whenever a command unexpectedly fails with "not found" / daemon errors.
---

# env-sync — refresh the per-host capability registry

## When to run

- First session on a machine (no `.agents/env/<hostname -s>.yml` yet)
- `make env-probe-check` (or the SessionStart hook) reports missing/stale
- Any mid-session capability surprise: `command not found`, docker daemon
  unreachable, auth failure on a capability the registry lists as available

## Steps

1. Run the probe (this is the single source of probe logic — do not re-implement
   probes inline):

   ```bash
   make env-probe
   ```

2. Read the generated `.agents/env/$(hostname -s).yml` and compare with the
   previous version (`git diff .agents/env/`). Report deltas to the user —
   especially capabilities that flipped (available ↔ absent), since stale plans
   or memories may depend on the old state.

3. If a capability needed by the current task is **absent**, classify before acting:
   - **Project-local fix** (safe to do now): `ansible-galaxy` collection install,
     venv creation, `make setup` / `make install`. Do it, then re-run `make env-probe`.
   - **System-level install** (docker, apt/yum packages, daemons): do NOT install
     automatically. Propose the exact install command to the user and record the
     gap + fallback in your report. The registry's `host_overrides` already note
     the degraded path.

4. If any flipped capability contradicts an agent memory file or an active plan's
   pre-conditions, update that record in the same round
   (`.agents/rules/environment-truth.md` same-round correction).

5. Commit the registry change with the next docs commit (it is tracked precisely
   so other machines can see it).

## Notes

- Task→command mapping SSOT is `docs/governance/testing-governance.md §3–§4`;
  the registry only carries host-conditional overrides.
- TTL default is 7 days (`ENV_PROBE_TTL_DAYS` to override). Freshness is a floor,
  not a guarantee — surprises always trigger re-probe regardless of age.
