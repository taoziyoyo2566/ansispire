# VPS Manager Plugin

`vps_manager` is a lightweight Ansispire plugin for VPS lifecycle tasks. It
processes one-shot YAML files from `runtime/inbox/vps/pending/`, runs the
matching Ansible playbook, archives a redacted copy of the task, and keeps
`runtime/state/vps_inventory.yml` as the long-lived state source.

## Safety Rules

- `ssh.managed_port` must be a non-22 high port.
- Inline passwords and inline private key material are rejected; use
  `password_env` and key file paths.
- Ansible automation uses `managed.ansible_key`; operator SSH access uses
  `managed.personal_keys` plus `local.ssh_config_identity_file`.
- A successful task is moved to `done/`; remote execution failures are moved
  to `failed/` with an adjacent `*.error.json`.
- YAML validation errors block the run before execution. Missing password
  environment variables prompt securely in an interactive terminal and block in
  non-interactive runs. The task remains in `pending/` so you can fix it and
  rerun `process`.
- A second `onboard` for an already active alias is rejected. Use `modify`
  for changes.
- Docker application exposure defaults to `127.0.0.1`; public ports require
  `expose.mode: public`.

## Runtime Layout

```text
runtime/
  inbox/vps/
    drafts/
    pending/
    processing/
    done/
    failed/
    cancelled/
    archived/
  state/
    vps_inventory.yml
    tasks/
  logs/vps_manager/
```

## Usage

Create an onboarding task with the guided generator:

```bash
make vps-new
```

The generator writes a validated YAML draft under
`runtime/inbox/vps/drafts/`, shows a summary, and lets you submit it to
`pending/`. It stores only `password_env`; bootstrap passwords are prompted
during `process` when needed and are not written to disk.
If you leave the managed user prompt empty, the generated task uses
`managed.user: ansible`.

To submit an existing draft:

```bash
make vps-submit FILE=runtime/inbox/vps/drafts/<draft>.yml
```

To inspect task state:

```bash
make vps-tasks
```

The lower-level manual flow is still available:

```bash
./plugins/vps_manager/vps_manager.py init

cp plugins/vps_manager/examples/onboard.standard.yml \
  runtime/inbox/vps/pending/jp-tokyo-01.yml

$EDITOR runtime/inbox/vps/pending/jp-tokyo-01.yml
export VPS_JP_TOKYO_01_AUTH='<set outside git>'

./plugins/vps_manager/vps_manager.py process
ssh jp-tokyo-01
```

If preflight blocks processing, fix the printed error and rerun the same
command. The pending task file is not consumed until preflight succeeds.
When `password_env` is not set and `process` is running in an interactive
terminal, the plugin prompts for the password with echo disabled, injects it
only into the current process environment for Ansible, and never writes it to
the task, inventory, archive, or log.
`password_env` is the environment variable name, not the password value. Use a
name like `VPS_JP_TOKYO_01_AUTH`.

The recommended key split is:

```bash
ssh-keygen -t ed25519 -a 100 -f ~/.ssh/ansispire_ed25519
```

```yaml
managed:
  user: ansible
  ansible_key:
    private_key: ~/.ssh/ansispire_ed25519
    public_key: ~/.ssh/ansispire_ed25519.pub
  personal_keys:
    - name: operator
      public_key: ~/.ssh/id_ed25519.pub
local:
  ssh_config_identity_file: ~/.ssh/id_ed25519
```

The Ansible private key is never uploaded. Its public key and the listed
personal public keys are installed into the managed user's `authorized_keys`.
Follow-up actions use `ansible_key.private_key`; the generated SSH alias uses
`local.ssh_config_identity_file`.

For a local lifecycle dry run that does not contact a server:

```bash
./plugins/vps_manager/vps_manager.py --no-execute --stable-seconds 0 process
```

For native Ansible syntax coverage of the action playbooks:

```bash
make vps-manager-syntax
```

## Actions

| Action | Remote | Purpose |
|---|---:|---|
| `onboard` | yes | Bootstrap a new VPS through the provider SSH port, create the managed user, handle Ubuntu `ssh.socket` when present, switch to a non-22 SSH port, apply UFW/fail2ban/security baseline, then write local inventory and SSH config. |
| `modify` | yes | Apply changes to packages, firewall ports, fail2ban, and optional network tuning. |
| `audit` | yes | Check host health and update inventory health state on success. |
| `remove` | no by default | Remove the alias from local inventory and generated SSH config. |
| `docker_host` | yes | Install Docker Engine and safe daemon defaults for a managed VPS. |
| `deploy_compose` | yes | Upload and run a Compose project, defaulting to local-only service exposure. |
