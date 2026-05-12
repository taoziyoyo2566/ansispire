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

# 4a. Deploy to the new host only (recommended on first add)
ansible-playbook playbooks/deploy_hub.yml \
  -i inventory/hosts.ini --limit my-new-vps \
  --vault-password-file .vault_pass --diff

# 4b. Or deploy to every host in [hub_remote]
make hub-deploy HUB_NODE=remote
```

`make hub-deploy HUB_NODE=remote` always targets every host in `[hub_remote]`; the `Makefile` does not pass `--limit`. Use 4a (raw `ansible-playbook`) when you want to land a single new node without re-running existing ones.

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

---

## 5. Backup & Restore

Ansispire's persistent state is split across three categories that need different handling. Treat them as separate backup units; do not bundle them into one tarball — encrypted material should never share storage with plaintext code.

### 5.1 What to back up

| Category | What lives there | Backup mechanism |
|---|---|---|
| **Code** | The whole working tree of this repo (`roles/`, `playbooks/`, `controller/`, `config/manifest.yml`, `inventory/hosts.ini`, ...) | git remotes — code is already version-controlled. Push regularly. |
| **Secrets** | `.vault_pass`, `inventory/local/vault.yml` (encrypted), `controller/semaphore/.env`, `controller/semaphore/.secrets`, `controller/rbac/.demo_*.pw`, `controller/rbac/users.yml` | Offline / encrypted store (password manager, hardware token, sealed backup). NEVER in git, NEVER in the same blob as code. |
| **State** | On the hub: `/var/lib/ansispire/state/.eda_token`; docker volumes `controller_semaphore-data`, `controller_audit-data` (Semaphore DB + audit `events.jsonl`) | Periodic snapshot of the volumes + state directory. |

The vault password file (`.vault_pass`) is the master key — losing it means `inventory/local/vault.yml` is unrecoverable. Treat it like any other root credential.

### 5.2 How to back up

**Secrets** (run on the workstation):

```bash
# Bundle the secret files into an offline-only tarball.
# DO NOT keep this tarball on the same disk as the repo working tree.
mkdir -p ~/secure-backups
tar czf ~/secure-backups/ansispire-secrets-$(date +%Y%m%d).tgz \
  .vault_pass \
  inventory/local/vault.yml \
  controller/semaphore/.env \
  controller/semaphore/.secrets \
  controller/rbac/.demo_*.pw \
  controller/rbac/users.yml 2>/dev/null

# Move it to your offline store (password manager attachment, encrypted USB, …).
gpg --symmetric --cipher-algo AES256 ~/secure-backups/ansispire-secrets-*.tgz
shred -u ~/secure-backups/ansispire-secrets-*.tgz    # only the .gpg survives
```

**State** (run on the hub, Path A):

```bash
ssh <hub>

# 1. Pause the audit stack so the SQLite/events files quiesce
sudo docker compose -f /opt/ansispire/controller/audit/docker-compose.yml stop

# 2. Snapshot the state dir + docker volumes
sudo tar czf /var/backups/ansispire-state-$(date +%Y%m%d).tgz \
  /var/lib/ansispire/state/

sudo docker run --rm \
  -v controller_semaphore-data:/data:ro \
  -v /var/backups:/backup \
  alpine tar czf /backup/semaphore-data-$(date +%Y%m%d).tgz -C /data .

sudo docker run --rm \
  -v controller_audit-data:/data:ro \
  -v /var/backups:/backup \
  alpine tar czf /backup/audit-data-$(date +%Y%m%d).tgz -C /data .

# 3. Resume
sudo docker compose -f /opt/ansispire/controller/audit/docker-compose.yml start
```

`docker compose stop` (not `down`) keeps containers and named volumes; only the processes pause. Resume time: < 5 s.

For **Path B** the equivalent volumes are on the workstation; substitute `controller-` for `controller_` (compose project naming) and skip the `ssh <hub>` step.

### 5.3 How to restore

Order matters — Code → Secrets → State.

```bash
# 1. Restore the working tree (fresh clone is fine; commits are in the remote)
git clone <your-repo-url> ansispire
cd ansispire

# 2. Restore secrets (decrypt the offline blob first)
gpg --decrypt ~/secure-backups/ansispire-secrets-YYYYMMDD.tgz.gpg \
  | tar xzf - -C .
chmod 600 .vault_pass
chmod 600 controller/semaphore/.env controller/semaphore/.secrets

# 3. Bring up the hub with NO existing state (Path B example)
make controller-up                    # creates fresh empty volumes
make controller-down                  # immediately stop, we need to replace volumes

# 4. Restore the docker volumes from snapshots
docker run --rm \
  -v controller_semaphore-data:/data \
  -v /path/to/backup:/backup \
  alpine sh -c 'cd /data && tar xzf /backup/semaphore-data-YYYYMMDD.tgz'

docker run --rm \
  -v controller_audit-data:/data \
  -v /path/to/backup:/backup \
  alpine sh -c 'cd /data && tar xzf /backup/audit-data-YYYYMMDD.tgz'

# 5. (Path A only) Restore the state dir on the hub
ssh <hub>
sudo tar xzf /var/backups/ansispire-state-YYYYMMDD.tgz -C /
sudo chmod 700 /var/lib/ansispire/state
sudo chown -R root:root /var/lib/ansispire/state

# 6. Start the stack against the restored data
make controller-up
make controller-audit-up
```

**Do NOT** run `make controller-bootstrap` after a state restore — it would mint a fresh API token and overwrite the restored `.secrets` / `.eda_token`. Bootstrap is for first-time provisioning only.

### 5.4 How to verify a restore

```bash
# 1. The web UI comes up and your existing admin password works
curl -s http://<hub>:3300/api/ping       # returns "pong"
# Log into the UI; check that historical projects / templates / tasks are visible.

# 2. The audit stream is intact (last event timestamp matches your snapshot time)
make controller-audit-tail | tail -5

# 3. The reactor is using the restored token (no fresh mint happened)
docker logs ansispire-audit-reactor 2>&1 | grep 'token loaded'
# Should show the same token prefix as before the restore.

# 4. Inject a synthetic event end-to-end (the 5.6 / 6.6 recipe in 02-quickstart-eda.md)
# A successful MATCH + remediation triggered means the chain is whole.
```

If step 2 shows a gap larger than your backup cadence, you lost events during that window — note for incident response.

### 5.5 Backup hazards

- **Never put `.vault_pass` and `vault.yml` in the same storage location.** That defeats the encryption. Keep the password in a password manager, the encrypted file in any storage that you control.
- **Never commit any of the §5.1 Secrets category to git** — even on a private remote. Once pushed, history is forever.
- **Plain-text `.env` is a credential.** Treat backups of it with the same care as the vault.
- **State snapshots include the API token in `.eda_token`.** Anyone who can read the snapshot can replay against your Semaphore. Encrypt at rest.
- **Retention**: keep at least the last 3 snapshots offsite. If a corruption goes undetected for a week, you need a pre-corruption copy to restore from.
- **Test restores quarterly.** A backup you have never restored is not a backup.
