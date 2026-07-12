# Operator Guide — Saberu VPS Takeover (Semaphore-native)

**What this branch delivers, and exactly how to operate it.** Follow top to bottom
and you take a fresh VPS from "bootstrap SSH only" to "fully managed + audited"
through the Semaphore control plane, without running local `ansible-playbook`.
The complete proof currently covers Ubuntu and Debian; the RHEL path remains partial.

Picture it first: the branch architecture lives in [`diagrams/`](diagrams/); the
[as-built](diagrams/as-built/) set identifies what these steps have actually proven.

---

## 0. What you get

```
   VPS Audit (baseline, root@22)  →  VPS Onboard (takeover)  →  cut to managed port
                                                                      ↓
                                        VPS Audit over managed channel = success + changed=0
```

- **VPS Audit** — read-only health (disk/memory/failed-services/reboot). No changes.
- **VPS Onboard** — creates a managed user + key + sudo, firewall (UFW), fail2ban,
  moves SSH to a non-22 managed port, then closes port 22. **This is a takeover.**
- The **gate**: after onboard, re-auditing over the managed channel must report
  `success` with `changed=0` (proves the managed state is real and idempotent).

## 1. Prerequisites

| Need | Detail |
|---|---|
| A **recoverable** VPS | Debian-family or RHEL-family. Must survive a botched run (console/VNC or reinstall). Onboard changes SSH access. |
| Bootstrap SSH | `root@22` reachable; the VPS's `root` `authorized_keys` trusts your fleet **public** key. |
| A **fleet keypair** | e.g. `~/.ssh/vps-fleet` (+ `.pub`). A passphrase is fine — Semaphore handles it internally. |
| Host tooling | Docker (for the Semaphore container). `make -C ~/workspace env-probe-check` to confirm. |

> RHEL note: onboard installs `fail2ban` from **EPEL**; the target must be able to
> reach EPEL mirrors, or `dnf` will hang. See Troubleshooting.

## 2. Bring up the control plane

```bash
cd ~/workspace/ansispire
cp controller/semaphore/.env.example controller/semaphore/.env   # set SEMAPHORE_ADMIN_PASSWORD
make controller-up            # Semaphore → http://localhost:3300  (admin / your password)
```

## 3. Bootstrap the Saberu resources (idempotent IaC)

```bash
make controller-bootstrap
```

Creates, in the `ansispire` project: `vps-fleet` (static inventory), `vps-fleet-key`
(SSH placeholder), `vps-audit-env` / `vps-onboard-env` (each carrying `ANSIBLE_CONFIG`
so runs are vault-free — see Troubleshooting), and the **`VPS Audit`** + **`VPS Onboard`**
templates (each **bound** to its environment). The post-condition assert prints
`Phase 1+2 OK ...` on success.

## 4. Inject the fleet key + trust it on the target

1. **Private key → Semaphore Key Store** (UI): Key Store → edit `vps-fleet-key` →
   paste the full contents of `~/.ssh/vps-fleet` (Login/Passphrase as needed) → Save.
   *(The agent never handles the private key; you do this.)*
2. **Public key → target** (so root@22 and, after onboard, the managed user trust it):
   ```bash
   ssh-copy-id -i ~/.ssh/vps-fleet.pub root@<TARGET_IP>
   ```

## 5. Register the target in `vps-fleet`

UI → Inventory → `vps-fleet` → edit → under `[vps_targets]` add **one** line
(start with a single host):

```ini
[vps_targets]
my-vps ansible_host=<TARGET_IP> ansible_user=root ansible_port=22
```

## 6. Set the onboard payload

UI → Environment → `vps-onboard-env` → its `json` carries `vps_task`. Set at least:

- `vps_task.managed.authorized_keys[0].public_key_content` = the contents of
  `~/.ssh/vps-fleet.pub` (the managed user's login key).
- `vps_task.ssh.managed_port` = your non-22 port (e.g. `39222`).
- `vps_task.managed.user` = e.g. `ansible`.

(Defaults come from `playbooks/vps/examples/onboard.minimal.yml`; the baked demo
host is TEST-NET/unroutable — your inventory host in step 5 is what actually runs.)

## 7. Baseline audit (optional but recommended)

UI → Task Templates → **VPS Audit** → Run. Expect `status=success` and health
output for your host over the bootstrap channel. Confirms connectivity before takeover.

## 8. Onboard (the takeover)

UI → Task Templates → **VPS Onboard** → Run. On success the host has: managed user +
key + sudo, UFW, fail2ban, SSH on the managed port, **port 22 closed**. Verify:

```bash
# from anywhere with network to the host:
nc -z <TARGET_IP> 22      && echo "22 open"    || echo "22 closed (expected)"
nc -z <TARGET_IP> 39222   && echo "managed up" || echo "managed down"
```

> Runs `strategy: free`, so with multiple hosts a slow/stuck one fails on its own
> without blocking the rest. The managed-login check runs **before** port 22 is
> closed, so a failed onboard leaves root@22 open and the host re-runnable.

## 9. Cut the inventory to the managed channel

UI → Inventory → `vps-fleet` → edit the host line to the managed user/port:

```ini
[vps_targets]
my-vps ansible_host=<TARGET_IP> ansible_user=ansible ansible_port=39222
```

## 10. The gate — re-audit over the managed channel

UI → **VPS Audit** → Run. **Required: `status=success` and `changed=0`** for the host.
That is the proof the takeover is real and the managed state is idempotent.

Automate this check any time:

```bash
make controller-vps-smoke     # runs VPS Audit, asserts success + changed=0 on every host
```

---

## Troubleshooting (hard-won)

| Symptom | Cause & fix |
|---|---|
| Task aborts at config-load: *"Could not read vault password file `.vault_pass`: Permission denied"* | The template isn't bound to an env carrying `ANSIBLE_CONFIG`. The Semaphore task runner does **not** inherit the container's env; the bound Environment's `env` must set `ANSIBLE_CONFIG=/workspace/controller/semaphore/ansible.cfg`. `make controller-bootstrap` converges this. See `controller/semaphore/README.md` "Template Authoring GOTCHA". |
| onboard hangs on a Rocky/RHEL host at *"Install fail2ban"* | The observed r9 run could not reach EPEL mirrors (`epel-release` installed, then `dnf install fail2ban` hung). Fix EPEL reachability, or disable fail2ban for that run. Passing this blocker is still required before the remaining RHEL path can be assessed. |
| managed-login validation fails right after cutover | The managed user must trust the fleet key — set `public_key_content` (step 6) to the fleet **public** key that pairs with the Key Store private key. |
| "processing"/no data on a host | fleet **private** key not in Key Store, or the target `authorized_keys` doesn't trust the fleet public key. |
| Want to undo | There is no auto-rollback. Onboard is re-runnable while root@22 is still open; a full revert (offboard) is TASK-010 (backlog). Use console/VNC if locked out. |

## References

- **Design + as-built diagrams**: [`diagrams/`](diagrams/)
- **Why/what landed (evidence)**: [`../reviews/feat-target-architecture/`](../reviews/feat-target-architecture/) — `round10`–`round13` changelogs
- **Test spec**: [`TSVS-VPS-ONBOARD-E2E-001`](../reference/test-specs/vps-onboard-managed-audit-e2e.md)
- **Playbooks**: `playbooks/vps/{audit,onboard}.yml` · **bootstrap**: `controller/semaphore/bootstrap.yml`
