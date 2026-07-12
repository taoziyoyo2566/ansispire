# VPS Lifecycle 运维参考

> **本文档定位**：`feat/target-architecture` 分支下 `playbooks/vps/` 的速查参考。
>
> **第一次接触？** 先看 [`playbooks/vps/README.md`](../../playbooks/vps/README.md)；
> 架构方向见 [`docs/reviews/feat-target-architecture/`](../reviews/feat-target-architecture/)。

---

## 1. 当前分支真相

- 本分支已删除旧的本地 `vps_manager` 控制面。
- 保留的 VPS 自动化内容位于 `playbooks/vps/`。
- 当前控制面真相是：
  - Semaphore Inventory
  - Semaphore Key Store
  - Semaphore Task API
- 这条分支当前**不再**提供本地 inbox / archive / inventory / SSH config 的维护逻辑。

---

## 2. 当前入口

- **Playbook 清单 + `vps_task` 契约**(权威表):见 [`playbooks/vps/README.md`](../../playbooks/vps/README.md) —— 本文不再重复列举,避免多处漂移。
- **主入口**：Semaphore UI 的 `vps-fleet` / Key Store / `VPS Audit` / `VPS Onboard`，见 [`../feat-target-architecture/operator-guide.md`](../feat-target-architecture/operator-guide.md)。
- **入口矩阵**：Semaphore UI / deferred Worker / Manual Ansible CLI，见 [feature-map `vps-lifecycle.md`](../reference/feature-map/vps-lifecycle.md)。
- **手动 onboarding 操作手册**（break-glass）：见 [`vps-onboard-runbook.md`](vps-onboard-runbook.md)。
- **语法闸口**:`make vps-lifecycle-syntax`(对全部保留 playbook 做原生 Ansible syntax-check)。

---

## 3. 输入契约

- playbook 统一假设 inventory 中存在 `vps_targets` host / group。
- 任务输入通过顶层变量 `vps_task` 注入。
- 示例 payload 在 `playbooks/vps/examples/*.yml`。
- 这些示例是 `extra_vars` 参考，不是旧 `runtime/inbox/vps/` 的任务文件。

---

## 4. 当前不再负责的事情

- 本地 task draft / submit / process 流程
- 本地 `runtime/state/vps_inventory.yml`
- 本地 SSH config 生成
- 本地任务归档与脱敏流程
- Python wrapper CLI / schema 校验器

这些能力如果还需要，必须通过新的 Semaphore-first 方案重新定义，不能把旧 `vps_manager` 语义直接搬回来。

---

## 5. 运行前要确认的事

1. `vps_task` 中的 `ssh.managed_port` 必须是非 22 高位端口。
2. bootstrap 密码仍建议通过 `password_env` 或等价 secret 注入，不要把明文写进 payload。
3. inventory / key / task-history 的真相应当落到 Semaphore 一侧，而不是回到本地文件系统。

---

## 6. 当前缺口

- Semaphore-native `VPS Audit` / `VPS Onboard` 已 provision；u24+d13 已完成真实闭环，RHEL 全链路仍待补齐。
- `cf-worker/` 已 probe/deploy，但不是当前主线。其 `onboard-bare` payload 仍使用已废弃的 `managed_private_key` 契约，刷新代码与测试前不得作为 onboard 入口。
- Worker production inventory migration、post-success promotion、并发 whole-blob 写保护仍 deferred。
- 活跃验证载体：`make controller-vps-smoke` + `TSVS-VPS-ONBOARD-E2E-001`；onboard takeover 段保持人工/API 触发，不做可重复破坏性 smoke。
- 旧 `vps_manager` 的本地生命周期单测已经不再代表当前分支的活跃实现。

---
*Updated: 2026-07-12 (`feat/target-architecture` Phase 3 partial proof + documentation reconciliation).*
