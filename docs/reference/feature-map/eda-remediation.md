# Feature: EDA Auto-Remediation

## Status
✅ 框架就绪。当前规则集见 [`extensions/eda/rules.json`](../../../extensions/eda/rules.json)：

| 规则名 | 状态 | 关联 playbook |
| :--- | :--- | :--- |
| **Remediation: Disk Full** | ✅ enabled，cooldown 600 s | `playbooks/remediation/disk_cleanup.yml` |
| **Remediation: DB Connection Failure** | ⚠ enabled=false（playbook 是 placeholder） | `playbooks/remediation/db_failover.yml` |

> 历史：早期 `feat/eda-remediation-nginx` 分支曾有 `Healing: Auto-Restart Nginx` 规则。当前规则集已重整，**nginx 重启的 playbook 仍存在**（`playbooks/remediation/fix_nginx.yml`），可被手工或 Semaphore template 直接调用，但**未挂自动 EDA 规则**。

---

## Overview

EDA 自愈的"反应平面"：当审计平面捕获到匹配规则的事件时，reactor 通过 Semaphore API 触发对应的修复剧本。整个回路 **API-driven**，不在 reactor 进程里直接 `ansible-playbook`。

## Triggers

匹配条件写在 `extensions/eda/rules.json` 的 `condition` 字段。当前用法：
- `description_contains: "Disk Full"` — substring 匹配 event 的 description 字段
- `description_contains: "database connection failed"` — 同上（DB 规则未启用）

## Remediation flow

1. `audit-relay.py` 拉 Semaphore tasks → POST 到 `audit-sink`
2. `audit-sink.py` append 到 `events.jsonl`
3. `audit-reactor.py` tail JSONL，匹配 `rules.json`
4. 命中 → 解析 `template_name → template_id` → `POST /api/project/<id>/tasks` 触发对应 Semaphore template
5. Semaphore 执行注册的 playbook（如 `disk_cleanup.yml`）

## Per-rule playbook details

### Disk Cleanup（实战可用）
- **Playbook**：`playbooks/remediation/disk_cleanup.yml`
- **Helper**：`extensions/eda/rulebooks/clean-tiny.sh`（Debian 路径的 apt-cache + journal 清理）
- **Semaphore template**：`Auto Remediation: Disk Cleanup`（由 `bootstrap.yml` 拨备）

### DB Failover（占位）
- **Playbook**：`playbooks/remediation/db_failover.yml` —— 只 `debug` 一行，等 TASK-008 真实化
- **EDA 规则**：`enabled: false` + 显式 `_disabled_reason` 引用 follow-up

### Nginx Restart（手动 / 可选）
- **Playbook**：`playbooks/remediation/fix_nginx.yml` —— 实战可用
- **EDA 规则**：当前 rules.json 未挂；如需自动化，需在 rules.json 加规则 + 在 Semaphore 拨备对应 template

## Testing

- L4 e2e（`make test-eda-e2e`）已覆盖 Disk Full 路径：注入合成事件 → 拉栈 → 看 reactor → 看 Semaphore task status
- 详见 [`docs/reference/test-specs/eda-reactor-e2e.md`](../test-specs/eda-reactor-e2e.md)

## Dependencies
- [`audit-plane`](./audit-plane.md) — 提供事件流
- [`eda-core`](./eda-core.md) — reactor 与规则加载器
