# Feature: Nginx Auto-Remediation

## Status

Implemented in branch `feat/eda-remediation-nginx` (early 2026); shipped as a built-in remediation rule.

## Overview

A self-healing loop for Nginx webservers. Transforms a failed health-check job in the Control Plane into an automatic service restart on the affected target.

## Triggers

- **Event type**: `task_completed`
- **Status**: `error`
- **Template filter**: `template_name == "Nginx Health Check"`

## Remediation logic

1. `audit-reactor` reads `events.jsonl` and matches the rule below.
2. The matched action triggers `playbooks/remediation/fix_nginx.yml`.
3. The playbook ensures Nginx is `started` and `enabled` on the affected target node.

## Rule definition

In [`extensions/eda/rules.json`](../../../extensions/eda/rules.json):

```json
{
  "name": "Healing: Auto-Restart Nginx",
  "condition": {
    "type": "task_completed",
    "status": "error",
    "template_name": "Nginx Health Check"
  },
  "actions": [
    {
      "type": "shell",
      "command": "ansible-playbook playbooks/remediation/fix_nginx.yml"
    }
  ]
}
```

## Remediation playbook

[`playbooks/remediation/fix_nginx.yml`](../../../playbooks/remediation/) — uses `gather_facts: false` for speed and `become: true` for privilege escalation to manage the systemd service.

## Testing strategy

1. Stop nginx on a managed host (`sudo systemctl stop nginx`).
2. Run the "Nginx Health Check" template in Semaphore.
3. Observe `audit-reactor` triggering the remediation playbook, then verify nginx is back up.

## Dependencies

- [`audit-plane`](./audit-plane.md) — reliable event stream from `events.jsonl`
- [`eda-core`](./eda-core.md) — reactor and rule loader
