# Ansispire — Ansible-based Multi-Server Management Control System

An Ansible-based reference control system split into a **data plane** (roles/playbooks) and a **control plane** (`controller/`). Built on Ansible best practices and community consensus; content is illustrative, intended for learning architectural patterns and operational techniques.

> Chinese reference snapshot: `docs/reference-cn/snapshot-2026-04-14/README.zh.md`

---

## Control Plane

`controller/` provides a **lightweight open-source control plane** that upgrades Ansible from "scripts + SSH" into a system with a real API, job history, and credential management.

Current implementation: **Semaphore + Docker Compose + BoltDB** (about 200 MB RAM).

```bash
# Quick start
cp controller/semaphore/.env.example controller/semaphore/.env
vim controller/semaphore/.env        # at minimum, change SEMAPHORE_ADMIN_PASSWORD
make controller-up                    # docker compose up -d
# Open http://localhost:3000 in a browser
```

Rationale, upgrade path, and comparison to AWX / AAP: see [`controller/README.md`](./controller/README.md).

---

## Audit Plane

Ansispire features a **decoupled audit plane** to ensure full traceability of all system actions.

- **Infrastructure**: A Python-based `relay.py` and `sink.py` architecture.
- **Reliability**: The relay supports **pagination and backfill**, ensuring that no events are lost even during relay restarts or high-load periods.
- **Heartbeat**: Includes a periodic heartbeat mechanism to verify the link between the control plane and the audit sink.
- **Data Flow**: `Semaphore API → Audit Relay → Audit Sink → JSONL Artifact`.

---

## Event-Driven Automation (EDA)

Ansispire includes a **lightweight EDA subsystem** that transforms audit events into autonomous actions.

- **Reactor Engine**: A Python-based `reactor.py` that tails the audit log.
- **Rulebook**: Configurable via `extensions/eda/rules.json`.
- **Capabilities**:
    - **Self-Healing**: Trigger Ansible playbooks or scripts when critical resources are modified.
    - **Alerting**: Forward critical events to Webhooks (Slack/Teams).
- **Security**: Actions are strictly limited to predefined commands in the rulebook.

---

## AI-Native Development

Ansispire is designed for high-efficiency AI collaboration. We use a Tiered Governance model to ensure architectural integrity while maintaining rapid iteration.

- **AI Policy**: See [`GEMINI.md`](./GEMINI.md) for the core project mandates.
- **Workflow Guide**: See [`docs/AI_WORKFLOW.md`](./docs/AI_WORKFLOW.md) for details on L0-L2 task classification and evidence-based verification.
- **Context Optimization**: `.geminiignore` is used to maintain a high signal-to-noise ratio for AI agents.

---

## Platform Support Matrix

| Tier | Platform | CI / Molecule | Notes |
|------|----------|:-------------:|-------|
| **Tier 1** | Ubuntu 20.04 / 22.04 | ✅ | Default test target |
| **Tier 1** | Rocky Linux 9 | ✅ | Verified via molecule/common |
| **Tier 2** | AlmaLinux 9 | ⚠ | Expected compatible; not yet in CI |
| **Tier 2** | Debian 11 / 12 | Not tested | Code skeleton present; expected compatible |
| **Tier 2** | AlmaLinux 8 / CentOS Stream 9 | Not tested | Code skeleton present |
| **Tier 3** | Alpine / no systemd / no Python | ❌ | Requires additional bootstrap; see `examples/` |

For Tier 3 handling, see the `raw + script bootstrap` section in `examples/advanced_patterns.yml`.

---

## Full Directory Structure

```
ansispire/
├── ansible.cfg                          # Project-level config (pure INI, no inline comments)
├── requirements.yml                     # External roles + collections dependencies
├── Makefile                             # Shortcuts for common commands
├── execution-environment.yml            # Ansible EE definition (ansible-builder)
├── .ansible-lint                        # Lint rules (profile: production)
├── .pre-commit-config.yaml              # Pre-commit checks
├── .yamllint                            # YAML style rules
├── .secrets.baseline                    # detect-secrets baseline
├── .gitignore                           # Includes vault.yml exclusion rules
│
├── .github/workflows/ci.yml             # CI: lint + syntax-check + Molecule (3 scenarios)
│
├── inventory/
│   ├── production/
│   │   ├── hosts.ini                    # Static inventory
│   │   ├── group_vars/
│   │   │   ├── all/
│   │   │   │   ├── vars.yml             # Plaintext shared vars (unified role-prefix naming)
│   │   │   │   ├── vault.yml            # Encrypted sensitive vars (excluded by .gitignore)
│   │   │   │   └── vault.example.yml   # Structural example (committable)
│   │   │   ├── webservers/vars.yml      # webserver__ prefixed vars
│   │   │   └── dbservers/vars.yml       # database__ prefixed vars
│   │   └── host_vars/web01.example.com/vars.yml
│   ├── staging/
│   └── dynamic/
│       ├── aws_ec2.yml                  # AWS EC2 dynamic inventory plugin
│       └── custom_inventory.py          # Custom dynamic inventory script
│
├── playbooks/
│   ├── site.yml                         # Main playbook
│   ├── rolling_update.yml               # Rolling-update reference template (⚠ configure vars)
│   └── vault_demo.yml                   # Vault workflow demo
│
├── examples/                            # ⚠ Teaching reference; NOT the default execution path
│   └── advanced_patterns.yml            # Full collection of advanced patterns (vars_prompt/add_host/etc.)
│
├── roles/
│   ├── common/                          # Base configuration (Tier 1: Ubuntu + Rocky)
│   │   ├── defaults/main.yml
│   │   ├── vars/os/                     # OS-specific vars (loaded via first_found)
│   │   │   ├── Debian.yml               # UFW / apt / ssh
│   │   │   ├── RedHat.yml               # firewalld / dnf / sshd
│   │   │   └── default.yml
│   │   ├── tasks/
│   │   │   ├── main.yml                 # import_tasks entry
│   │   │   ├── preflight.yml            # Tier 1/2 OS check, disk, Python
│   │   │   ├── packages.yml             # package install, users, block/rescue
│   │   │   └── security.yml             # SSH + cross-platform firewall + async upgrade
│   │   ├── handlers/main.yml
│   │   ├── templates/motd.j2            # Inline Jinja2 (no filter_plugins dependency)
│   │   └── meta/
│   │       ├── main.yml
│   │       └── argument_specs.yml
│   │
│   ├── webserver/                       # Nginx (Tier 1: Ubuntu)
│   │   ├── defaults/main.yml
│   │   ├── vars/main.yml                # Internal constants
│   │   ├── tasks/
│   │   │   ├── main.yml
│   │   │   ├── preflight.yml            # Pre-checks before vhost configuration
│   │   │   ├── install.yml
│   │   │   ├── configure.yml            # validate / blockinfile / replace
│   │   │   └── vhosts.yml               # Symlink management + unified nginx -t check
│   │   ├── handlers/main.yml
│   │   ├── templates/
│   │   │   ├── nginx.conf.j2
│   │   │   └── vhost.conf.j2
│   │   ├── files/default_index.html
│   │   └── meta/
│   │       ├── main.yml
│   │       └── argument_specs.yml
│   │
│   └── database/                        # MySQL (Tier 1: Ubuntu)
│       ├── defaults/main.yml            # Note: mysql_root_password has no default
│       ├── tasks/
│       │   ├── main.yml
│       │   ├── install.yml
│       │   └── configure.yml            # no_log / community.mysql
│       ├── handlers/main.yml
│       ├── templates/
│       │   ├── my.cnf.j2                # Primary/replica conditional rendering
│       │   └── backup.sh.j2             # Backup script template
│       └── meta/
│           ├── main.yml
│           └── argument_specs.yml       # required: true (no default; see comments)
│
├── library/app_config.py                # Custom module (JSON config management)
├── filter_plugins/custom_filters.py     # Custom Jinja2 filters
├── lookup_plugins/config_value.py       # Custom lookup plugin
├── callback_plugins/human_log.py        # Demo callback (opt-in example)
│
└── molecule/
    ├── common/      # Ubuntu 22 + Rocky 9 (Tier 1 dual platform)
    ├── webserver/   # Ubuntu 22
    └── database/    # Ubuntu 22
```

---

## Quick Start

### Prerequisites

Ansispire uses a **self-bootstrapping** workflow via a Python virtual environment to ensure toolchain consistency.

```bash
# 1. Full bootstrap (creates .venv, installs Ansible + Lint + Molecule)
make setup

# 2. (Optional) Activate the environment for ad-hoc commands
source .venv/bin/activate
```

### Vault Workflow (Option B: do not commit plaintext vault.yml)

```bash
# 1. Create a dummy or real vault password file
echo "your-password" > .vault_pass
chmod 600 .vault_pass

# 2. Copy the structural example
cp inventory/production/group_vars/all/vault.example.yml \
   inventory/production/group_vars/all/vault.yml

# 3. Encrypt
ansible-vault encrypt inventory/production/group_vars/all/vault.yml
```

### Run & Verify

```bash
# Verify project integrity
make syntax
make lint

# Run by tag
make tags TAGS=preflight,packages

# Molecule tests
make test             # Ubuntu 22 + Rocky 9 (common scenario)
make molecule-all     # All scenarios
```

---

## Core Concepts

### Variable Precedence (low to high)

```
role defaults/         ← easiest to override; use for "reasonable defaults"
inventory group_vars/  ← group-level vars (naming convention: role prefix)
inventory host_vars/   ← host-level vars
play vars:             ← vars declared directly in a playbook
role vars/             ← internal constants; higher precedence than group_vars!
task vars:             ← task-level vars (vars passed via include_role)
extra_vars -e          ← -e on the command line; highest precedence, unoverridable
```

> **Variable naming convention:** group_vars and role defaults both use the `role__*` prefix
> (e.g., `webserver__worker_processes`) to avoid the "variable looks set but is never consumed" trap.

### import_tasks vs include_tasks

| | `import_tasks` (static) | `include_tasks` (dynamic) |
|---|---|---|
| Resolution time | Compile time | Runtime |
| Tag propagation | ✅ | ❌ |
| Dynamic filename | ❌ | ✅ |
| loop support | ❌ | ✅ |

**Rule of thumb:** default to `import_tasks`; only switch to `include_tasks` when you need a dynamic filename or a loop.

### Role Argument Validation (Ansible 2.11+)

`meta/argument_specs.yml` automatically validates argument type / required / enum before a role runs.
**Note:** `required: true` cannot coexist with a default value in `defaults/main.yml` (see the comment in `roles/database/meta/argument_specs.yml`).

### Tag Conventions

```bash
ansible-playbook site.yml --tags nginx,config   # Run only the given tags
ansible-playbook site.yml --skip-tags hardening  # Skip the given tags
ansible-playbook site.yml --list-tags            # List all tags
ansible-playbook site.yml --tags upgrade         # Run tasks tagged never
```

| Tag | Meaning |
|-----|---------|
| `always` | Always runs (preflight checks) |
| `never` | Skipped by default (upgrades, destructive ops; must be triggered explicitly) |
| `preflight` | Pre-checks |
| `packages` | Package installation |
| `hardening` | Security hardening |
| `nginx` / `mysql` | Component-related |
| `verify` | Verification (read-only; safe to run alone) |

### Handler Design Principles

```yaml
# ✅ Recommended: decouple via listen; pure service operations; use FQCN everywhere
- name: Reload Nginx
  ansible.builtin.systemd:
    name: nginx
    state: reloaded
  listen: Reload Nginx   # tasks do: notify: Reload Nginx

# ❌ Avoid: putting when conditions or complex logic inside a handler
- name: Restart service
  ansible.builtin.systemd:
    name: nginx
    state: restarted
  when: some_condition   # decide whether to notify on the task side, not in the handler

# meta: flush_handlers — run queued handlers now (do not wait for play end)
- name: Force handler execution now
  ansible.builtin.meta: flush_handlers
```

### Vault Best Practices

```
vault.example.yml  ← structure description; committable
vault.yml          ← committable only after encryption; the unencrypted form is in .gitignore
```

Naming convention: prefix vault variables with `vault_` and reference them from plaintext vars.yml:
```yaml
# vault.yml (encrypted): vault_db_password: "real_secret"
# vars.yml (plaintext):  db_password: "{{ vault_db_password }}"
```

---

## Feature Reference

| Feature | Example location |
|---------|------------------|
| ansible.cfg without inline comments (INI) | `ansible.cfg` |
| Multi-environment inventory | `inventory/production/` vs `inventory/staging/` |
| group_vars directory (plaintext + vault split) | `group_vars/all/vars.yml` + `vault.example.yml` |
| host_vars host-level override | `host_vars/web01.example.com/` |
| AWS EC2 dynamic inventory plugin | `inventory/dynamic/aws_ec2.yml` |
| Custom dynamic inventory script | `inventory/dynamic/custom_inventory.py` |
| Role Argument Validation | `roles/*/meta/argument_specs.yml` |
| `required: true` with no default | `roles/database/meta/argument_specs.yml` |
| Preflight checks (Tier 1/2) | `roles/common/tasks/preflight.yml` |
| OS-specific variables (first_found) | `roles/common/vars/os/` |
| Cross-platform firewall (UFW + firewalld) | `roles/common/tasks/security.yml` |
| `strategy: free` / `linear` | `playbooks/site.yml` |
| `gather_subset` minimal facts | `playbooks/site.yml` |
| import_tasks vs include_tasks | `roles/common/tasks/main.yml` |
| loop + subelements + loop_control | `roles/common/tasks/packages.yml` |
| block / rescue / always | `roles/common/tasks/packages.yml` |
| register / changed_when / failed_when | `roles/common/tasks/security.yml` |
| async / poll asynchronous tasks (dual platform) | `roles/common/tasks/security.yml` |
| `never` tag | `roles/common/tasks/security.yml` |
| check_mode awareness | `roles/common/tasks/security.yml` |
| `ansible_managed` (no filter dependency) | `roles/common/templates/motd.j2` |
| `validate` pre-write check | `roles/webserver/tasks/configure.yml` |
| blockinfile / replace | `roles/webserver/tasks/configure.yml` |
| Unified `nginx -t` after vhost deploy | `roles/webserver/tasks/vhosts.yml` |
| Handler `listen` mechanism | `roles/webserver/handlers/main.yml` |
| `no_log` protects sensitive data | `roles/database/tasks/configure.yml` |
| Primary/replica conditional rendering (db_role) | `roles/database/templates/my.cnf.j2` |
| Backup script template | `roles/database/templates/backup.sh.j2` |
| serial + delegate_to + run_once | `playbooks/rolling_update.yml` |
| `lb_host` variable (not hardcoded) | `playbooks/rolling_update.yml` |
| Complete Vault workflow demo | `playbooks/vault_demo.yml` |
| vars_prompt / add_host / group_by | `examples/advanced_patterns.yml` |
| meta directives / throttle / environment | `examples/advanced_patterns.yml` |
| hostvars / groups magic vars | `examples/advanced_patterns.yml` |
| Built-in lookups (file/env/pipe/password) | `examples/advanced_patterns.yml` |
| uri REST API / wait_for | `examples/advanced_patterns.yml` |
| raw + script bootstrap | `examples/advanced_patterns.yml` |
| Advanced Jinja2 (selectattr/combine/json_query) | `examples/advanced_patterns.yml` |
| Custom module | `library/app_config.py` |
| Custom Jinja2 filters | `filter_plugins/custom_filters.py` |
| Custom lookup plugin | `lookup_plugins/config_value.py` |
| Demo callback (robust version) | `callback_plugins/human_log.py` |
| `ansible_managed` template header | `roles/*/templates/*.j2` |
| `delegate_to` / `run_once` | `playbooks/rolling_update.yml` |
| `until` / `retries` / `delay` polling | `playbooks/rolling_update.yml` |
| Full Ansible Vault workflow | `playbooks/vault_demo.yml` |
| Molecule (3 scenarios, dual platform) | `molecule/common/` `molecule/webserver/` `molecule/database/` |
| CI (5 jobs incl. dual-platform Molecule) | `.github/workflows/ci.yml` |
| EE definition (ansible-lint self-consistent) | `execution-environment.yml` |
| pre-commit + ansible-lint + detect-secrets | `.pre-commit-config.yaml` + `.secrets.baseline` |

---

## Common Commands

```bash
make install           # Install roles + collections
make lint              # ansible-lint
make syntax            # --syntax-check
make dry-run           # --check --diff
make deploy-staging    # Deploy to staging
make deploy-prod       # Deploy to production (requires confirmation)

# Ad-hoc
ansible all -m ansible.builtin.ping
ansible webservers -m ansible.builtin.setup -a "filter=ansible_distribution*"
ansible all -m ansible.builtin.shell -a "df -h" --become

# Run by tag
ansible-playbook playbooks/site.yml --tags preflight,packages
ansible-playbook playbooks/site.yml --skip-tags hardening

# Filter by host
ansible-playbook playbooks/site.yml --limit web01.example.com
ansible-playbook playbooks/site.yml --limit 'webservers:!web03*'

# Ad-hoc service operations
ansible webservers -m ansible.builtin.service -a "name=nginx state=restarted" --become

# Molecule (full test / debug)
molecule test -s common
molecule converge -s webserver   # Keep containers running for debugging
molecule verify -s webserver
molecule login -s webserver      # SSH into a test container
```

---

## Vault Workflow Cheatsheet

```bash
# Encrypt an entire file
ansible-vault encrypt inventory/production/group_vars/all/vault.yml

# View an encrypted file (no plaintext written to disk)
ansible-vault view inventory/production/group_vars/all/vault.yml

# Edit an encrypted file
ansible-vault edit inventory/production/group_vars/all/vault.yml

# Change the vault password
ansible-vault rekey inventory/production/group_vars/all/vault.yml

# Encrypt a single string (inlined into vars.yml)
ansible-vault encrypt_string 'MyPassword123' --name 'vault_db_password'
# Output can be pasted directly into vars.yml:
# vault_db_password: !vault |
#   $ANSIBLE_VAULT;1.1;AES256
#   66...

# Multiple vault-ids (different passwords per environment)
ansible-playbook site.yml \
  --vault-id prod@.vault_pass_prod \
  --vault-id dev@.vault_pass_dev
```

**Naming convention:** prefix all variables in a vault file with `vault_` and reference them from plaintext vars.yml:
```yaml
# vault.yml (encrypted)
vault_db_password: "SuperSecret123"

# vars.yml (plaintext)
db_password: "{{ vault_db_password }}"
```

---

## Dynamic Inventory

```bash
# Test the custom script
python inventory/dynamic/custom_inventory.py --list | python -m json.tool

# Use multiple inventory sources simultaneously
ansible-playbook site.yml -i inventory/production:inventory/dynamic

# Configure multiple sources in ansible.cfg
[defaults]
inventory = inventory/production:inventory/dynamic
```

---

## Performance Tips

| Technique | Where to configure |
|-----------|---------------------|
| Persistent SSH connection | `ansible.cfg`: `ssh_args = -o ControlPersist=60s` |
| SSH pipelining (fewer round-trips) | `ansible.cfg`: `pipelining = true` |
| Fact cache (avoid recollection) | `ansible.cfg`: `fact_caching = jsonfile` |
| Minimal facts scope | playbook: `gather_subset: [min, hardware]` |
| Parallel host count | `ansible.cfg`: `forks = 20` |
| Task scheduling strategy | playbook: `strategy: free` (when hosts are independent) |
| Disable facts on pure-config plays | playbook: `gather_facts: false` |

---

## Further Reading

- [Ansible official best practices](https://docs.ansible.com/ansible/latest/tips_tricks/ansible_tips_tricks.html)
- [Jeff Geerling's roles](https://github.com/geerlingguy) — the most widely used community reference
- [dev-sec hardening roles](https://github.com/dev-sec) — security hardening reference
- [Ansible Lint rules](https://ansible.readthedocs.io/projects/lint/)
- [Molecule docs](https://ansible.readthedocs.io/projects/molecule/)
- [Ansible Builder / EE](https://ansible.readthedocs.io/projects/builder/)
