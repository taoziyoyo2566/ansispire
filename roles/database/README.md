# Role: database

Installs and configures **MySQL 8.0** with primary/replica replication support, automated backups, and secure user management. Depends on the `common` role.

## Supported Platforms

| OS Family | Distribution | Versions | Support Tier |
|-----------|-------------|---------|--------------|
| Debian | Ubuntu | 22.04 | 1 (fully tested) |
| RedHat | Rocky Linux | 9 | 2 skeleton (not yet complete) |

## Requirements

- Role `common` must be applied first (declared in `meta/main.yml`).
- `database__mysql_root_password` **must** be provided via Ansible Vault — no default is intentional.

## Role Variables

All variables use the `database__` prefix.

| Variable | Default | Description |
|----------|---------|-------------|
| `database__mysql_version` | `"8.0"` | MySQL version to install |
| `database__mysql_port` | `3306` | MySQL listening port |
| `database__mysql_bind_address` | `"127.0.0.1"` | Bind address (use `0.0.0.0` for replica access) |
| `database__mysql_innodb_buffer_pool_size` | `"512M"` | InnoDB buffer pool size |
| `database__mysql_max_connections` | `150` | Max concurrent connections |
| `database__databases` | `[]` | List of databases to create |
| `database__users` | `[]` | List of MySQL users to create |
| `database__backup_enabled` | `false` | Enable automated backup cron job |
| `database__backup_dir` | `/backups/mysql` | Backup storage directory |
| `database__backup_retention_days` | `7` | Days to retain backup files |

### Host-level variable (required per host)

| Variable | Values | Description |
|----------|--------|-------------|
| `db_role` | `primary` / `replica` | Controls replication config in `my.cnf` |

### Sensitive variables (required from Vault)

| Variable | Description |
|----------|-------------|
| `database__mysql_root_password` | MySQL root password — **no default, must be vaulted** |

### Database definition

```yaml
database__databases:
  - name: myapp
    encoding: utf8mb4       # optional, default: utf8mb4
    collation: utf8mb4_unicode_ci  # optional
```

### User definition

```yaml
database__users:
  - name: appuser
    password: "{{ vault_db_app_password }}"   # always use vault reference
    priv: "myapp.*:ALL"
    host: localhost
```

## Dependencies

```yaml
dependencies:
  - role: common
```

## Example Playbook

```yaml
- name: Configure database servers
  hosts: dbservers
  become: true
  any_errors_fatal: true
  roles:
    - role: common
    - role: database
```

`host_vars/db01.example.com/vars.yml`:
```yaml
db_role: primary
```

`inventory/production/group_vars/dbservers/vars.yml`:
```yaml
database__mysql_root_password: "{{ vault_db_root_password }}"
database__databases:
  - name: appdb
    encoding: utf8mb4
database__users:
  - name: appuser
    password: "{{ vault_db_app_password }}"
    priv: "appdb.*:ALL"
    host: localhost
```

## Tags

| Tag | Tasks |
|-----|-------|
| `mysql` | All MySQL tasks |
| `database` | Database and user creation |

## Testing

```bash
molecule test -s database
```

Set `db_role: primary` in molecule host_vars (already configured).
