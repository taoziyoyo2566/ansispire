# Stag Environment (Staging / Pre-production)

The Stag environment is a mirrored replica of production. It is used to validate playbooks against real remote infrastructure and network constraints without affecting the live service.

## Core Roles
- **Infrastructure Parity**: Ensures that firewall rules, Python versions, and OS dependencies match the production target.
- **Rollout Verification**: Testing rolling updates and complex orchestration before final delivery.

## Key Workflows

### 1. Baseline & Application Deployment
Applies the full-stack configuration to the staging fleet.
```bash
make deploy-stag
```

### 2. Manual Verification
Once deployed, perform manual smoke tests on the staging URLs/IPs defined in the inventory.

## Inventory Details
Located in `inventory/stag/hosts.ini`. Map your staging VPS aliases and groups here.
