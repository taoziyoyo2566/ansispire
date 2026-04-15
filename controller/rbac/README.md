# Round 8 — RBAC + Credential Centralization

This directory holds the artifacts introduced in Round 8:

| File | Purpose |
|------|---------|
| `role-matrix.md` | Permission model: owner / manager / task_runner / guest |
| `users.yml` (generated, **gitignored**) | Random passwords for the 3 demo users |
| `.demo_*.pw` (generated, **gitignored**) | Per-user password seeds used by `ansible.builtin.password` lookup |

The bootstrap playbook (`controller/semaphore/bootstrap.yml`) seeds:
- 3 demo users (`demo_platform`, `demo_dev`, `demo_audit`) with random passwords
- An independent project `round8-rbac-demo`
- Direct user→role bindings on that project (`owner`, `task_runner`, `guest`)
- Two placeholder credentials: `ssh_lab_key` (SSH) and `vault_prod_password` (login/password)

## Running the bootstrap

```bash
# 1. Ensure Semaphore is running
make controller-up

# 2. Run the bootstrap (pass admin password from controller/semaphore/.env)
ansible-playbook controller/semaphore/bootstrap.yml \
  -e semaphore_url=http://localhost:3001 \
  -e semaphore_user=admin \
  -e semaphore_password="$(grep ^SEMAPHORE_ADMIN_PASSWORD controller/semaphore/.env | cut -d= -f2)"
```

After a successful run, `controller/rbac/users.yml` contains each demo
user's password (file mode 0600). The lookup paths (`.demo_*.pw`) are
also persisted so re-running the bootstrap is idempotent.

## API deviation from plan

Semaphore OSS v2.10.34 does not expose a `/api/teams` endpoint. This
round therefore maps conceptual teams (documented in `role-matrix.md`)
to **direct user→role bindings** on the demo project. The least-privilege
demonstration is unchanged; the shape of the binding is flatter.

If a later Semaphore version adds team support, migrate by replacing
the per-user bindings with per-team bindings in one pass — the role
matrix does not need to change.

## Importing real SSH / vault material (post-bootstrap)

Bootstrap creates **placeholder** credentials (PEM-shaped dummy private
key, literal `REPLACE_ME` password). Real material can be imported along
either of two paths — both are idempotent and both are visible to the UI
once the key reaches Semaphore's database.

### Key detection (both paths)

Semaphore reads keys from its data volume regardless of origin. The
bootstrap playbook's `when:` guard skips creation when a key with the
target name already exists, so a re-run never overwrites a key you
updated by hand. You can verify the current content type via:

```bash
curl -s -b $COOKIE $SEM/api/project/$PID/keys | \
  python3 -m json.tool
```

A placeholder key shows `"private_key": ""` and the dummy PEM body; a
real key never echoes `private_key` content back (Semaphore returns an
empty string for any read-after-write).

### SSH key (`ssh_lab_key`)

**Path A — UI import** (recommended for humans)

1. Log in to Semaphore as `admin` (or any `owner` on `round8-rbac-demo`).
2. Navigate to the `round8-rbac-demo` project → **Key Store** → `ssh_lab_key`.
3. Paste the private key (PEM) and optional passphrase.
4. Save.

**Path B — API / manual import** (scriptable; useful for CI pipelines)

```bash
SEM=http://localhost:3001
PW=$(grep ^SEMAPHORE_ADMIN_PASSWORD controller/semaphore/.env | cut -d= -f2)
COOKIE=/tmp/semaphore.cookies
curl -s -X POST $SEM/api/auth/login -H 'Content-Type: application/json' \
  -d "{\"auth\":\"admin\",\"password\":\"$PW\"}" -c $COOKIE -o /dev/null

# Resolve key id, then PUT the new content
PID=$(curl -s -b $COOKIE $SEM/api/projects | python3 -c "import sys,json; \
  print(next(p['id'] for p in json.load(sys.stdin) if p['name']=='round8-rbac-demo'))")
KID=$(curl -s -b $COOKIE $SEM/api/project/$PID/keys | python3 -c "import sys,json; \
  print(next(k['id'] for k in json.load(sys.stdin) if k['name']=='ssh_lab_key'))")

python3 - <<PY
import json, subprocess
body = {
    "id": $KID, "name": "ssh_lab_key", "type": "ssh", "project_id": $PID,
    "ssh": {"login": "ansible", "passphrase": "",
            "private_key": open("/path/to/id_ed25519").read()},
}
subprocess.run(["curl", "-s", "-b", "$COOKIE", "-X", "PUT",
                f"$SEM/api/project/$PID/keys/$KID",
                "-H", "Content-Type: application/json",
                "-d", json.dumps(body)], check=True)
PY
```

The key is stored encrypted in Semaphore's data volume
(`semaphore-data`, bound to `/var/lib/semaphore`). Removing a user from
the project's `owner` role removes their ability to read or overwrite
the key.

### Vault password (`vault_prod_password`)

1. Navigate to the project → **Key Store** → `vault_prod_password`.
2. Replace the placeholder `REPLACE_ME` with the real vault password.
3. Save.

Use this credential in templates that need `--ask-vault-pass` equivalents
by selecting it as the `secret` for the template run.

## Verifying least privilege

Round 8 §11 self-check points (see the plan). Condensed procedure:

| Step | Expected outcome |
|------|------------------|
| Log in as `demo_audit`, go to `round8-rbac-demo` | Can view templates / runs; create/edit/delete buttons greyed out or return 403 |
| As `demo_dev`, attempt to edit the demo template | 403 — `task_runner` cannot modify |
| As `demo_dev`, trigger the demo template | Succeeds (runs in check mode) |
| As `demo_platform`, edit and re-run the template | Succeeds — `owner` can do both |
| As any demo user, attempt to open the Round 7 `ansible-demo` project | No access — scoping is per-project |

## Rotating demo-user credentials

Delete `controller/rbac/users.yml` and the `.demo_*.pw` seed files, then
re-run the bootstrap. The `ansible.builtin.password` lookup will generate
fresh values. You must also rotate the Semaphore-side passwords via the
admin UI (or a future `bootstrap.yml` extension) to match.

## Cleanup (tearing down Round 8 demo state)

```bash
# Delete the 3 demo users and the demo project via admin API
# (run from the host; adjust SEMAPHORE_URL as needed)
SEM=http://localhost:3001
PW=$(grep ^SEMAPHORE_ADMIN_PASSWORD controller/semaphore/.env | cut -d= -f2)
COOKIE=/tmp/semaphore.cookies
curl -s -X POST $SEM/api/auth/login -H 'Content-Type: application/json' \
  -d "{\"auth\":\"admin\",\"password\":\"$PW\"}" -c $COOKIE -o /dev/null

for u in demo_platform demo_dev demo_audit; do
  UID_=$(curl -s -b $COOKIE $SEM/api/users | python3 -c "import sys,json; \
    print(next((u['id'] for u in json.load(sys.stdin) if u['username']=='$u'), ''))")
  [ -n "$UID_" ] && curl -s -b $COOKIE -X DELETE $SEM/api/users/$UID_
done

PID=$(curl -s -b $COOKIE $SEM/api/projects | python3 -c "import sys,json; \
  print(next((p['id'] for p in json.load(sys.stdin) if p['name']=='round8-rbac-demo'), ''))")
[ -n "$PID" ] && curl -s -b $COOKIE -X DELETE $SEM/api/project/$PID

rm -f controller/rbac/users.yml controller/rbac/.demo_*.pw
```
