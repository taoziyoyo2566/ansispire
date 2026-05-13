# Vendor Patches

> External roles that have been **patched locally**. Do NOT overwrite via `ansible-galaxy install` without re-applying the fixes — the patches are required for project-level lint and FQCN compliance.
>
> Migrated from the former `SUMMARY.md` §5 in the 2026-05-10 docs refactor.

---

## Patched roles

| Role | Source | Patches applied | Why |
|---|---|---|---|
| `geerlingguy.docker` | [Galaxy](https://galaxy.ansible.com/geerlingguy/docker) | FQCN-ification of module names; octal value standardization (`mode: "0644"` over `mode: 0644`) | Project lint profile (`production`) flags non-FQCN and bare-octal as errors; upstream has not adopted these standards yet |

## Re-apply protocol

If `ansible-galaxy install -r requirements.yml --force` overwrites a patched role:

1. Identify the affected role from `ansible-galaxy list` output.
2. Re-apply the patches by hand, or revert the role directory from git history (`git checkout HEAD -- collections/ansible_collections/<vendor>/<role>/`).
3. Run `make lint` to confirm zero new violations.
4. If the patch needs to evolve (new upstream changes), update this file with the new diff summary in the table above.

## Why we do not fork

Forking the role and pinning to the fork's git URL would be cleaner long-term. We do not currently fork because:
- The patch set is small and stable.
- Upstream may adopt FQCN/octal standards in a coming release; tracking via fork would be parallel maintenance.
- The `ansible-galaxy` install path is shared with CI; switching sources adds friction.

When the patch set grows past two roles or one of these patches needs to live across a major upstream version bump, revisit and consider forking.
