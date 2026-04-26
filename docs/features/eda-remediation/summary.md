# Feature: Nginx Auto-Remediation

## Overview
This feature provides a self-healing loop for Nginx webservers. It transforms a failed health check job in the Control Plane into an automatic service restart.

## Triggers
- **Event Type**: `task_completed`
- **Status**: `error`
- **Template Filter**: `template_name == "Nginx Health Check"`

## Remediation Logic
1. `audit-reactor` detects the failure.
2. Triggers `playbooks/remediation/fix_nginx.yml`.
3. Ensures Nginx is `started` and `enabled` on the target nodes.

## Dependencies
- **Audit Plane**: Reliable event stream from `events.jsonl`.
- **EDA Core**: `reactor.py` and `rules.json`.
