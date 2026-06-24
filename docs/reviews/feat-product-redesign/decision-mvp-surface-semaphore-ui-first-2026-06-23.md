# Decision - MVP Surface Uses Semaphore UI First

**Status**: Confirmed on 2026-06-23

## Decision

For the short-term Saberu MVP, use **Semaphore UI first** as the operator
surface.

Do not start by building a new custom TypeScript web/API product shell. A custom
thin layer can be reconsidered later, after the Semaphore-native onboard/audit
loop is proven and the remaining product gaps are concrete.

## Why

The confirmed short-term target is new-VPS takeover:

1. VPS input draft
2. SSH preflight
3. Generate execution plan
4. User confirmation
5. Takeover and security baseline
6. Managed-channel validation
7. Software and service configuration
8. Validation, state recording, and audit

Most of the required MVP control-plane surface already maps to Semaphore UI:

| Saberu need | Semaphore surface |
|---|---|
| nodes and groups | Inventory |
| credentials | Key Store |
| playbooks and templates | Repositories and Task Templates |
| execution | Tasks |
| logs/history | Task logs and task history |
| scheduling | Schedules |
| API access | REST API and API tokens |
| access control | Teams/RBAC/auth surfaces |

The missing product value is not a generic dashboard. The missing value is the
correct Saberu workflow content and contracts: `vps-fleet` inventory, fleet key
handling, audit/onboard templates, payload conventions, managed-channel
validation, idempotent audit, and later AI/profile gaps.

## Official evidence checked

- Semaphore UI docs describe it as a web UI and API for automation with Ansible,
  Terraform/OpenTofu, PowerShell, Shell/Bash, and Python.
- The first-run checklist includes project setup, repositories, credentials,
  inventory, variables, task templates, tasks, schedules, RBAC, and
  notifications.
- Inventory supports file or web-edited static inventories and binds
  credentials.
- Key Store supports SSH keys, login/password credentials, vault passwords, and
  encrypted database/external secret storage options.
- Task Templates support Ansible and other task types; Tasks expose status and
  logs.
- Schedules support cron-style recurring task execution.
- API docs support API tokens and launching tasks by API.
- The public repository is MIT licensed.

References:

- https://semaphoreui.com/docs
- https://semaphoreui.com/docs/user-guide/inventory
- https://semaphoreui.com/docs/user-guide/key-store
- https://semaphoreui.com/docs/user-guide/task-templates
- https://semaphoreui.com/docs/user-guide/tasks
- https://semaphoreui.com/docs/user-guide/schedules
- https://semaphoreui.com/docs/admin-guide/api
- https://github.com/semaphoreui/semaphore

## Consequence

Near-term active work should remain in `ansispire` and execute the
Semaphore-native onboard plan:

1. run audit through Semaphore first,
2. fix onboard runtime contracts,
3. provision real onboard/audit templates,
4. complete real onboard,
5. rerun audit through the managed channel and prove `0 changed`.

## Deferred

Custom UI/API work is deferred until after the onboard/audit loop is proven and
the remaining gaps are clear. Likely future candidates:

- AI-assisted input parsing;
- plan/confirm UX around Ansible payloads;
- first-class Profile catalog;
- service relationship views;
- provider-resource planning;
- a thin API layer over Semaphore REST if the native UI becomes too awkward.
