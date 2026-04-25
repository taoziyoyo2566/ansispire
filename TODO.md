# Ansispire Project TODO List

## Current Phase: Functional Depth & Automation

### 🟢 Completed Tasks
- establish AI-native governance (GEMINI.md)
- mass quality refactoring (lint clean)
- zero-data-loss audit relay with pagination
- lightweight EDA reaction engine core

### 🟡 Pending / Future Tasks
- [TASK-001] **Extend Business Logic: Advanced Self-Healing**
    - Description: Create specific Ansible playbooks for automated recovery (e.g., auto-restart Nginx on failure detected via audit logs).
    - Strategy: Implement rules in `rules.json` that trigger `ansible-playbook` commands inside the `audit-reactor` container.
    - Branch: `feat/advanced-healing` (planned)

- [TASK-002] **Monitoring Integration**
    - Description: Export audit metrics to Prometheus/Grafana.

- [TASK-003] **Controller High Availability**
    - Description: Implement active-passive failover for Semaphore.
