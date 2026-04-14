# 控制面（Control Plane）

本目录是本项目"多服务器管理控制系统"的**控制平面**落地起点。
当前仅提供 Semaphore 最小实现，后续轮次会逐步引入 AWX、RBAC、审计、EDA 等能力。

---

## 为什么需要控制面？

没有控制面时，Ansible 是"脚本 + SSH"：
- 谁在哪台机器触发了什么，无审计
- 凭证散落在各人的 `.vault_pass`
- 无法对接事件驱动（告警 → 自愈）
- 无统一的 Job 历史与调度

有了控制面后：
- Job 集中调度、记录、可追溯
- 凭证/vault key 集中管理，不下发到人
- 暴露 REST API / Webhook，供 CI、EDA、上游编排调用
- RBAC 可对 project / template / inventory 分别授权

---

## 控制器选型对比

| 维度 | **Semaphore**（本项目默认）| AWX | AAP（商业）|
|------|---------------------------|-----|-----------|
| 部署 | Docker Compose 一条命令 | 仅支持 k3s/k8s + Operator | 仅支持 k8s + Operator |
| 最小资源 | ~200 MB RAM | 4-6 GB RAM | 8+ GB RAM |
| 协议 | MIT | Apache 2.0 | 商业订阅 |
| 功能覆盖 | project / inventory / template / schedule / job history / API | 同左 + EDA + workflow + constructed inventory | AWX + 企业支持/证书/认证 |
| 升级成本 | 生态独立，迁到 AWX 需重建资源定义 | AWX↔AAP 同源，数据可平滑迁移 | — |
| 本项目定位 | **学习/低配机**首选 | 进阶/贴近生产 | 企业采购 |

本项目的 1 GB 内存预算下，Semaphore 是唯一合理选择。

---

## 目录结构

```
controller/
├── README.md              # 本文件（控制面总览）
└── semaphore/             # Semaphore 最小实现
    ├── docker-compose.yml # 服务定义
    ├── .env.example       # 环境变量样例
    ├── bootstrap.yml      # 首次 API 初始化
    └── README.md          # Semaphore 使用文档
```

后续规划目录（未创建）：
```
controller/
├── awx/                   # Round 10+：AWX on k3s 对比教学
├── rbac/                  # Round 8：权限模型示例
└── eda/                   # Round 10：Event-Driven Ansible 接入
```

---

## 快速启动

```bash
# 从仓库根目录
make controller-up           # 启动 Semaphore
make controller-logs         # 跟踪日志
# 浏览器打开 http://localhost:3000
make controller-down         # 停止（保留数据）
```

详细步骤见 [`semaphore/README.md`](./semaphore/README.md)。

---

## 升级路径

### 短期（本项目范围内）
- **Round 8**：在 Semaphore 中定义 RBAC 示例（User / Team / Project permission）
- **Round 9**：审计日志对接（Semaphore webhook → 本 repo `extensions/audit/`）
- **Round 10**：接入 `ansible-rulebook`，Semaphore template 作为 EDA action

### 中期（需额外资源）
- **Round 11**：引入 Prometheus + Grafana 最小栈（独立 docker-compose），监控 Semaphore 和受管主机
- **Round 12**：可选引入 AWX on k3s 作为对比教学（需 4-6 GB RAM，用户决定是否开启）

### 长期（超出本项目）
- 生产环境推荐直接使用 AAP 或 AWX（非本项目范围）

---

## 设计原则

1. **控制面与数据面解耦**：`controller/` 目录独立于 `roles/` `playbooks/`，可单独启停
2. **只读挂载 repo**：控制面不修改代码，只消费 repo；代码修改回到 git 工作流
3. **向更重方案演进时零破坏**：本轮的 inventory/playbook 结构在未来换 AWX 时可直接被 project 同步拉取
4. **教学可读性 > 生产完备性**：本项目目标是让学习者理解控制面概念，不是替代生产平台

---

## 参考

- [Semaphore 官方文档](https://docs.semaphoreui.com/)
- [Semaphore REST API](https://docs.semaphoreui.com/administration-guide/api/)
- [AWX GitHub](https://github.com/ansible/awx)
- 本项目 Round 6 架构方案：`../docs/reviews/claude-review-round-6-2026-04-14.md`
- 本项目 Round 7 实施方案：`../docs/reviews/claude-review-round-7-2026-04-14.md`
