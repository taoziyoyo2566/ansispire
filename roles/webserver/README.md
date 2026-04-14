# Role: webserver

Installs and configures **Nginx** with virtual host support, SSL/TLS, optional PHP-FPM, and security hardening. Depends on the `common` role.

## Supported Platforms

| OS Family | Distribution | Versions | Support Tier |
|-----------|-------------|---------|--------------|
| Debian | Ubuntu | 20.04, 22.04 | 1 (fully tested) |

## Requirements

- Role `common` must be applied first (declared in `meta/main.yml`).
- SSL certificates must be pre-provisioned (e.g., via certbot) before this role runs if `ssl: true`.

## Role Variables

All variables use the `webserver__` prefix.

| Variable | Default | Description |
|----------|---------|-------------|
| `webserver__nginx_version` | `"*"` | Nginx version to install (`*` = latest) |
| `webserver__worker_processes` | `auto` | Nginx worker processes |
| `webserver__worker_connections` | `1024` | Max connections per worker |
| `webserver__keepalive_timeout` | `65` | Keepalive timeout in seconds |
| `webserver__client_max_body_size` | `"16m"` | Max request body size |
| `webserver__server_tokens` | `"off"` | Hide Nginx version in headers |
| `webserver__ssl_protocols` | `"TLSv1.2 TLSv1.3"` | Allowed TLS protocol versions |
| `webserver__ssl_ciphers` | Strong ECDHE ciphers | TLS cipher suite |
| `webserver__gzip_enabled` | `true` | Enable gzip compression |
| `webserver__vhosts` | `[]` | List of virtual host definitions |

### Virtual host definition

Each entry in `webserver__vhosts` (or `nginx_vhosts` from group_vars):

```yaml
nginx_vhosts:
  - name: app.example.com        # Server name (required)
    root: /var/www/app           # Document root (required)
    ssl: true                    # Enable HTTPS redirect
    ssl_cert: /etc/ssl/certs/app.crt   # Required if ssl: true
    ssl_key: /etc/ssl/private/app.key  # Required if ssl: true
    php_fpm: false               # Enable PHP-FPM proxy
    php_fpm_socket: ""           # Required if php_fpm: true
    allowed_ips: []              # IP whitelist (empty = allow all)
```

## Dependencies

```yaml
dependencies:
  - role: common
    vars:
      common__extra_packages: [openssl]
```

## Example Playbook

```yaml
- name: Configure web servers
  hosts: webservers
  become: true
  vars:
    nginx_vhosts:
      - name: app.example.com
        root: /var/www/app
        ssl: false
        php_fpm: false
  roles:
    - role: common
    - role: webserver
```

## Tags

| Tag | Tasks |
|-----|-------|
| `nginx` | All Nginx tasks |
| `ssl` | DH parameter generation, SSL config |
| `vhosts` | Virtual host deployment |

## Testing

```bash
molecule test -s webserver
```
