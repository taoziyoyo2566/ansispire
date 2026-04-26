# Feature Details: Nginx Auto-Remediation

## Implementation Details

### Rule Definition
Located in `extensions/eda/rules.json`:
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

### Remediation Script
Located in `playbooks/remediation/fix_nginx.yml`. It uses `gather_facts: false` for speed and `become: true` for privilege escalation to manage the systemd service.

### Testing Strategy
1. Manually stop Nginx on a managed host.
2. Run the "Nginx Health Check" template in Semaphore.
3. Observe `audit-reactor` triggering the remediation playbook.
