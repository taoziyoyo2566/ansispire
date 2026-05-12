# Installation Guide

> **Audience**: anyone setting up Ansispire for the first time, on a clean control node.
> **Outcome**: by the end you will have a working control plane (Semaphore web UI), an audit + reactor stack, and a verified self-healing loop.
>
> For the deep "why does it work this way" explanation see [`02-quickstart-eda.md`](./02-quickstart-eda.md). For maintainer command speed-look-up see [`../operations/eda-core.md`](../operations/eda-core.md).

---

## 1. Prerequisites

### Control node (the machine you run `ansible-playbook` on)

- Linux: Ubuntu 22.04+ or Debian 12 recommended.
- Python: ≥ 3.10 (`python3 --version`).
- Docker Engine ≥ 24 + the Compose plugin (`docker compose version`).
- Standard tools: `git`, `curl`, `jq`, `rsync`, `acl`, `gnupg2`.
- Outbound network access to: Galaxy (`galaxy.ansible.com`), Docker Hub or your container registry, and (Path A only) SSH to the target VPS.

### Managed nodes (the servers Ansispire will deploy to)

- Python ≥ 3.9 (Ansible's managed-node baseline since the 2026 LTS upgrade).
- SSH reachable from the control node, with key auth set up.
- Tier 1: Debian 12, Ubuntu 22.04+. Tier 2 (skeleton support): RHEL/Rocky 9, Alpine.

Versions of Ansible Core and the collection set are pinned — see [`requirements.txt`](../../requirements.txt) and [`requirements.yml`](../../requirements.yml). Do not mix-and-match; the [`execution-environment.yml`](../../execution-environment.yml) is the source of truth.

---

## 2. One-shot setup

```bash
git clone <your-fork-or-this-repo>.git
cd ansispire
make setup        # creates .venv, installs Ansible + collections + roles
source .venv/bin/activate
```

`make setup` is idempotent — re-run any time dependencies change.

Sanity:

```bash
make verify       # ansible-lint + syntax-check + EDA test pyramid + dry-run
```

If `make verify` fails, fix it before going further. Common causes: missing `.vault_pass` (see §4), missing Docker daemon, or stale Galaxy collections (`ansible-galaxy collection install -r requirements.yml --force`).

---

## 3. Choose a deployment path

Ansispire ships **two** entry points. Pick one based on what you are doing today.

| | Path B — local dev stack | Path A — real deployment |
|---|---|---|
| **Where it runs** | docker-compose on your workstation | Ansible role onto a remote VPS (or `localhost`) |
| **Use when** | you are exploring, writing rules, or running e2e tests | you are deploying the hub for production / persistent use |
| **Persistence** | ephemeral; `make controller-reset` wipes everything | persistent; survives reboots; deploys are idempotent |
| **Port** | 3300 (or 3320 for the disposable e2e stack) | 3300 on the hub host |
| **Secrets** | `controller/semaphore/.env` (gitignored) | encrypted `inventory/local/vault.yml` + `.vault_pass` |
| **Entry command** | `make controller-up && make controller-bootstrap` | `make hub-deploy HUB_NODE={local\|remote\|all}` |

Most first-time users should start with **Path B** to verify the setup, then switch to Path A to put the hub somewhere permanent.

---

## 4. Path B — local dev stack (recommended first run)

```bash
# 1. Set the admin password
cp controller/semaphore/.env.example controller/semaphore/.env
$EDITOR controller/semaphore/.env       # set SEMAPHORE_ADMIN_PASSWORD

# 2. Stand up the control plane
make controller-up                       # docker compose up -d (auto-runs manifest-sync)

# 3. IaC bootstrap: registers project, templates, mints the API token
make controller-bootstrap

# 4. Start the audit + reactor stack
make controller-audit-up
```

Visit <http://localhost:3300> and log in with `admin` and the password from `.env`.

End-to-end self-healing demo (disposable, port 3320):

```bash
make test-eda-e2e
```

Expected: exits zero in ~60 s. Stack stays running for inspection (cleanup with `cd controller/audit/e2e && docker compose -p ansispire-e2e down -v`).

To tear down Path B fully:

```bash
make controller-audit-down
make controller-down
make controller-reset                    # only if you want to wipe the database
```

---

## 5. Path A — real deployment

This deploys the same hub onto a real machine via Ansible role (`ansispire_hub`). Works against either:

- the workstation itself (`HUB_NODE=local`, useful for a permanent local hub on a dedicated host), or
- a remote VPS (`HUB_NODE=remote`), or
- both (`HUB_NODE=all`).

### 5.1 Configure the vault

```bash
# 1. Vault password file (gitignored)
echo "your-vault-password" > .vault_pass
chmod 600 .vault_pass

# 2. If inventory/local/vault.yml does not exist yet, copy from the example
cp inventory/local/vault.yml.example inventory/local/vault.yml
$EDITOR inventory/local/vault.yml         # set vault_semaphore_admin_password
ansible-vault encrypt inventory/local/vault.yml

# Or, if it already exists:
ansible-vault edit inventory/local/vault.yml
```

### 5.2 Add the target host to the inventory

Open [`inventory/hosts.ini`](../../inventory/hosts.ini). The relevant groups for hub deployment are:

```ini
[hub_local]
control_node ansible_connection=local ansible_python_interpreter=/usr/bin/python3

[hub_remote]
ans-hk01 ansible_python_interpreter=/usr/bin/python3.13
# my-new-vps ansible_python_interpreter=/usr/bin/python3   # add here

[hub:children]
hub_local
hub_remote
```

Always set `ansible_python_interpreter` explicitly — auto-discovery is fragile and drifts after future Python upgrades on the target. Hosts in `[hub_remote]` must be reachable as the SSH alias listed (configure `~/.ssh/config` first).

Smoke-test connectivity:

```bash
ansible -i inventory/hosts.ini hub -m ping
```

### 5.3 Dry-run, then deploy

```bash
make hub-deploy-check HUB_NODE=remote     # --check --diff, no changes
make hub-deploy       HUB_NODE=remote     # apply
```

The dry-run **must not** show any of the following in the rsync diff (they would indicate a leak from the workstation):

- `.claude/`, `.ansible/`, `__pycache__/`
- `controller/rbac/.demo_*.pw`, `controller/rbac/users.yml`
- `controller/semaphore/.env`, `.secrets`
- `*deleting .eda_token`

If any of those appear, **stop** and review the rsync exclude list in `roles/ansispire_hub/tasks/main.yml`.

A successful first deploy takes 3-5 minutes and ends with the hub URL printed.

### 5.4 Verify on the target

```bash
ssh ans-hk01

docker ps | grep ansispire-                          # all containers up
docker logs ansispire-audit-reactor 2>&1 | head -20  # reactor loaded N rules

# Inject a synthetic Disk Full event
docker exec ansispire-audit-sink sh -c 'printf "%s\n" \
  "{\"payload\":{\"event\":{\"object_type\":\"task\",\"description\":\"Disk Full on remote\"}}}" \
  >> /var/log/semaphore/events.jsonl'

docker logs --tail 50 ansispire-audit-reactor        # MATCH then triggered task id
```

### 5.5 Re-deploy / upgrade

`ansispire_hub` is idempotent. `make hub-deploy HUB_NODE=...` again:

- skips already-installed packages,
- skips already-created users,
- rsyncs only changed files,
- preserves the existing `.eda_token` (no re-mint needed unless you delete it).

---

## 6. Where to go next

- **Day-2 operations** (commands you will run repeatedly): [`eda-core.md`](../operations/eda-core.md), [`hub-deployment.md`](../operations/hub-deployment.md).
- **Adding new self-healing rules**: see [`03-configuration.md`](./03-configuration.md) §2 ("Common tasks").
- **Backing up / restoring state, secrets, and the audit stream**: [`03-configuration.md`](./03-configuration.md) §5.
- **Per-environment differences** (dev / stag / prod): [`environments.md`](../operations/environments.md).
- **Architecture rationale**: [`ARCHITECTURE.md`](../../ARCHITECTURE.md).
- **When something breaks**: [`04-troubleshooting.md`](./04-troubleshooting.md).
- **Deep "why does it work this way" walkthrough**: [`02-quickstart-eda.md`](./02-quickstart-eda.md) (ZH, long-form).
