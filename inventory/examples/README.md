# `inventory/examples/` — Documentation-only variable templates

**⚠ Ansible does NOT auto-load any file in this tree.**

These files exist purely as reference templates. The directory structure
intentionally mirrors `inventory/<env>/` so you can see where each example
would live if you copied it into a real environment.

---

## Why this directory exists

Ansible auto-loads any file with extension `.yml` / `.yaml` / `.json` under
`inventory/<env>/group_vars/<group>/` and `inventory/<env>/host_vars/<host>/`
— **regardless of filename**. A file named `vault.example.yml` placed there
becomes real variables (its placeholder values can silently shadow real ones
depending on alphabetical sort order, which is fragile and breaks easily).

Keeping example artifacts here, outside any `inventory/<env>/` path, removes
that risk entirely.

---

## Contents

### `group_vars/all/`

| File | What it shows |
|---|---|
| `vault.example.yml` | The shape of `vault.yml` — the 5 `vault_*` placeholders this project expects |
| `secrets_external.example.yml` | Alternative path: replace ansible-vault with HashiCorp Vault / AWS Secrets Manager / Azure Key Vault lookups |

### `host_vars/`

| Path | What it shows |
|---|---|
| `web01.example.com/vars.yml` | Per-host overrides pattern: extra vhosts + worker_connections bump |

---

## How to use

To activate any example for an environment:

```bash
# Vault (the common case)
cp inventory/examples/group_vars/all/vault.example.yml \
   inventory/<env>/group_vars/all/vault.yml
$EDITOR inventory/<env>/group_vars/all/vault.yml          # fill in real values
ansible-vault encrypt inventory/<env>/group_vars/all/vault.yml

# External secret backend (replaces vault.yml)
cp inventory/examples/group_vars/all/secrets_external.example.yml \
   inventory/<env>/group_vars/all/secrets_external.yml
# Then uncomment exactly ONE backend section inside

# Per-host overrides
cp -r inventory/examples/host_vars/web01.example.com \
      inventory/<env>/host_vars/<your-actual-host>
# Note: the dirname MUST exactly match an inventory hostname or Ansible won't apply it
```

Replace `<env>` with `dev` / `stag` / `prod`.

---

## What is NOT here

- `inventory/local/vault.yml.example` — left in place because the suffix
  `.yml.example` is **not** in Ansible's auto-load extension set, so it stays
  inert even sitting next to `inventory.ini` files. It is a legitimate
  template that happens to live alongside its consumer.

---

## Do NOT try `-i inventory/examples`

This directory has no `hosts.ini` — `ansible-inventory -i inventory/examples`
will fail. Use `inventory/dev/`, `inventory/stag/`, `inventory/prod/`, or the
SSOT `inventory/hosts.ini`.
