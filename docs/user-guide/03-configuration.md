# Configuration Guide

> **Audience**: anyone who needs to change a port, bump a version, manage secrets, add a remediation rule, or wire a new managed VPS.
> **Principle**: Ansispire enforces SSOT (Single Source of Truth). Each kind of config has exactly one editable file; everything else is generated.

---

## 1. The configuration map

```
config/manifest.yml                 ← Edit here: ports + image versions
   │
   ├─→ make manifest-sync           Renders into the # BEGIN/END manifest block of:
   │     │
   │     ├─→ controller/semaphore/.env       (user-edits admin/timezone; manifest block is script-managed)
   │     │
   │     └─→ controller/semaphore/.secrets   (auto-written by bootstrap: SEMAPHORE_API_TOKEN)
   │
   ├─→ controller/semaphore/bootstrap.yml    (vars_files derives semaphore_url)
   │
   └─→ playbooks/deploy_hub.yml              (vars_files lets role defaults read ports/versions)
         │
         └─→ roles/ansispire_hub/templates/semaphore_env.j2
               (writes /opt/ansispire/controller/semaphore/.env on the hub)

extensions/eda/rules.json           ← Edit here: "what event → what template"
   │
   ├─→ make test-eda-contract       L2 contract test: rule's template_name MUST exist in bootstrap
   │
   └─→ controller/audit/reactor.py  Loaded at startup; matched against events.jsonl

extensions/eda/events.schema.json   ← Edit here: declare which event fields the reactor recognizes
   │
   └─→ make test-eda-contract C9    Rule condition fields MUST be declared in this schema

inventory/hosts.ini                 ← Edit here: physical machines, who's hub, who's target
   │
   ├─→ [hub_local]    Local management nodes
   ├─→ [hub_remote]   Remote VPS management nodes
   └─→ [targets_*]    Managed VPS by OS family (next-stage expansion)

inventory/local/vault.yml           ← Edit here (encrypted): Semaphore admin password
   │
   └─→ playbooks/deploy_hub.yml vars_files (requires .vault_pass to decrypt)

inventory/{dev,stag,prod}/group_vars/all/vars.yml
                                    ← Edit here: per-environment plain-text vars (env, timezone,
                                    SSH hardening, log retention)

playbooks/remediation/*.yml         ← Edit here: actual remediation scripts (executed on targets)
```

---

## 2. Common tasks

### Change a port

Example: move Semaphore from 3300 to 3400.

```bash
$EDITOR config/manifest.yml          # set ansispire_ports.semaphore_host: 3400
make controller-down && make controller-up   # auto-resyncs .env, restarts stack
```

For Path A, the rerendered `.env` lands during the next `make hub-deploy`.

The host-port convention: **container port + 300** (avoiding IANA ports like 3306 / 5432 / 6379 / 3000). Standard protocol ports (e.g. MySQL 3306) are not project-managed and stay at their IANA defaults.

### Bump an image version

```bash
$EDITOR config/manifest.yml          # set ansispire_versions.semaphore_pinned: vX.Y.Z
make controller-down && make controller-up
```

`*_pinned` fields pin production tags. `default_tag: latest` is the fallback for fresh clones — never use `latest` in production (`docker compose` does not auto-pull, so the version freezes at first pull and never moves).

### Add a new remediation rule

```bash
# 1. Author the actual remediation playbook
$EDITOR playbooks/remediation/restart_nginx.yml

# 2. Register the corresponding Semaphore template in bootstrap.yml
#    (in the "Register remediation templates" loop)
$EDITOR controller/semaphore/bootstrap.yml
#   - name: Auto Remediation: Restart Nginx
#     playbook: playbooks/remediation/restart_nginx.yml

# 3. Add the matching rule
$EDITOR extensions/eda/rules.json
#   {
#     "name": "Remediation: Nginx Down",
#     "condition": { "description_contains": "nginx connection refused" },
#     "actions": [{ "type": "semaphore_api",
#                   "project_name": "ansispire",
#                   "template_name": "Auto Remediation: Restart Nginx",
#                   "name": "Restart Nginx" }]
#   }

# 4. The contract test enforces template_name <-> bootstrap registration
make test-eda-contract               # MUST pass before commit

# 5a. Path B: refresh the audit stack
make controller-audit-down && make controller-audit-up

# 5b. Path A: re-deploy
make hub-deploy HUB_NODE=remote
```

### Wire a new managed VPS

```bash
# 1. Set up the SSH alias on the workstation
$EDITOR ~/.ssh/config
# Host my-new-vps
#   HostName ...
#   User ...
#   IdentityFile ...

# 2. Add it to inventory/hosts.ini under the right group
$EDITOR inventory/hosts.ini
# [hub_remote]
# my-new-vps ansible_python_interpreter=/usr/bin/python3
# (or [targets_debian] if it's a managed VPS, not a hub)

# 3. Smoke-test
ansible -i inventory/hosts.ini hub -m ping

# 4. Deploy
make hub-deploy HUB_NODE=remote
```

Always pin `ansible_python_interpreter` explicitly — auto-discovery emits warnings and drifts after future Python upgrades on the target.

---

## 3. Secrets management

### Files that must NEVER reach git or rsync

| File | Holds | Protection |
|---|---|---|
| `.vault_pass` | Vault password (plaintext) | `.gitignore` line 2; rsync `--exclude=*.vault_pass` |
| `inventory/local/vault.yml` | Encrypted admin password | Encrypted; `.gitignore` `inventory/**/vault.yml` |
| `controller/semaphore/.env` | Admin password (plaintext) | `.gitignore`; rsync exclude |
| `controller/semaphore/.secrets` | Bearer API token | `.gitignore`; rsync exclude |
| `controller/audit/e2e/.env`, `.secrets` | Disposable e2e creds | `.gitignore`; rsync exclude |
| `controller/rbac/.demo_*.pw`, `users.yml` | Demo-user creds | `.gitignore`; rsync exclude |
| `<hub>:/var/lib/ansispire/state/.eda_token` | Hub-side EDA token | Outside the rsync target dir; rsync never sees it |

After a Path A `--check` you can verify no secret slipped through:

```bash
make hub-deploy-check HUB_NODE=remote 2>&1 | grep -E "\.env|\.secrets|\.demo_|users\.yml|\.eda_token"
```

The output should contain **only** `.env.example` (template). Any real secret appearing in the diff is a bug.

### Vault workflow

```bash
# First-time setup
echo "your-vault-password" > .vault_pass
chmod 600 .vault_pass

# If vault.yml does not exist yet
cp inventory/local/vault.yml.example inventory/local/vault.yml
$EDITOR inventory/local/vault.yml         # set vault_semaphore_admin_password
ansible-vault encrypt inventory/local/vault.yml

# Day-to-day
ansible-vault edit   inventory/local/vault.yml         # in-place edit
ansible-vault view   inventory/local/vault.yml         # read-only peek (no plaintext to disk)
ansible-vault rekey  inventory/local/vault.yml         # change vault password

# Encrypt a single value (paste output into a vars file)
ansible-vault encrypt_string 'MyPassword123' --name 'vault_db_password'
```

Vault password file is auto-discovered via `ansible.cfg`'s `vault_password_file = .vault_pass`. If you keep your password elsewhere, override per command (`--vault-password-file`) or per Make invocation (`make hub-deploy VAULT_PASSWORD_FILE=...`).

### EDA token rotation

There is no automatic rotation. The token is long-lived once minted. Recommended cadence: each quarter, or after any security incident.

```bash
ssh <hub>
sudo rm /var/lib/ansispire/state/.eda_token
exit
make hub-deploy HUB_NODE=remote          # mints a fresh token, restarts the audit stack
```

---

## 4. Configuration hazards

- **Do not edit on the hub directly**: the rsync `--delete` will erase any local edits inside `/opt/ansispire/`. The single exception is `/var/lib/ansispire/state/` (not under the rsync target).
- **Do not create Semaphore resources via the Web UI**: every project / inventory / template must come from `bootstrap.yml`. The UI is for inspection and one-off real-credential entry only.
- **Do not unset `become: false` in `bootstrap.yml` or `manifest_sync.yml`**: the project-wide `become = True` would silently `chown` local files to root.
- **Do not touch `/var/lib/ansispire/state/` mode**: default `0700`; loosening it exposes the EDA token to any user that can `cat` files.
- **Do not pin a manifest version to `latest`**: docker compose does not auto-pull, so once cached the version freezes. Use a real tag (`v2.18.2`).

For deeper rationale on each of these, see [`02-quickstart-eda.md`](./02-quickstart-eda.md) §11.
