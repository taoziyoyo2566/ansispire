# Event-Driven Ansible (EDA) — 预留目录

## 简介

Event-Driven Ansible (EDA) 是 Ansible Automation Platform 2.4+ 中 GA 的组件，
用于基于事件自动触发 playbook 执行（如监控告警、Webhook、Kafka 消息等）。

**当前状态**: 此目录为预留骨架，尚未实现具体规则。
**适合场景**: 基础设施自愈、事件驱动的自动化运维。

## 何时启用

当你的基础设施满足以下任一场景时，考虑实现 EDA 规则:

- 监控系统（Prometheus/Grafana）触发告警后需要自动执行修复操作
- Webhook 触发基础设施变更（如代码部署后自动更新配置）
- 基于 Kafka/RabbitMQ 消息的自动化运维响应
- 计划外事件的自愈（服务崩溃 → 自动重启）

## 快速开始

1. 安装依赖:
   ```bash
   pip install ansible-rulebook
   ansible-galaxy collection install ansible.eda
   ```

2. 在此目录创建规则文件（见下方示例）

3. 运行规则集:
   ```bash
   ansible-rulebook --rulebook extensions/eda/rulebooks/remediation.yml -i inventory/production
   ```

## 规则文件示例

以下为一个服务自愈规则的骨架，可按需实现:

```yaml
# extensions/eda/rulebooks/remediation.yml
---
- name: Service Auto-Remediation
  hosts: all
  sources:
    # 监听 Alertmanager webhook
    - ansible.eda.alertmanager:
        host: 0.0.0.0
        port: 9000

    # 或监听文件变更
    # - ansible.eda.file_watch:
    #     path: /var/log/app

    # 或监听 Kafka
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

## 相关资源

- [EDA 官方文档](https://ansible.readthedocs.io/projects/rulebook/)
- [ansible.eda 集合](https://galaxy.ansible.com/ansible/eda)
- [AAP EDA 指南](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.5/html/event-driven_ansible_controller_user_guide/)
- [社区讨论](https://forum.ansible.com/c/project/event-driven-ansible/55)
