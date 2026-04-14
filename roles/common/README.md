# Role: common

Base configuration applied to **all** managed hosts. This role is a prerequisite for all other roles.

## Supported Platforms

| OS Family | Distribution | Versions | Support Tier |
|-----------|-------------|---------|--------------|
| Debian | Ubuntu | 20.04, 22.04, 24.04 | 1 (fully tested) |
| Debian | Debian | 11, 12 | 2 (best-effort) |
| RedHat | Rocky Linux | 9 | 1 (fully tested) |
| RedHat | AlmaLinux | 8, 9 | 2 (best-effort) |

## Role Variables

All variables use the `common__` prefix to avoid conflicts.

| Variable | Default | Description |
|----------|---------|-------------|
| `common__extra_packages` | `[]` | Additional packages to install on all hosts |
| `common__timezone` | `"UTC"` | System timezone (overridden by `system_timezone` from group_vars) |
| `common__motd_enabled` | `true` | Enable MOTD template deployment |
| `common__motd_message` | `"This server is managed by Ansible."` | Custom MOTD message |
| `common__sysctl_settings` | See defaults | Dict of sysctl key-value pairs |
| `common__deploy_users` | `[]` | List of users to create with SSH keys |

### group_vars variables (required)

These are expected from `group_vars/all/vars.yml`:

| Variable | Example | Description |
|----------|---------|-------------|
| `system_timezone` | `Asia/Shanghai` | System timezone |
| `common_packages` | `[curl, vim]` | Base packages for all hosts |
| `app_base_dir` | `/opt/apps` | Application base directory |
| `app_user` | `appuser` | Application runtime user |
| `app_group` | `appgroup` | Application runtime group |
| `ssh_allowed_users` | `[deploy]` | Users allowed via SSH |
| `firewall_allowed_tcp_ports` | `[22]` | Ports to open in firewall |

### Sensitive variables (from vault)

| Variable | Description |
|----------|-------------|
| (none) | This role has no required secrets |

## Dependencies

None. This role has no dependencies on other roles.

## Example Playbook

```yaml
- name: Apply baseline to all hosts
  hosts: all
  become: true
  roles:
    - role: common
```

With custom deploy user:

```yaml
- name: Apply baseline
  hosts: all
  become: true
  vars:
    common__deploy_users:
      - name: deploy
        uid: 1001
        groups: [sudo]
        authorized_keys:
          - "ssh-ed25519 AAAA... deploy@laptop"
  roles:
    - role: common
```

## Tags

| Tag | Tasks |
|-----|-------|
| `always` | Preflight checks |
| `packages` | Package installation |
| `users` | User and group management |
| `hardening` | SSH and firewall configuration |
| `never` | OS upgrade (run explicitly with `--tags upgrade`) |

## Testing

```bash
molecule test -s common
```

Tests Tier 1 platforms: Ubuntu 22.04 and Rocky Linux 9.
