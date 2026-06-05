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

| 入口 | 说明 |
|---|---|
| `playbooks/vps/onboard.yml` | 新机或重装后重新接管：bootstrap SSH → managed user / sudo / fail2ban / 非 22 SSH |
| `playbooks/vps/modify.yml` | 对已纳管主机做包、防火墙、fail2ban、网络参数变更 |
| `playbooks/vps/audit.yml` | 做磁盘 / 内存 / reboot-required / failed services 巡检 |
| `playbooks/vps/remove.yml` | 可选远端清理步骤 |
| `playbooks/vps/docker_host.yml` | 把主机准备成 Docker Host |
| `playbooks/vps/deploy_compose.yml` | 上传并运行 Compose；非公网暴露默认强制 `127.0.0.1` |
| `make vps-lifecycle-syntax` | 对以上 6 个 playbook 做原生 Ansible syntax-check |

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

- 还没有在这条分支上完成 Semaphore Inventory / Task API 的实际 wiring。
- `playbooks/vps/` 目前只有 syntax gate，没有新的 Semaphore 执行链路 TSVS。
- 旧 `vps_manager` 的本地生命周期单测已经不再代表当前分支的活跃实现。

---
*Updated: 2026-06-03 (`feat/target-architecture` branch cleanup).*
