# Ansispire Project TODO

> 工作流：根据 `~/workspace/CLAUDE.md` §2 Plan-First，所有非平凡变更 plan-doc 优先。每完成一轮在 `docs/reviews/<kind>-<topic>/roundN-YYYY-MM-DD.changelog.md` 落证据。
>
> 状态语义：`[ ]` 未启动 / `[~]` 进行中 / `[✓]` 完成 / `[blocked]` 等外部依赖。
>
> **这是唯一的任务真相源（task ledger SSOT）**。原 `todo` 分支已于 2026-06-05 退役，历史保留在 tag `archive/todo-ledger-2026-06-05`。

---

## 🧭 Scope 决策 (2026-06-05) — 方向锁定

这些是已拍板、不再讨论的方向边界，新工作不得违背：

1. **OS 支持集封闭**：仅 **Debian 系 + RHEL 系**。Alpine 及其他 family 永久 out of scope，由 `infra_baseline` 守门 `fail` 拒绝。原 TASK-007.B（Alpine 分支）**已取消**，不再保留为 backlog。
2. **`todo` 分支退役**：动态真相只看 `TODO.md`。CLAUDE.md §2 已同步。
3. **`feat/target-architecture` 永不进 `master`**：按 §4 分支规则，feat 只回 `dev`；架构方向的发布走 `dev`，release 边界另议。
4. **`feat/vps-manager-v2` 冻结为历史参考**：所有「回归 Semaphore」的新规划/实现归 `feat/target-architecture` 或其子分支，不再落到 v2。

---

## 🟢 已完成 (Completed)

| ID | 任务 | 闭环时间 | 闭环报告 |
|---|---|---|---|
| TASK-007 | Multi-OS Target Fleet (Debian + RHEL families — 即完整支持集) | 2026-05-19 | [`docs/reviews/feat-multi-os-target-fleet/round1-2026-05-19.changelog.md`](docs/reviews/feat-multi-os-target-fleet/round1-2026-05-19.changelog.md) |
| TASK-001 | Advanced Self-Healing Scenarios (v2.3 API-driven reactor & IaC) | 2026-05-10 | [`docs/reviews/feat-eda-advanced-healing/round4-2026-05-10.changelog.md`](docs/reviews/feat-eda-advanced-healing/round4-2026-05-10.changelog.md) |
| TASK-004 | Robust Bootstrap 2.1 (venv isolation & path consistency) | — | — |
| TASK-006 | 升级至 Ansible-Core 2.20.5 (2026 LTS) | — | — |
| — | establish AI-native governance (GEMINI.md / CLAUDE.md hierarchy) | — | — |
| — | mass quality refactoring (lint clean) | — | — |
| — | zero-data-loss audit relay with pagination | — | — |
| — | lightweight EDA reaction engine core (Round 1–4) | 2026-05-10 | TASK-001 |
| — | basic Nginx auto-remediation logic (`feat/eda-remediation-nginx`) | — | — |

---

## 🟡 进行中 / 下一轮可立刻启动 (Active / Next-up)

### Target Architecture — 回归 Ansible + Semaphore  ▶️ **P1 主线**
- **目标**：以 `Semaphore Inventory + Key Store + Task API` 作为控制面真相；owner branch 已移除本地 `vps_manager` 调度层，并把保留的生命周期 playbook 迁到 `playbooks/vps/`。
- **入口**：`docs/reviews/feat-target-architecture/`（`plan-2026-05-25.md` / `design-2026-05-26.md` / `TODO-2026-06-03-branch-management.md` / `round1..3-2026-06-03.changelog.md`）、`docs/reference/investigations/IVG-SEMAPHORE-INVENTORY-API.md`
- **状态**：▶️ owner branch + cleanup 已落地；Phase 1 **静态**契约调查完成（IVG），**运行态验证被环境阻塞**。
- **🚧 头号阻塞（critical path gate）**：本工作区 `.venv/bin/ansible-playbook`、`python3` 缺失，且 Docker daemon socket 指向失效目标——无法跑一次性 Semaphore 探针。**在恢复 Docker daemon 之前，Phase 1 无法收尾，整条 P1 主线停滞。**
- **下一步**：
    1. `[blocked]` Phase 1 收尾：在有 Docker daemon 的环境跑一次性 Semaphore 探针，证明 `GET/PUT /inventory/{id}` + task launch `extra_vars` 契约（当前公开证据只够支撑 `static` whole-blob CRUD，未证明 `extra_vars`）
    2. `[ ]` **Q4 决策（待用户）**：CF Worker 语言 —— JS 推荐 / Python 备选
    3. `[ ]` Phase 2：锁定 Wizard / Worker payload 契约（依赖 Phase 1 探针结论）
    4. `[ ]` Phase 3：把 `controller/semaphore/bootstrap.yml` 的 `type:"file"` inventory 切到 DB-backed `static`，并把 `playbooks/vps/` 真正接到 Semaphore Inventory / Key Store / Task API
- **建议子分支**（仅在 Phase 1 探针通过后开）：`feat/semaphore-inventory-api` → `feat/cf-worker-wizard` → `refactor/semaphore-vps-cutover` → `feat/semaphore-prod-hardening`（全部 from `feat/target-architecture`）

### TASK-009 — Dependency / Image Security Governance  🟡 **P1（并行，不阻塞主线）**
- **目标**：把当前「版本治理骨架」补成真正可审计的安全 / 兼容性闭环：覆盖 Python 依赖、容器镜像、Semaphore 上游版本、兼容性矩阵、以及 waiver 机制。
- **入口**：`docs/reviews/feat-dependency-security-governance/plan-2026-06-03.md`、`round1-2026-06-03.changelog.md`
- **当前缺口**：
    1. `[ ]` Python 依赖无漏洞扫描（仅有 `detect-secrets` + Dependabot）
    2. `[ ]` Docker / Semaphore / base image 无 CVE gate
    3. `[ ]` 依赖与镜像缺少 release-mode 冻结集（当前多为 `>=` 最低版本）
    4. `[ ]` 没有兼容性矩阵，无法定义「支持 / 候选 / 豁免 / 不支持」
    5. `[ ]` 没有 Semaphore 上游 advisory / release 审查机制与 waiver 规则
- **说明**：纯仓内工作，**不依赖 Docker daemon**——在 P1 主线被环境阻塞期间，这是可立刻推进的那条 P1。
- **建议分支**：`feat/dependency-security-governance`

### TASK-007.C — Hub remote orphan cleanup  🟡 P2（待用户决策）
- **目标**：`inventory/hosts.ini` 与 `inventory/prod/hosts.ini` 的 `[hub_remote]` 仍指 `ans-hk01`，但该 IP（89.185.26.211）在 2026-05-19 OS 重装后已变成 Debian 13 target `d13`（port 22）。
- **决策项（待用户）**：(a) 拨新 VPS 当 remote hub / (b) 接受 hub-only-local 并清空 `[hub_remote]` / (c) 重新部署 hub 到 d13 或其他机器。
- **拆解**：
    1. `[ ]` 用户决策：要不要 hub_remote？
    2. `[ ]` 按决策更新 inventory + SSH config
    3. `[ ]` 如保留：`make hub-deploy HUB_NODE=remote` 验证
- **建议分支**：`fix/hub-remote-cleanup`

### TASK-008 — DB Failover Playbook 真实化  🟡 P2（待用户决策）
- **目标**：把 `playbooks/remediation/db_failover.yml` 占位剧本替换为真实 failover；翻 `extensions/eda/rules.json` 中 `Remediation: DB Connection Failure` 的 `enabled: false` → `true`；加 L4 e2e 用例。
- **决策项（待用户）**：failover 模型 —— 主备切换 / 提升 standby / DNS 切换；以及是否有可演练的 db 拓扑。
- **拆解**：
    1. `[ ]` 设计 failover 模型（需用户决策）
    2. `[ ]` 实现 `playbooks/remediation/db_failover.yml`
    3. `[ ]` 翻 rules.json `enabled` + 删 `_disabled_reason`
    4. `[ ]` `controller/audit/e2e/run.sh` 加第二注入步骤 + 第二 task 轮询
    5. `[ ]` 更新 `docs/reference/test-specs/eda-reactor-e2e.md` §6（双用例）
- **建议分支**：`feat/eda-db-failover`

---

## 🔵 待规划 (Backlog)

### TASK-005 — Production Deployment Blueprint  *(scope 已收缩)*
- **现状**：Round 4 已实现 Path A 真部署（`make hub-deploy HUB_NODE=...`）+ 完整 operator-guide；原 scope 大部分被 TASK-001 吸收。
- **剩余 scope**：
    1. `[ ]` 部署后健康监控（hub 上 cron / systemd timer 定期查 audit-relay/sink/reactor 存活）
    2. `[ ]` 定期 EDA token 轮换 playbook
    - *(注：原「`make verify` 的 vault 密码集成」已被 `ec93094` 修复，移出此清单)*
- **优先级**：P2

### TASK-002 — Monitoring Integration (Prometheus)
- **目标**：reactor / relay / sink 暴露 metrics endpoint；hub 上跑 prom-stack；自愈链路有 `eda_rule_matches_total` 等指标。
- **依赖**：TASK-001（已闭环）；端口 9390/9090 已在 `config/manifest.yml` 预留。
- **优先级**：P3 ・ **建议分支**：`feat/observability-prometheus`

### TASK-003 — Controller High Availability
- **目标**：多节点 Semaphore；DB 从 SQLite 升级到 Postgres / MySQL；HA 选主 / 共享存储。
- **优先级**：P3（生产规模化时再做）。**注**：与 Target Architecture Phase 3/4 的 DB-backed inventory 方向相关，落地时需对齐。

---

## ❓ 待用户决策汇总 (Open Decisions — 阻塞下游)

| # | 决策 | 阻塞的任务 | 选项 |
|---|---|---|---|
| Q4 | CF Worker 语言 | Target Arch Phase 2 | JS（推荐）/ Python |
| D1 | hub_remote 去留 | TASK-007.C | 拨新机 / 清空 local-only / 重部署到 d13 |
| D2 | DB failover 模型 + 是否有演练 db 拓扑 | TASK-008 | 主备切换 / 提升 standby / DNS 切换 |
| ENV | 提供一个有 Docker daemon + ansible venv 的环境 | Target Arch Phase 1 收尾（**P1 critical path**） | 恢复本机 daemon / 换执行环境 |

---

## 📌 当前分支状态 (Branch Status)

- **当前分支**：`feat/target-architecture`（owner / planning branch for 回归-Semaphore 方向）
- **合并目标**：**仅 `dev`**（feat→dev，§4 规则）。**永不进 `master`**（2026-06-05 决策）。
- **同步状态**（2026-06-05 实测）：`feat/target-architecture..origin/dev` 为空 —— 与 dev tip 一致，无待合并 dev 改动（W-R21 sync 通过）。
- **本分支已落地**：owner-branch bootstrap（`3cf02fe`）+ Phase 1 IVG 调查 + 本轮 scope 整理（Alpine 下线 / todo 分支退役 / reference 副本清理 / 文档真相同步）。
- **环境限制**：本工作区无 `.venv` ansible 二进制、无可用 Docker daemon —— 运行态/molecule 验证需在具备这些的环境补做（见 Open Decisions ENV）。

---

## 🗂 索引

- **架构主图**：[`ARCHITECTURE.md`](ARCHITECTURE.md)
- **当前方向证据链**：[`docs/reviews/feat-target-architecture/`](docs/reviews/feat-target-architecture/)
- **EDA 自愈用户向 guide**：[`docs/user-guide/02-quickstart-eda.md`](docs/user-guide/02-quickstart-eda.md)
- **Hub 部署速查**：[`docs/operations/hub-deployment.md`](docs/operations/hub-deployment.md)
- **测试规格 (TSVS)**：[`docs/reference/test-specs/`](docs/reference/test-specs/)
- **调查索引**：[`docs/reference/investigations/INDEX.md`](docs/reference/investigations/INDEX.md)
- **CLAUDE.md 三层**：`~/.claude/CLAUDE.md` / `~/workspace/CLAUDE.md` / `./CLAUDE.md`

---
*Last updated: 2026-06-05 (Scope 决策锁定：Alpine 下线 / todo 分支退役 / target-arch 不进 master / reference 副本清理；Branch Readiness 段重写为当前分支真相).*
