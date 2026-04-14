# Event-Driven Ansible (EDA) — Reserved Directory

> Chinese reference snapshot: `../../../docs/reference-cn/snapshot-2026-04-14/extensions/eda/rulebooks/README.zh.md`

## Overview

Event-Driven Ansible (EDA) is a component that went GA in Ansible Automation Platform 2.4+.
It is used to trigger playbook execution automatically based on events (monitoring alerts, webhooks, Kafka messages, etc.).

**Current status**: This directory is a reserved skeleton; no concrete rules are implemented yet.
**Fit for**: infrastructure self-healing, event-driven automation ops.

## When to Enable

Consider implementing EDA rules when your infrastructure hits any of the following:

- A monitoring system (Prometheus/Grafana) fires alerts that should trigger automatic remediation
- Webhooks drive infrastructure changes (for example, auto-updating configuration after a code deploy)
- Automation responses to Kafka / RabbitMQ messages
- Self-healing for unplanned events (service crash → automatic restart)

## Quick Start

1. Install dependencies:
   ```bash
   pip install ansible-rulebook
   ansible-galaxy collection install ansible.eda
   ```

2. Create a rulebook in this directory (see the example below).

3. Run the rulebook:
   ```bash
   ansible-rulebook --rulebook extensions/eda/rulebooks/remediation.yml -i inventory/production
   ```

## Rulebook Example

The following is a skeleton for a service self-healing rulebook — adapt as needed:

```yaml
# extensions/eda/rulebooks/remediation.yml
---
- name: Service Auto-Remediation
  hosts: all
  sources:
    # Listen on Alertmanager webhooks
    - ansible.eda.alertmanager:
        host: 0.0.0.0
        port: 9000

    # Or watch files
    # - ansible.eda.file_watch:
    #     path: /var/log/app

    # Or consume from Kafka
    # - ansible.eda.kafka:
    #     host: kafka.example.com
    #     port: 9092
    #     topic: ansible-events

  rules:
    - name: Restart service on alert
      condition: event.payload.status == "firing"
      action:
        run_playbook:
          name: playbooks/remediation/restart_service.yml

    - name: Notify on resolution
      condition: event.payload.status == "resolved"
      action:
        run_job_template:
          name: "Notify Slack"
          organization: Default
```

## Related Resources

- [EDA documentation](https://ansible.readthedocs.io/projects/rulebook/)
- [ansible.eda collection](https://galaxy.ansible.com/ansible/eda)
- [AAP EDA guide](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.5/html/event-driven_ansible_controller_user_guide/)
- [Community discussion](https://forum.ansible.com/c/project/event-driven-ansible/55)
