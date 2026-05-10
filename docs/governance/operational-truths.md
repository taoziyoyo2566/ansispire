# Operational Truths

> Cross-cutting engineering invariants the project has converged on. Migrated from the former `SUMMARY.md` §4 in the 2026-05-10 docs refactor (see [`docs/reviews/refactor-docs-enterprise/plan-2026-05-10.md`](../reviews/refactor-docs-enterprise/plan-2026-05-10.md)).
>
> These are not investigations (no IVG-prefix) — they are settled decisions whose violation has caused regression in the past. New rules of this kind belong here, not in CLAUDE.md (per workspace W-R14: CLAUDE.md is methodology-only).

---

## Toolchain & runtime

- **Core Engine (2026 LTS)**: Ansible-Core 2.20.5 is the pinned baseline. Dependencies and collections are strictly locked in [`requirements.txt`](../../requirements.txt) and [`requirements.yml`](../../requirements.yml) to prevent version drift.
- **`ansible_managed` location (2.20+)**: the config-level `ansible_managed` directive is deprecated; the value lives in `group_vars/all/vars.yml` instead.
- **Python ≥ 3.9 on managed nodes**: enforced by the LTS upgrade. Ubuntu 20.04 dropped from Tier 1 support.

## Test environment

- **Environment Sensing — never assume a feature is present in containers**: roles MUST `stat` the relevant path (`/etc/ssh/sshd_config`, `/etc/cron.d`, IPv6 sysctls, etc.) before mutating it. Test containers commonly omit `openssh-server`, `cron`, and similar; assuming presence breaks Molecule scenarios silently.
- **Minimal Image Dependency**: minimal base images omit packages that the role expects (`cron`, `openssh-server`, `acl`, etc.). Install them in the Molecule `prepare` phase, not the `converge`.
- **Variable Precedence in Molecule**: use `provisioner.inventory.host_vars` in `molecule.yml` to override platform-specific limitations cleanly. Group vars and role defaults are too coarse.
- **Molecule Plugin Isolation**: the Docker driver does not inherit the local `PYTHONPATH` or `ANSIBLE_FILTER_PLUGINS`; both must be explicitly mapped in `molecule.yml` for custom filters (e.g. `ljust`) to load inside the container.

## Platform support

- **Tier 1**: Debian 12, Ubuntu 22.04+ in CI and Molecule.
- **Tier 2**: Rocky Linux 9, Alpine — skeleton tested, not first-class. Rocky 9 specifically has deep PAM entanglements in Docker that make functional role testing unreliable in containerized CI; prefer real-VM testing for RHEL-family verification.
- **Dropped**: Ubuntu 20.04 (Python baseline), Debian 11 (EOL trajectory).

## Governance

- **AI-native collaboration**: Gemini and Claude rules are integrated. See [`CLAUDE.md`](../../CLAUDE.md) and [`GEMINI.md`](../../GEMINI.md).
- **Cross-AI audit**: any multi-AI investigation must produce a peer-review and archiving trail (planning + changelog), so a future agent can reconstruct the rationale.

---
*This file replaces `SUMMARY.md` §4. Its role is to retain those settled truths in a place where they are searchable and can grow without bloating the architecture document.*
