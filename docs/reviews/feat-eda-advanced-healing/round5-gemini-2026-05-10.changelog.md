# Round 5 — Molecule Loopback Hardening (Gemini, 2026-05-10)

> **Reference**: this round was executed by an external agent (Gemini) on
> branch `feat/eda-advanced-healing`. It is unrelated to the EDA topic that
> rounds 1–4 cover; it landed on the same branch by convention. Round 6
> follows up with corrections (see `round6-2026-05-10.changelog.md`).

## Scope

Real-loop testing of the four Molecule scenarios (`common`, `webserver`,
`database`, `full-stack`) on Ubuntu 22.04 / Debian 12, plus root-cause
analysis and remediation of every failure surfaced.

Level: **L1.5 Investigation + L1 Engineering** (per project §1).

## File change manifest

| File | Change | Summary |
| :--- | :--- | :--- |
| `roles/common/tasks/security.yml` | edit | New task: `ufw allow in on lo` (loopback exempt) |
| `roles/database/tasks/configure.yml` | edit | `mysql_user`: add `check_implicit_admin: true`, explicit `login_user`/`login_password` |
| `roles/database/templates/my.cnf.j2` | edit | `{{ ansible_managed }}` → `{{ ansible_managed \| comment }}` |
| `roles/webserver/templates/nginx.conf.j2` | edit | same as above |
| `roles/webserver/templates/vhost.conf.j2` | edit | same as above |
| `roles/database/meta/argument_specs.yml` | edit | Escape Jinja in description string (over-escaped — see round 6) |
| `molecule/common/molecule.yml` | edit | Pin `ansible_managed` to deterministic format string |
| `molecule/database/molecule.yml` | edit | Add `provisioner.env` (plugin paths + warning suppression); inject `database__mysql_root_password`; pin `ansible_managed`; enable `common_auto_provision_targets` |
| `molecule/database/verify.yml` | edit | `mysql -u root` now passes `-p'{{ database__mysql_root_password }}'` |
| `molecule/full-stack/molecule.yml` | edit | Same env / pinned vars; rename `nginx_vhosts` → `webserver__vhosts`; **remove `published_ports`** (verify runs in-container, host port mapping no longer needed) |
| `molecule/full-stack/verify.yml` | edit | New `appdb` existence assertion; `my.cnf` path corrected to `/etc/mysql/mysql.conf.d/mysqld.cnf`; service-key check tolerates `nginx` and `nginx.service` shapes |
| `molecule/webserver/molecule.yml` | edit | Same env/pinned vars; add `webserver__vhosts` to group_vars |
| `Makefile` | edit | `molecule-all` now also runs `full-stack` scenario |
| `docs/operations/environments.md` | edit | New "Automated Verification — Molecule" section with troubleshooting list |

## Bugs found and resolved

| Bug | Root cause | Resolution | Severity |
| :--- | :--- | :--- | :--- |
| **UFW breaks intra-host loopback** | UFW default-deny incoming + `lo` not explicitly allowed; nginx self-checks and MySQL socket connections fail with "Connection refused" | New `ufw allow in on lo` task in `roles/common/tasks/security.yml` | **High** (production-impacting) |
| **Nginx fails to start with `ansible_managed` header** | Default `ansible_managed` is plain text; nginx parses "Ansible managed..." as an unknown directive | `{{ ansible_managed \| comment }}` in `nginx.conf.j2`, `vhost.conf.j2`, `my.cnf.j2`, `backup.sh.j2` | **Medium** |
| **MySQL root password idempotency** | First run sets root via empty-password socket; second run lacks credentials; race between socket auth and the password being set | `check_implicit_admin: true` + explicit `login_user`/`login_password` | **High** (re-run safety) |
| **Variable name divergence** | `nginx_vhosts` legacy name still used in some test inventories; `defaults/main.yml` and tasks already moved to `webserver__vhosts` | Rename in `molecule/full-stack/molecule.yml` group_vars (round 6 also cleans up `molecule/webserver/converge.yml` + `preflight.yml` fallback) | **Low** (config consistency) |
| **Custom Jinja filters not loaded under Molecule** | Molecule containers do not inherit the repo-relative `filter_plugins/` path; custom filters fall back silently | Set `ANSIBLE_FILTER_PLUGINS`/`LOOKUP_PLUGINS`/`CALLBACK_PLUGINS` in each scenario's `provisioner.env` | **Medium** (test fidelity) |

## Test methodology

1. **Static gates**: `ansible-lint --profile production` + `ansible-playbook --syntax-check` against both `inventory/stag` and `inventory/prod`.
2. **Black-box**: Docker containers running systemd (`geerlingguy/docker-ubuntu2204-ansible`).
3. **Assertion-based**: `ansible.builtin.assert` + `uri` + `wait_for` checks for physical state (port listening, HTTP responses, DB schema present).
4. **Integration**: `full-stack` scenario verifies nginx and mysql co-exist on a single host without resource contention.

## Results

- All four Molecule scenarios pass on Ubuntu 22.04 (`common` additionally tested on Ubuntu 20.04 + Debian 12).
- Idempotency: second run produces zero changes.
- Service co-existence verified.

## NOT done in this round (deferred to round 6)

- `argument_specs.yml` Jinja escape used a heavyweight pattern (`'{{ '{{' }} ... {{ '}}' }}'`); should be `{% raw %}…{% endraw %}` or backticks.
- `scripts/verify_report.py` retained `.venv/bin/` hardcoded prefix and hardcoded `✅ PASS` rows — fixed/removed in round 6.
- `molecule/full-stack/verify.yml` `fail_msg` was stripped of debug context to dodge an undefined-variable risk; should use `default()` instead.
- `molecule/webserver/converge.yml` still defines `nginx_vhosts` (different content from the molecule.yml group_vars `webserver__vhosts`); cleaned up in round 6.
- `roles/webserver/tasks/preflight.yml` fallback `{{ nginx_vhosts | default(webserver__vhosts) }}` is dead code once converge is aligned.
- New root-level `ANSISPIRE_TEST_REPORT.md` and `DOCS_AUDIT_REPORT.md` violated the docs-refactor decision (CHANGELOG already removed snapshot reports). Resolved in round 6 by deleting the script + report and folding this audit into the present file.

## CLAUDE.md updates (this round)

None.
