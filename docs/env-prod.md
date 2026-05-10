# Prod Environment (Production)

The Prod environment represents the stable, high-security operational plane of Ansispire. It governs both the management infrastructure and the live business services.

## Architectural Distinction
- **Control Plane**: Managed via `make hub-deploy HUB_NODE=remote`. This transforms a remote VPS into an authoritative management node.
- **Data Plane**: Managed via `make deploy-prod`. This orchestrates the actual application stack (Nginx, MySQL) across the production fleet.

## Core Roles
- **Operational Excellence**: Running real-world remediation for disk space, database failovers, and service health.
- **Security Hardening**: Applying the most restrictive SSH and firewall policies (defined in `roles/common/tasks/security.yml`).

## Key Workflows

### 1. Management Hub Deployment (Path A)
Deploys the control plane (Semaphore + Audit stack) to a remote VPS.
```bash
# Set up vault password first
echo "your-password" > .vault_pass && chmod 600 .vault_pass

make hub-deploy-check HUB_NODE=remote  # Dry-run
make hub-deploy HUB_NODE=remote        # Apply
```

### 2. Application Stack Deployment
Deploys the business services (Web/DB) to the production fleet.
```bash
make deploy-prod  # Requires explicit 'y' confirmation
```

### 3. Vault Management
Always encrypt sensitive variables.
```bash
# Encrypt the vault file
ansible-vault encrypt inventory/prod/group_vars/all/vault.yml

# Edit existing secrets
ansible-vault edit inventory/prod/group_vars/all/vault.yml
```

## Inventory Details
Located in `inventory/prod/hosts.ini`. Targets real SSH aliases (e.g., `ans-hk01`).
