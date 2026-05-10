# Environments — Dev, Stag, Prod

> **Audience**: maintainer choosing which inventory and which Make target to invoke for a given task.
> **Source of truth**: the inventory directories themselves (`inventory/{dev,stag,prod}/`).

Ansispire follows a tiered environment model. One playbook (`playbooks/site.yml`) and one role tree (`roles/`) are applied across three inventories with different content and security posture.

---

## At a glance

| | Dev | Stag | Prod |
|---|---|---|---|
| **Inventory** | [`inventory/dev/`](../../inventory/dev/) | [`inventory/stag/`](../../inventory/stag/) | [`inventory/prod/`](../../inventory/prod/) |
| **Connection** | `local` (loopback) | SSH to staging fleet | SSH to production fleet |
| **Hosts** | `localhost` (always) | per [`inventory/stag/hosts.ini`](../../inventory/stag/hosts.ini) | per [`inventory/prod/hosts.ini`](../../inventory/prod/hosts.ini) |
| **SSH hardening** | n/a | relaxed (root + password OK) | strict (no root, no password) |
| **Log retention** | n/a | 7 days | 30 days |
| **Application debug** | n/a | `app_debug: true` | off |
| **Apply playbook** | `make deploy-dev` | `make deploy-stag` | `make deploy-prod` (prompts confirm) |
| **Hub control plane** | Path B docker stack on port 3300 | (none — staging is data-plane only) | Path A on `[hub_remote]`, port 3300 |
| **EDA self-healing** | ephemeral e2e on port 3320 (`make test-eda-e2e`) | optional | persistent |

The `env=` group var in each inventory's `[<env>:vars]` section labels the host so playbooks can branch (`when: env == 'prod'`).

---

## Dev — local development & verification

The cheapest, fastest loop. Use it for: rapid iteration on roles, EDA rule authoring, syntax fuzzing, before any remote action.

```bash
make deploy-dev-check         # dry-run, --check --diff
make deploy-dev               # apply to localhost via ansible_connection=local

# Permanent local control plane (no playbook involved)
make controller-up
make controller-bootstrap     # IaC provisioning + mints token
# Open http://localhost:3300

# Disposable EDA loopback test (cleans previous run, leaves stack up on success)
make test-eda-e2e             # → http://localhost:3320
```

Inventory file: [`inventory/dev/hosts.ini`](../../inventory/dev/hosts.ini). All hosts are `localhost` with `ansible_connection=local`, so no SSH, vault, or remote plumbing is required.

---

## Stag — pre-production parity

Mirrors the production fleet at the infrastructure level so you can verify rolling updates, firewall rules, Python interpreter availability, and orchestration ordering against real SSH hosts before they hit prod.

```bash
make deploy-stag              # ANSIBLE_HOST_KEY_CHECKING=False, --diff
```

Inventory file: [`inventory/stag/hosts.ini`](../../inventory/stag/hosts.ini). Add staging VPS aliases under `[webservers]` and `[dbservers]`. Stag-specific overrides (relaxed SSH, debug mode, shorter log retention) are in [`inventory/stag/group_vars/all/vars.yml`](../../inventory/stag/group_vars/all/vars.yml).

After deploy, verify against the staging URLs / IPs defined in your inventory; no automated post-deploy verification is wired in for stag.

---

## Prod — live management + applications

Two distinct deployment surfaces share the prod inventory.

### Control plane (the hub)

Deploys Semaphore + audit + reactor onto a node in `[hub_remote]` (or `[hub_local]` for a permanent local hub).

```bash
# 1. Vault password (one-time setup; .vault_pass is gitignored)
echo "your-password" > .vault_pass && chmod 600 .vault_pass

make hub-deploy-check HUB_NODE=remote   # dry-run
make hub-deploy       HUB_NODE=remote   # apply
# HUB_NODE ∈ {local, remote, all}; default is local (safe).
```

The hub deploy uses [`inventory/hosts.ini`](../../inventory/hosts.ini) (the physical fleet topology), not the `inventory/prod/` overlay — see [`hub-deployment.md`](./hub-deployment.md) for why.

### Data plane (web / db / app stack on the production fleet)

```bash
make deploy-prod              # prompts y/N before touching prod
```

Inventory file: [`inventory/prod/hosts.ini`](../../inventory/prod/hosts.ini). Targets real SSH aliases (e.g. `ans-hk01`). Strict security defaults are in [`inventory/prod/group_vars/all/vars.yml`](../../inventory/prod/group_vars/all/vars.yml): SSH root login disabled, password auth disabled, log retention 30 days.

### Vault management

Production secrets must be encrypted with Ansible Vault. The encrypted file is [`inventory/local/vault.yml`](../../inventory/local/) (gitignored once decrypted-then-edited; the `.example` template is tracked).

```bash
ansible-vault edit   inventory/local/vault.yml      # edit in place
ansible-vault rekey  inventory/local/vault.yml      # change password
ansible-vault view   inventory/local/vault.yml      # read-only peek
```

Per-string encryption (for embedding into a vars file):

```bash
ansible-vault encrypt_string 'MyPassword123' --name 'vault_db_password'
```

For the full vault workflow cheatsheet, see [`playbooks/vault_demo.yml`](../../playbooks/vault_demo.yml) (header comments).

---

## Automated Verification — Molecule

For deep, infrastructure-level verification (firewall, systemd, database schemas), we use Molecule. This is the **highest tier of local verification** before pushing to Stag/Prod.

```bash
make molecule-all             # Run all scenarios (common, webserver, database, full-stack)
molecule test -s <scenario>   # Run a specific scenario
```

### Troubleshooting & Common Pitfalls

During real-time research and loopback testing, the following "gotchas" were codified:

1.  **Firewall (UFW) vs. Localhost**:
    - When enabling UFW, always ensure loopback traffic is explicitly allowed: `ufw allow in on lo`.
    - Without this, internal Nginx health checks (localhost:80) or MySQL socket connections may fail with "Connection refused".
2.  **Template Headers (`ansible_managed`)**:
    - Always use the `comment` filter for the `ansible_managed` variable in config templates (e.g., `{{ ansible_managed | comment }}`).
    - Some config engines (like Nginx) treat an un-commented "Ansible managed..." string as an unknown directive, causing service start failures.
3.  **MySQL Authentication**:
    - When setting or updating the MySQL root password, use `check_implicit_admin: true`.
    - During verification stages, ensure the `mysql` CLI includes the password flag: `mysql -u root -p'{{ password }}'`.
4.  **Vhost Variable Naming**:
    - Use the canonical `webserver__vhosts` everywhere (defaults, group_vars, molecule, converge.yml). The legacy alias `nginx_vhosts` is no longer accepted.
    - When variable names diverge across `converge.yml` `vars:` and `molecule.yml` `group_vars`, preflight assertions and the actual deploy can silently iterate over different lists. Single source of truth: molecule.yml group_vars.
5.  **Custom Filter / Plugin Loading under Molecule**:
    - Molecule containers do not automatically inherit the repo-relative `filter_plugins/` path; custom Jinja filters fall back silently and produce surprising rendering.
    - Pin `ANSIBLE_FILTER_PLUGINS` (and `LOOKUP_PLUGINS`, `CALLBACK_PLUGINS`) under each scenario's `provisioner.env` so test fidelity matches production.

---

## How the playbook decides what to do

`playbooks/site.yml` is environment-agnostic. Selection happens at the `-i` flag, and the per-environment `group_vars/all/vars.yml` drives behavioral differences (security strictness, log retention, etc.). The `env` variable is the explicit hook for any task that needs to branch on environment.
