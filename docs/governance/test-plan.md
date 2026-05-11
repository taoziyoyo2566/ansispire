# docs/governance/test-plan.md — 测试计划书 (Test Plan)

> 本文回答："**什么被测了，什么没被测，缺口风险有多大**"。
> 配套的"**应该跑什么 / 何时跑**"在 [`testing-governance.md`](testing-governance.md)。
>
> 治理范围：本文是覆盖率与缺口的**真相清单**。任何"测了"声明必须能在 §4 找到具体断言来源。

---

## 1. 目标与读者

- **读者**：审计员（覆盖率审查）/ 维护者（缺口投资决策）/ 未来 AI agent（接手项目时判断在哪些区域可以信任既有保护）
- **目标**：单文档完整呈现当前测试覆盖矩阵 + 已知缺口与风险等级
- **不在范围**：
  - 测试运行规则（见 [`testing-governance.md`](testing-governance.md)）
  - 单条 TSVS 内容（见 `docs/reference/test-specs/`）
  - 实际历史执行记录（见各 TSVS 第 6 章 "Actual Results"）

---

## 2. 表面清单 (Surface Inventory)

每个表面 = 一个独立追踪覆盖的第一方代码 / 配置区。

| 表面 | 路径 | 类型 | 主要测试拥有者 | TSVS 文档 |
|---|---|---|---|---|
| common role | `roles/common/` | Ansible role | `molecule -s common` | **缺**（round 2 待补） |
| webserver role | `roles/webserver/` | Ansible role | `molecule -s webserver` | **缺**（round 2 待补） |
| database role | `roles/database/` | Ansible role | `molecule -s database` | **缺**（round 2 待补） |
| ansispire_hub role | `roles/ansispire_hub/` | Ansible role (deploy hub stack via rsync) | 仅 lint + syntax + dry-run；e2e 间接覆盖 | **无** |
| ansispire_audit role | `roles/ansispire_audit/` | Ansible role (deploy reactor + relay + sink) | EDA pyramid + e2e | `audit-loopback-functional.md`（间接） |
| infra_baseline role | `roles/infra_baseline/` | Ansible role | 仅 lint + syntax | **无** |
| reactor controller | `controller/audit/reactor.py` | Python | EDA L1 + L3 | `eda-reactor-unit.md` (L1)、`eda-reactor-component.md` (L3)、`eda-reactor-e2e.md` (L4) |
| rules contract | `extensions/eda/rules.json` ↔ `bootstrap.yml` | Config 契约 | EDA L2 | `eda-rules-contract.md` |
| rbac controller | `controller/rbac/` | Bash + Semaphore API | RBAC smoke | `rbac-functional-smoke.md` |
| audit relay/sink | `controller/audit/e2e/`、`controller/audit/{relay,sink}.py` | Docker stack | loop-smoke + e2e | `audit-loopback-functional.md` |
| Cross-role integration | `roles/{common,webserver,database}/*` 共存 | combo | `molecule -s full-stack` | **缺**（round 2 待补） |
| playbooks/inventory | `playbooks/site.yml`、`inventory/{stag,prod}/` | 编排 | lint + syntax + dry-run | **无**（dry-run 即覆盖） |

---

## 3. 覆盖矩阵

行 = 质量属性；列 = 测试金字塔层级。✅ = 已覆盖；⚠ = 部分覆盖；✗ = 未覆盖。

| 质量属性 | L0 静态 | L1 单元 | L2 契约 | L3 组件 | L4 集成 | L5 E2E |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| 语法 / 风格 | ✅ lint+yamllint | — | — | — | — | — |
| Python 纯函数逻辑 | — | ✅ EDA L1 (14) | — | — | — | — |
| 跨配置文件契约 | — | — | ✅ EDA L2 (9) | — | — | — |
| 组件 + mock 外部 | — | — | — | ✅ EDA L3 (5) | — | — |
| Role 部署正确性 | ⚠ syntax (有限) | ✗ | ✗ | ✗ | ✅ Molecule (3 个 role) | ✗ |
| Role 幂等性 | ✗ | ✗ | ✗ | ✗ | ✅ Molecule (idempotence 阶段) | ✗ |
| 多 role 共存 | ✗ | ✗ | ✗ | ✗ | ✅ full-stack | ✗ |
| 真实 stack happy-path | ✗ | ✗ | ✗ | ✗ | ✗ | ✅ EDA L4 + audit-loopback + rbac smoke |
| **防火墙 + intra-host** | ✗ | ✗ | ✗ | ✗ | ✅ Molecule (round 5 修复后) | ✗ |
| **模板渲染产物正确** | ⚠ syntax-check 无法验渲染后 | ✗ | ✗ | ✗ | ✅ Molecule | ✗ |
| **二次执行幂等** | ✗ | ✗ | ✗ | ✗ | ✅ Molecule | ✗ |
| 跨发行版行为 | ✗ | ✗ | ✗ | ✗ | ⚠ 仅 `common` 跨 2 distro (Ubuntu 22 + Debian 12)；`webserver`/`database`/`full-stack` 仅 Ubuntu 22 | ✗ |
| RBAC 权限边界 | ✗ | ✗ | ✗ | ✗ | ✗ | ✅ rbac smoke |

**加粗行** = round 5 实际触发的 bug 类型。**全部只能由 L4 浮现**，L0–L3 物理上无法捕捉。

---

## 4. 每表面断言清单

### 4.1 common role (`molecule/common/verify.yml`)

- timezone == UTC
- `curl` 已安装（来自 `common_packages`）
- Debian 系：`ufw` 已安装（条件：`common_ufw_enabled`）
- `/etc/motd` 存在 + 含 `Ansible` 标记
- `app_base_dir`（默认 `/opt/apps`）存在且为目录
- `app_user`（默认 `appuser`）存在于 passwd

**未断言**：UFW 规则的具体内容、SSH 加固结果、deploy users 详细权限。

### 4.2 webserver role (`molecule/webserver/verify.yml`)

- nginx service running
- `nginx -t` 配置语法通过
- HTTP 200/301/302 在 `localhost:80`
- `/var/www/html/index.html` 存在
- `/etc/nginx/sites-available/test.local.conf` 存在

**未断言**：SSL 证书加载、PHP-FPM 集成、vhost 多入口、限流配置。

### 4.3 database role (`molecule/database/verify.yml`)

- mysql 或 mysqld service running
- `127.0.0.1:3306` 监听
- `testdb` 数据库存在（用 root 密码访问）
- `/etc/mysql/mysql.conf.d/mysqld.cnf` 存在 + 含 `Ansible` 标记

**未断言**：用户权限正确性、备份脚本可执行、replication 状态、innodb 缓冲池实际大小。

### 4.4 ansispire_hub role

- L0：lint + syntax + dry-run
- L4：**无 Molecule 场景**
- L5：通过 `make test-eda-e2e` 启动 docker stack 间接验证（未独立 TSVS）

**结构性盲区**：rsync exclude 规则（21 项）变更没有断言验证；OS family validation 没有 Molecule-level 测试。

### 4.5 ansispire_audit role

- L0：lint + syntax
- L1+L2+L3：EDA pyramid（reactor 14 + contract 9 + component 5 = 28 cases，see TSVS）
- L5：`make controller-loop-smoke` + `make test-eda-e2e` + `audit-loopback-functional.md`

最佳覆盖表面之一（除 reactor 内部以外）。

### 4.6 infra_baseline role

- 仅 L0：lint + syntax
- L1–L5：**全无**
- TSVS：**无**

**最大盲区**。任何变更只能依赖人工 review 与生产部署回滚保护。

### 4.7 reactor controller (`controller/audit/reactor.py`)

详见：
- `eda-reactor-unit.md` (TEST-EDA-001, L1, 14 cases — match_rule 5 种、cooldown 2 种、enabled flag、process_event 4 种)
- `eda-reactor-component.md` (TEST-EDA-003, L3, 5 cases — reactor → mock Semaphore HTTP 契约)
- `eda-reactor-e2e.md` (Phase 3 L4)

### 4.8 rules contract

详见 `eda-rules-contract.md`（TEST-EDA-002, L2, 9 cases）—— 校验 `rules.json` 中所有 `template_name` 在 `bootstrap.yml` 中存在对应 template 定义，字段名 / cooldown 类型合法。

### 4.9 rbac controller

详见 `rbac-functional-smoke.md`（RBAC smoke）—— 三角色（guest / task_runner / owner）权限边界 smoke。

### 4.10 audit relay/sink

详见 `audit-loopback-functional.md`（TSVS-AUDIT-LOOP-001）—— Semaphore API → reactor → relay → sink 全链路回环，验证 ≤ 20s 内事件抵达 sink JSONL。

### 4.11 Cross-role integration (`molecule/full-stack/verify.yml`)

- common 断言子集：timezone == UTC、`curl` 已安装、`appuser` 存在、`/opt/apps` 为目录（**注**：不含 MOTD / UFW 断言）
- `'nginx' in ansible_facts.packages`
- nginx.service running + `nginx -t` 通过
- vhost `fullstack-test.local.conf` 存在
- HTTP 200/301/302/404 响应于 `localhost:80`
- `'mysql-server' in ansible_facts.packages`
- mysql.service running + `127.0.0.1:3306` 监听
- `appdb` 数据库存在（用 root 密码访问）
- `/etc/mysql/mysql.conf.d/mysqld.cnf` 含 `Ansible managed`（**soft check**：`failed_when: false`，不实际中断 verify）
- nginx **AND** mysql 同时 running（co-existence assertion）

---

## 5. 已知缺口与风险分级

| # | 缺口 | 风险 | 触发条件 | 建议处置 | 责任轮次 |
|---|---|:---:|---|---|---|
| G1 | `infra_baseline` 无任何功能测试 | **高** | 任何变更都可能误入生产；该 role 是基线，覆盖面广 | 引入 Molecule 场景 + TSVS | Tier C |
| G2 | `ansispire_hub` 无 Molecule 场景 | 中 | rsync exclude / state file separation 变更未被自动验证 | 引入 Molecule 场景或扩展 e2e | Tier C |
| G3 | `webserver` / `database` 仅 Ubuntu 22.04 | 中 | 跨发行版部署未验证 | 扩展 molecule platforms 矩阵到 Debian 12 | Tier C |
| G4 | 4 个 Molecule 场景无 TSVS | 中 | 断言意图隐式，contributor 需读 verify.yml 才知验什么 | 补 4 份 TSVS（按 §4 已盘断言） | **本 workstream round 2** |
| G5 | `docs/reference/test-specs/INDEX.md` 缺失 | 中 | 找不到全部 TSVS 清单，新加入者难入门 | 创建 INDEX，建立 active/applied/retired 状态机 | **本 workstream round 2** |
| G6 | 缺中间 verify 层（quick 与 full-bore 二选一） | 中 | 贡献者要么测得不够要么测得太久 | 引入 `make verify-mid`（按 git diff 路径选 molecule 场景） | Tier C |
| G7 | 本地 `molecule-all` 串行 | 低 | release 前耗时 10–20 min；CI 已并行不影响 | xargs -P 或并行 Make target | Tier C |
| G8 | 模板渲染产物只有 Molecule 验证 | 低 | 现状勉强可接受，毕竟有 L4 兜底 | 维持现状 + round 2 在 `webserver`/`database` TSVS 显式登记 | round 2 |
| G9 | `roles/common/verify.yml` 不验证 UFW 规则具体内容 | 低 | round 5 已知问题（UFW lo），加规则后仅靠功能测试间接验证 | round 2 在 common TSVS 列入 known limitation | round 2 |

**风险评级原则**：
- **高**：缺口可直接导致生产事故，无人工兜底
- **中**：有部分人工 / 间接覆盖，但应自动化
- **低**：现状可接受，记录在案以备未来决策

---

## 6. 新代码验收准则

新增 / 重大改造任何 first-party role 或 controller 子系统，PR 合并前必须：

1. **L0 全绿**：lint + syntax + dry-run + detect-secrets
2. **TSVS 登记**：至少有一份 TSVS 文档登记在 `docs/reference/test-specs/INDEX.md`（INDEX 由 round 2 引入）
3. **类型对应补充**：
   - 新 Ansible role → Molecule 场景 + TSVS
   - 新 controller pure-Python 模块 → L1 unit + (L3 component if has external IO)
   - 新跨配置 / 跨文件契约 → L2 contract 测试
   - 新 e2e 链路 → L5 e2e 脚本 + TSVS
4. **本文件同步**：§2 表面清单补行 + §3 覆盖矩阵更新 + §4 断言清单补节
5. **治理同步**：[`testing-governance.md`](testing-governance.md) §3 决策树补行
6. **CHANGELOG**：用户可见的测试规则变化按 `CLAUDE.md §0 Sync Guard` 落入 `[Unreleased]`

**红线**：仅"加测试代码、不更新文档"或"加文档、不加测试"都不算完成。

---

## 7. 维护节奏

| 触发 | 必须同步 |
|---|---|
| 新 surface 引入 | §2 + §3 + 决策树（治理文档 §3） |
| 现有测试断言增减 | §4 对应小节 |
| 缺口被消除 | §5 移除该行（保留备注于 changelog） |
| 新缺口被发现 | §5 新行 + 风险等级 + 责任轮次 |
| TSVS 新增 / 退役 | §2 表面清单"TSVS 文档"列 + INDEX |
| 跨发行版扩展 | §3 + §5 G3 行 |
| Round 收尾 | 整体扫一遍是否过时（与治理文档同节奏） |

**自检节奏**：每一轮 round 收尾时，扫本文 §3 覆盖矩阵 + §5 缺口表，判断本轮是否新增 / 闭合缺口。任何漂移立即修复，不允许"下一轮再说"。

---

*配套测试运行规则与决策树见 [`testing-governance.md`](testing-governance.md)。*
*单测试规格与执行记录见 [`docs/reference/test-specs/`](../reference/test-specs/)。*
