# Fleet key secrets — onboard managed-channel validation

This directory is bind-mounted **read-only** into the Semaphore container at
`/etc/ansispire/keys` (see `../docker-compose.yml`). It holds the fleet SSH
**private** key(s) that `playbooks/vps/onboard.yml` uses to prove managed login
works (`ssh -i /etc/ansispire/keys/<name> ...`) after cutting a host to the
managed port. Key material is gitignored and never committed.

## Operator setup

```bash
# Place the real fleet private key here (mode 600); filename is referenced by
# vps_task.managed.ansible_key.private_key as /etc/ansispire/keys/<name>.
install -m 600 ~/.ssh/vps-fleet controller/semaphore/secrets/vps-fleet-key
make controller-up   # (re)start so the read-only mount picks it up
```

## Why the same key exists in two places (Key Store + mounted file)

The one fleet keypair is referenced by the onboard flow in two distinct roles:

| Copy | Consumer | Role |
|---|---|---|
| Semaphore **Key Store** (`vps-fleet-key`) | Semaphore SSH transport | authenticates the ansible connection to the target over the bootstrap/managed channel |
| Mounted **file** (`/etc/ansispire/keys/<name>`) | `onboard.yml` `ssh -i` validation task | an independent, out-of-band managed-login check that does not go through Semaphore's own transport |

Semaphore injects the Key Store credential into the SSH transport but does not
expose it as a task-readable file path, so the explicit `ssh -i` validation
needs its own on-disk copy. They are the **same private key**, provisioned twice.

## Who can access each copy

- **Key Store**: Semaphore project members with credential access (RBAC); stored
  encrypted in the control-plane volume.
- **Mounted file**: any process inside the Semaphore container (read-only). Keep
  the host file `0600` and the host directory owner-only.

## Rotation

1. Generate a new fleet keypair; add the new **public** key to each managed host's
   `authorized_keys` (via an onboard re-run with the new `public_key_content`).
2. Replace this file **and** the Semaphore Key Store entry with the new private key.
3. Remove the old public key from hosts once the new key is proven.

## Removing the duplication later

If a future Semaphore version (or an ansible connection plugin) exposes the Key
Store credential as a task-time file path, the `ssh -i` validation can read that
path directly and this mounted copy can be dropped — collapsing to a single
source of the private key. Until then the duplication is deliberate and documented.
