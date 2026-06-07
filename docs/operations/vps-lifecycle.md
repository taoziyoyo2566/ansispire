# VPS Lifecycle 运维参考

> **本文档定位**：`feat/target-architecture` 分支下 `playbooks/vps/` 的速查参考。
>
> **第一次接触？** 先看 [`playbooks/vps/README.md`](../../playbooks/vps/README.md)；
> 架构方向见 [`docs/reviews/feat-target-architecture/`](../reviews/feat-target-architecture/)。

---

## 1. 当前分支真相

- 本分支已删除旧的本地 `vps_manager` 控制面。
- 保留的 VPS 自动化内容位于 `playbooks/vps/`。
- 后续的控制面真相目标是：
  - Semaphore Inventory
  - Semaphore Key Store
  - Semaphore Task API
- 这条分支当前**不再**提供本地 inbox / archive / inventory / SSH config 的维护逻辑。

---

## 2. 当前入口

- **Playbook 清单 + `vps_task` 契约**(权威表):见 [`playbooks/vps/README.md`](../../playbooks/vps/README.md) —— 本文不再重复列举,避免多处漂移。
- **三种管理入口矩阵**(Web Wizard / Worker REST API / Manual Ansible CLI):见 [feature-map `vps-lifecycle.md` 的 Management Entry Points](../reference/feature-map/vps-lifecycle.md)。
- **手动 onboarding 操作手册**(控制节点 step-by-step):见 [`vps-onboard-runbook.md`](vps-onboard-runbook.md)。
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

- Semaphore Inventory / Key / Task API 的接入已由 `cf-worker/` 实现，并通过 probe `static` inventory 的 live CRUD 验证;**仍缺** real onboard/audit template provisioning 与 Phase 3 生产 inventory 迁移(file id `2` → static)。
- 部署滞后:`workers.dev` 上的 Worker 可能落后于工作区最新代码,需 `wrangler deploy` 对齐(本地 `npm run integration:live` 测的是本地 handler,测不到已部署版本)。
- `playbooks/vps/` 目前只有 syntax gate，没有新的 Semaphore 执行链路 TSVS。
- 旧 `vps_manager` 的本地生命周期单测已经不再代表当前分支的活跃实现。

---
*Updated: 2026-06-03 (`feat/target-architecture` branch cleanup).*
