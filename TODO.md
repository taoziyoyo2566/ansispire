# Ansispire Project TODO

> 工作流：根据 `~/workspace/CLAUDE.md` §2 Plan-First，非平凡变更先建立与审批范围匹配的 direction/execution 基线；调查、稳定设计、runbook、测试契约和治理文档按各自 SSOT 路由，不再统一包装成 plan。新主题在 `docs/workstreams/<kind>-<topic>/` 保存审批/review/round evidence；`docs/reviews/` 仅作为未迁移历史根目录。
>
> 状态语义：`[ ]` 未启动 / `[~]` 进行中 / `[✓]` 完成 / `[blocked]` 等外部依赖。
>
> **这是唯一的任务真相源（task ledger SSOT）**。原 `todo` 分支已于 2026-06-05 退役；该分支与 0.0.1 之前的已完成任务记录均保留在归档的上游 `ansispire` 仓库历史中。

---

## 🧭 Scope 决策 (2026-06-05) — 方向锁定

这些是已拍板、不再讨论的方向边界，新工作不得违背：

1. **OS 支持集封闭**：仅 **Debian 系 + RHEL 系**。Alpine 及其他 family 永久 out of scope，由 `infra_baseline` 守门 `fail` 拒绝。原 TASK-007.B（Alpine 分支）**已取消**，不再保留为 backlog。
2. **`todo` 分支退役**：动态真相只看 `TODO.md`。CLAUDE.md §2 已同步。
3. **`feat/target-architecture` 永不进 `master`**：按 §4 分支规则，feat 只回 `dev`；架构方向的发布走 `dev`，release 边界另议。
4. **`feat/vps-manager-v2` 冻结为历史参考**：所有「回归 Semaphore」的新规划/实现归 `feat/target-architecture` 或其子分支，不再落到 v2。

---

## 🟡 进行中 / 下一轮可立刻启动 (Active / Next-up)

> 0.0.1 之前的已完成任务（TASK-001/004/006/007 等）连同闭环报告保留在归档的
> 上游 `ansispire` 仓库历史中，本清单只保留活跃与待办条目。

### Saberu Repo Migration — 迁移到 saberu-ops/saberu 0.0.1  ▶️ 进行中
- **目标**：以当前整合工作树为基线，裁剪后作为 `saberu-ops/saberu` 的 `v0.0.1` 初始导入（无历史）；旧仓库归档。
- **入口**：[`docs/workstreams/feat-saberu-migration/`](docs/workstreams/feat-saberu-migration/)（execution plan APPROVED 2026-07-18）。
- **状态**：Phase 1–2 执行中；Phase 4（建仓+推送）前需用户放行；新仓 `master`/`dev` 不接受直接提交，导入走 PR。
- **0.0.2 后续**：内部 `ansispire`→`saberu` 改名（约 191 文件，L2）；旧仓库转 archive；`/tmp` worktree 清理；被整合分支的收尾。

### Target Architecture / Saberu MVP — Semaphore-native VPS takeover  ▶️ **P1 主线**
- **目标**：以 `Semaphore Inventory + Key Store + Task API + Semaphore UI` 作为近期控制面真相；先在当前 `ansispire` 跑通 Saberu MVP 的第一条执行证明链路：audit → onboard → managed-channel audit `0 changed`。owner branch 已移除本地 `vps_manager` 调度层，并把保留的生命周期 playbook 迁到 `playbooks/vps/`。
- **产品方向（2026-06-23 已确认）**：产品名 **Saberu**；短期目标是个人多 VPS 标准化接管/加固/软件安装/服务配置；短期实施图为 [`new-vps-takeover-implementation-steps-2026-06-23.drawio`](docs/reviews/feat-product-redesign/new-vps-takeover-implementation-steps-2026-06-23.drawio)；领域模型为 `Node` / `NodeGroup` / `Credential` / `BaselineProfile` / `ServiceProfile` / `TaskPlan` / `TaskRun` / `AuditEvent` / `Service`。
- **MVP surface 决策（D2 关闭）**：**Semaphore UI first**。官方能力覆盖 MVP 控制台基础面（Inventory / Key Store / Repositories / Task Templates / Tasks+logs / Schedules / API tokens / Teams-RBAC 入口）；自研 UI/API 和新仓蓝图 deferred，直到 onboard/audit 闭环跑通且具体 gap 出现。
- **入口**：方向/执行主线 [`docs/reviews/feat-target-architecture/plan-semaphore-native-onboard-2026-06-10.md`](docs/reviews/feat-target-architecture/plan-semaphore-native-onboard-2026-06-10.md)（APPROVED，方向与父执行范围已定）；细节拆解 [`plan-saberu-vps-takeover-execution-2026-06-24.md`](docs/reviews/feat-target-architecture/plan-saberu-vps-takeover-execution-2026-06-24.md)（**APPROVED 2026-07-11**，执行工作分解生效）；产品治理 [`docs/reviews/feat-product-redesign/plan-product-redesign-2026-06-23.md`](docs/reviews/feat-product-redesign/plan-product-redesign-2026-06-23.md)；D2 决策 [`decision-mvp-surface-semaphore-ui-first-2026-06-23.md`](docs/reviews/feat-product-redesign/decision-mvp-surface-semaphore-ui-first-2026-06-23.md)；`docs/reference/investigations/IVG-SEMAPHORE-INVENTORY-API.md`。
- **状态**：▶️ owner branch + cleanup 已落地；Worker 本地实现 / Cloudflare deploy / live probe CRUD 均通过但 **不是执行主线**。**Phase 0 gate + Phase 1 gate 均已过（2026-07-11）**：首次真机 `VPS Audit` 对 3 台跨系测试机（Ubuntu 24.04 / Rocky 9.8 / Debian 13.5）`status=success`、`failed=0 changed=0`。过程中修掉 `bootstrap.yml` 两个缺陷（template 未绑 env + `vps-audit-env` 缺 `ANSIBLE_CONFIG` env → vault 文件权限中止），改为 create + 无条件 converge PUT，break→heal 回归验证通过。**Phase 2 + Phase 3 亦已推进（2026-07-11）**：`VPS Onboard` 模板 + 凭据契约（`public_key_content`；managed 校验用**任务级连接变量复用 Key Store 钥匙**，无挂载——round12 真机验证后从挂载方案重构而来）。**Phase 3 真机闭环 2/3 通过**：u24 + d13 onboard → 切 39222 managed 通道 → 重审 `success` + `changed=0`；r9 首先受 EPEL 镜像不可达阻塞，后续 RHEL 步骤仍待验证。`controller-vps-smoke` 与 TSVS 已建并对 u24+d13 PASS。见 `round10`–`round12-2026-07-11.changelog.md`。**下一步：修复 r9 EPEL 可达性后补齐 RHEL 全链路。**
- **运行态探针结论（2026-06-06）**：Semaphore `static` inventory 支持 whole-blob CRUD；`PUT /inventory/{id}` 返回 `204`；任务运行时变量使用 task-level `environment` JSON string 承载嵌套 `vps_task`，不依赖 raw `extra_vars`。
- **决策（2026-06-06 全部关闭）**：Q1 不加内部 TLS（docker 内部）· Q2 暂用 SQLite（后期升 Postgres，与 TASK-003 一并处理）· Q3 保持 Key Store（后续按需 Vault）· Q4 CF Worker = JS。详见 `design-2026-05-26.md §八`。
- **下一步（按 Jun-10 approved plan 执行，不另开新仓）**：
    1. `[✓]` Phase 0（gate 已过 2026-07-11）：**collections 解析已验证**——`make controller-up`（Semaphore v2.18.2 / ansible 13.5.0）+ 容器内 `--syntax-check playbooks/vps/{onboard,audit}.yml` 均 `exit 0`，4 个所需 collection（community.general/mysql/docker、ansible.posix）镜像自带，**无需烘焙 Dockerfile**。顺带修复 `ansible.cfg` 全局 `vault_password_file` 使容器急切加载 host `.vault_pass`（uid1000/600）失败的 bug——commit `0b68119`。
    2. `[✓]` Phase 1（gate 已过 2026-07-11）：**代码 P1.1–P1.4（commit `2da4aae`）+ P1.3 副作用 SAFE + 首次真机 audit `status=success`**。`bootstrap.yml` 新增 `vps-fleet`/`vps-fleet-key`/`vps-audit-env`/`VPS Audit` + post-condition 断言 + 幂等修复。首跑 vault 报错 → 修掉两缺陷（未绑 env + 缺 `ANSIBLE_CONFIG` env，见 changelog Root Cause），改 create + converge PUT，break→heal 回归通过。task #3/#4 对 u24/r9/d13 三机 `failed=0 changed=0`；修复与 round10 已由 commit `96b11ba` 落地。
    3. `[✓]` Phase 2（2026-07-11）：`onboard.yml` 加 `public_key_content` 内联分支；`bootstrap.yml` 新增 `vps-onboard-env` + `VPS Onboard`(复用 Phase 1 env-绑定,live id=15/env=5)。**凭据契约后经真机验证重构（round12）**：managed 校验从"挂载私钥 + `ssh -i`"改为**任务级连接变量复用 Semaphore Key Store 钥匙**（挂载撞容器 uid 权限、且重复 Key Store，已删挂载/secrets）；顺带修 fail2ban-on-RHEL(前置 EPEL)。见 `round11`/`round12-2026-07-11.changelog.md`。
    4. `[~]` Phase 3（2026-07-11，2/3 真机证明）：**u24 + d13 完整闭环——onboard → 切 39222 managed 通道、关 22 → managed 重审 `success` + `changed=0`**。**r9(Rocky)受阻**：观察到的首个 blocker 是 `dnf install fail2ban` 无法访问 EPEL 镜像；通过该点后仍需验证余下 RHEL 步骤。onboard 已加 `strategy: free`(单台慢机不再堵全队)。**`controller-vps-smoke`(managed 审计幂等冒烟)+ TSVS-VPS-ONBOARD-E2E-001 已建并 PASS**(u24+d13)。剩余：r9 修 EPEL 可达性后 onboard 补齐(补 RHEL 全链路)。
- **Deferred**：Worker R3–R12、production inventory migration、自研 UI/API / 新 `saberu` 仓蓝图、AI Copilot(D3) 等都等上述闭环证明后再评估。Profile catalog 已因配置归属/可发现性问题单列为下方方向计划，不再混在本行。

### VPS Profile Catalog — 可组合配置与单一归属  🟡 **P1 方向已批准 / 实现待子计划批准**
- **目标**：把用户/身份、主机策略、软件与服务的非秘密配置集中到一个可发现的 Git profile library；每个 Node 直接选择一个完整 `BaselineProfile` 和零到多个 `ServiceProfile`，由 Baseline 在内部组合 identity / host-policy / baseline-software 组件；明确 Git / Semaphore Inventory / Key Store / 单次任务参数 / role defaults 的唯一职责。
- **触发问题**：当前 managed user 至少有 `vps_task.managed`、`common__deploy_users`、`infra_baseline_mgr_user` 三个 owner；`vps-onboard-env` 同时被 UI 手工修改与 `controller-bootstrap` 从仓库示例无条件覆盖，用户无法可靠判断配置应改在哪里。
- **Workstream**：[`docs/workstreams/feat-vps-profile-catalog/README.md`](docs/workstreams/feat-vps-profile-catalog/README.md) 是状态、当前动作与 artifact map 的单一入口。
- **Direction**：`APPROVED 2026-07-17`；whole-topic migration 保留历史文件名，批准范围仍仅为 direction。
- **Execution details**：WU-1 identity migration execution plan 已建立为 `DRAFT`，必须先由 WU-0 carrier probe 关闭编码/API 未知，再转 `PENDING_APPROVAL`；fail2ban software-profile pilot 仍为 `DRAFT`，并受最终 WU-1 resolver/provider contract 阻塞。旧 software-only 草案已 superseded，但仍作为独立 legacy topic 保留，未被推定为 whole-topic absorption。
- **已确认层级（2026-07-17）**：`BaselineProfile` 是更高层设计；identity 目前只是 Baseline 内部组件，不新增产品级 `IdentityProfile`。Node 日常不直接拼底层组件，需要新组合时创建/复用 Baseline。
- **当前动作**：先保全并从本主题工作树分离未提交的 review-taxonomy 改动与未归类 `package.list`，再从 `feat/target-architecture` 基线创建/迁移 owner branch `feat/vps-profile-catalog`；完成分支卫生后执行 WU-0 carrier probe，证据落到同一功能包的 `investigation-profile-carrier.md`，随后用调查结论补齐 WU-1 draft 并单独提交审批。任何代码或真机变更仍受 execution plan 与 live go/no-go gate 阻塞。
- **分支管理缺口**：当前工作树仍在 child branch `feat/vps-software-catalog`；经 2026-07-17 freshness check，本地与远端均不存在 `feat/vps-profile-catalog`。现状未满足“一主题一 owner branch”，不能把准确记录误当作已闭环；本轮不擅自删除未知文件或切换分支。

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

### TASK-010 — VPS Offboard / Reverse Playbook  *(Target Architecture 相关)*
- **目标**：提供「真正还原」能力——把已托管节点回退到 bare 态（或删除某个特定 managed 用户），区别于现有 `remove.yml`（仅从 inventory 移除 + 可选删 sshd drop-in，**默认保留用户与密钥**）。
- **背景**：onboard 无自动回滚，失败靠「修因 + 幂等重跑」恢复；删除 ≠ 还原（删除只是系统遗忘，服务器改动照旧）。详见 [`docs/reviews/feat-target-architecture/onboard-execution-models-2026-06-07.md`](docs/reviews/feat-target-architecture/onboard-execution-models-2026-06-07.md) §5/§9。
- **拆解**：
    1. `[ ]` 设计 offboard 模型（整机还原 vs 仅删指定用户；端口/sshd lockdown 回退顺序）
    2. `[ ]` 实现 `playbooks/vps/offboard.yml`
    3. `[ ]` Worker/wizard 暴露入口（可选）
- **优先级**：P3（独立块，不阻塞 onboard 主线）・**建议分支**：`feat/vps-offboard`

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
- **🔗 Q2 对齐（2026-06-06）**：Target Architecture 决定**暂用 SQLite**（降复杂度），后期升级 Postgres。**Postgres 迁移归口到本任务**——届时 Target Arch 的 DB 后端与本任务的 HA DB 选型一并处理，不重复选型。

---

## ❓ 待用户决策汇总 (Open Decisions — 阻塞下游)

Target Architecture 的 Q1–Q4 已于 2026-06-06 全部关闭（见 `design-2026-05-26.md §八`）：Q1 不加内部 TLS · Q2 暂用 SQLite（Postgres 升级归口 TASK-003）· Q3 保持 Key Store · Q4 CF Worker = JS。Saberu 产品 D1/D2 已于 2026-06-23 关闭：D1 名称 = Saberu；D2 MVP surface = Semaphore UI first。剩余开放项：

| # | 决策 | 阻塞的任务 | 选项 |
|---|---|---|---|
| D1 | hub_remote 去留 | TASK-007.C | 拨新机 / 清空 local-only / 重部署到 d13 |
| D2 | DB failover 模型 + 是否有演练 db 拓扑 | TASK-008 | 主备切换 / 提升 standby / DNS 切换 |
| ~~ENV~~ | ~~执行前复探 Docker/Semaphore runtime~~ | ~~Phase 0~~ | ✅ 已复探（2026-07-11，`~/workspace/.agents/env/mail.yml`，registry 已上移 workspace 层）+ Phase 0/1 gate 已过；Phase 2 前再复探即可 |

---

## 📌 当前分支状态 (Branch Status)

- **当前分支**：`feat/saberu-migration`（自 `feat/vps-software-catalog` 切出，承载整合工作树 + 0.0.1 裁剪；下述为其父线 `feat/target-architecture` 的状态记录）
- **合并目标**：**仅 `dev`**（feat→dev，§4 规则）。**永不进 `master`**（2026-06-05 决策）。
- **同步状态**（2026-06-06 实测）：已 merge `origin/dev`（含 baseline PR #19/#20/#21），CLAUDE.md 冲突已解（merge commit `66e2bb8`）。
- **本分支已落地**：owner-branch bootstrap（`3cf02fe`）+ Phase 1 IVG 调查 + scope 整理（Alpine 下线 / todo 分支退役 / reference 副本清理 / 文档同步）+ dev 同步 merge + **Phase 2 CF Worker 详细设计 + Q1–Q4 决策关闭（2026-06-06 Round 6）** + **Phase 1 runtime probe closure（2026-06-06 Round 7）** + **Saberu 产品方向 / D2 Semaphore UI first / Jun-10 execution plan approval（2026-06-23 docs round）**。
- **环境状态**：执行 Phase 0 前必须按 environment-truth 复探 Docker/Semaphore runtime；不要沿用 2026-06-06 或 2026-06-10 的旧能力快照。

---

## 🗂 索引

- **架构主图**：[`ARCHITECTURE.md`](ARCHITECTURE.md)；Saberu TARGET/AS-BUILT 图与操作入口见 [`docs/feat-target-architecture/`](docs/feat-target-architecture/)
- **当前方向证据链**：[`docs/reviews/feat-target-architecture/`](docs/reviews/feat-target-architecture/)
- **EDA 自愈用户向 guide**：[`docs/user-guide/02-quickstart-eda.md`](docs/user-guide/02-quickstart-eda.md)
- **Hub 部署速查**：[`docs/operations/hub-deployment.md`](docs/operations/hub-deployment.md)
- **测试规格 (TSVS)**：[`docs/reference/test-specs/`](docs/reference/test-specs/)
- **调查索引**：[`docs/reference/investigations/INDEX.md`](docs/reference/investigations/INDEX.md)
- **CLAUDE.md 三层**：`~/.claude/CLAUDE.md` / `~/workspace/CLAUDE.md` / `./CLAUDE.md`

---
*Last updated: 2026-07-18 (saberu-ops/saberu 0.0.1 migration in progress; completed-task history pruned to the archived ansispire repo; Phase 3 remains proven on u24+d13 and partial on RHEL).*
