# Dev Environment (Development & Local Prototyping)

The Dev environment provides a safe, low-cost sandbox for rapid iteration and logic verification.

## Development States
- **Ephemeral (Loopback)**: Verifies the "Event-Driven" logic without persistent state. Perfect for testing new reactor rules.
- **Persistent (Local Hub)**: Runs a full management node on the workstation for UI configuration and long-term testing.

## Core Roles
- **Full-stack Logic**: Validating the end-to-end orchestration of `site.yml` on the local machine before any remote interaction.

## Key Workflows

### 1. EDA Self-Healing Test (Ephemeral)
Verifies the complete loop: Event -> Reactor -> API -> Semaphore -> Playbook.
```bash
make test-eda-e2e
```
*Note: This starts a temporary stack on port 3320 which remains active for manual inspection after completion.*

### 2. Full-stack Dev Deployment (Persistent)
Applies the main application logic to your local workstation using `connection: local`.
```bash
make deploy-dev-check  # Dry-run
make deploy-dev        # Apply
```

### 3. Local Control Plane (Docker Compose)
Runs the persistent management hub on your workstation.
```bash
make controller-up
make controller-bootstrap
# Access at http://localhost:3300
```

## Inventory Details
Located in `inventory/dev/hosts.ini`. Uses `ansible_connection=local` to ensure no SSH dependencies for local dev work.
