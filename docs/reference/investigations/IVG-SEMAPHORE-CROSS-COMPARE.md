# 技术调查报告 — Ansispire vs Semaphore UI 架构对比 (独立 + 交叉验证)

## 1. 调查概览 (Overview)
- **调查 ID**: `IVG-SEMAPHORE-CROSS-COMPARE`
- **关联任务**: 用户主动发起；无单一 TASK 编号
- **调查类型**: 架构探索 + 局部技术审计 + 第三方分析交叉验证
- **目标**:
  1. 独立形成对 Ansispire 当前架构的观察清单（不参考外部 review）
  2. 独立调研上游 `semaphoreui/semaphore` v2.18 系列的官方架构主张
  3. 与 Codex CLI 提供的分析进行差量对比：哪些独立到达同一结论 / 哪些独立发现 Codex 漏掉 / 哪些 Codex 提出但需要修正
- **结论形态**: 三档建议（Tier 1 hygiene / Tier 2 engineering / Tier 3 architecture），均**不**在本轮实施

---

## 2. 背景与问题描述 (Background)
- **初始观察**: 用户提交 Codex CLI 对 Ansispire dev 分支与 semaphore v2.18.2 的对比分析（5 条具体发现 + 4 个架构借鉴方向）
- **触发原因**: 验证 Codex 结论的覆盖度与正确性，避免单一外部 review 被直接吸收为决策依据（W-R13 / W-R18 pre-accept verification）
- **影响范围**: `controller/semaphore/` + `controller/audit/` + `roles/ansispire_hub/` + `extensions/eda/` + `config/manifest.yml`
- **方法论约束**: 用户要求"先独立分析，再对比 Codex"——本报告 §3-§5 完全独立形成，§6 才做 diff

---

## 3. 调查过程 (Investigation Process)

### 3.1 独立调研步骤（按时序）
1. 读 `ARCHITECTURE.md`、`docs/reference/feature-map/INDEX.md`、`TODO.md`、`README.md` 建立 ansispire 自有架构主张基线
2. 读 `controller/semaphore/docker-compose.yml` + `bootstrap.yml` + `.env.example` + 渲染模板 `roles/ansispire_hub/templates/semaphore_env.j2`
3. 读 `controller/audit/docker-compose.yml` + `reactor.py` + `extensions/eda/rules.json`
4. 读 `roles/ansispire_hub/tasks/main.yml` + `defaults/main.yml`（Path A 全流程）
5. 独立检索 `semaphoreui.com/docs/` 三个核心页面：configuration / runners / security（不沿用 Codex 引用链接）
6. 读取上游 `deployment/docker/server/server-wrapper` 真实源码确认 SQLite 路径语义
7. 验证 `.gitignore` 实际覆盖 vs rsync `--exclude` 实际覆盖的差量

### 3.2 假设（已逐条验证）
- **H1**: 控制面与执行面是否分离 → **否**（同进程）
- **H2**: 上游 `SEMAPHORE_DB_PATH` 是目录还是文件 → **目录**（验证见 §4）
- **H3**: Path A 首次部署 token 链路是否健全 → **不健全**（验证见 §4）
- **H4**: 上游官方 Runner 是 OSS 还是 Pro → **基础 Runner OSS；Tag-routing 是 Pro**（独立确认）
- **H5**: 上游 HashiCorp Vault 集成是 OSS 还是 Pro → **Pro**（独立确认 → Codex 未明确区分）

---

## 4. 证据与日志 (Evidence)

### 4.1 上游 `server-wrapper` 真实路径处理逻辑
```bash
export SEMAPHORE_DB_PATH="${SEMAPHORE_DB_PATH:-/var/lib/semaphore}"
elif [ "${SEMAPHORE_DB_DIALECT}" = 'sqlite' ]; then
    export SEMAPHORE_DB_HOST=${SEMAPHORE_DB_PATH}/database.sqlite
fi
```
来源：`https://raw.githubusercontent.com/semaphoreui/semaphore/develop/deployment/docker/server/server-wrapper`
**结论**：`SEMAPHORE_DB_PATH` 是目录；wrapper 自动追加 `/database.sqlite`。

### 4.2 Ansispire 当前 compose 设置
```yaml
# controller/semaphore/docker-compose.yml:27
SEMAPHORE_DB_PATH: /var/lib/semaphore/semaphore.db
```
**推导实际效果**：wrapper 解析后 `SEMAPHORE_DB_HOST=/var/lib/semaphore/semaphore.db/database.sqlite`——`semaphore.db` 被当作目录创建。Path A 同样问题，因为 `controller/semaphore/docker-compose.yml` 被 rsync 到 `/opt/ansispire/` 后未做修改。

### 4.3 Path A 首次部署 token 链路
```yaml
# roles/ansispire_hub/tasks/main.yml:83-141
- ansible.builtin.stat: path=...state/.eda_token → ansispire_hub_token_file  # ① BEFORE mint
- block:                                                                       # ② mint
    when: not ansispire_hub_token_file.stat.exists and not ansible_check_mode
    # ... mint token, write to file
- ansible.builtin.slurp: src=...state/.eda_token                                # ③ slurp
  when: ansispire_hub_token_file.stat.exists                                    # ←  uses STALE pre-mint value
- ansible.builtin.set_fact: ansispire_hub_eda_token=...
  when: ansispire_hub_token_raw.content is defined
```
**首次部署路径**：① stat=false → ② mint 成功写入文件 → ③ slurp 跳过（仍以 stale false 判断）→ `ansispire_hub_token_raw` 未注册 → fact 未设置 → 下游 `ansispire_audit` 角色拿到空 `SEMAPHORE_API_TOKEN` → reactor 启动后无法触发 remediation。

### 4.4 上游官方配置文档关键变量（独立摘录）
| 变量 | 用途 | requiredness |
|---|---|---|
| `SEMAPHORE_ACCESS_KEY_ENCRYPTION` | Key Store 数据库 AES 密钥 | Recommended（缺失则 Key Store 退化为非加密存储） |
| `SEMAPHORE_COOKIE_HASH` | Session cookie 签名 | Recommended（缺失则重启 invalidate session） |
| `SEMAPHORE_COOKIE_ENCRYPTION` | Session cookie 加密 | Recommended |
| `SEMAPHORE_RUNNER_TOKEN` | Runner 注册 token（Runner 端） | Required（仅当部署 Runner） |
| Vault 外部存储 | 外部 secret store | **Pro feature** |
| Runner Tag routing | 任务路由 | **Pro feature**（基础 Runner 是 OSS） |

来源：`https://semaphoreui.com/docs/administration-guide/configuration` + `/runners` + `/security`

### 4.5 .gitignore 与 rsync exclude 差量
```
.gitignore 包含： .env / .secrets / .vault_pass / runtime/  ✅ 全部生效
roles/ansispire_hub/tasks/main.yml rsync exclude 中：
  - .vault_pass ✅
  - controller/semaphore/.env ✅
  - controller/semaphore/.secrets ✅
  - controller/rbac/users.yml ✅
  - runtime/ ❌ 缺失
git ls-files | grep secret-bearing files ⇒ 仅 .env.example 被追踪（正确）
```

---

## 5. 发现与分析 (Findings) — 独立形成

### 5.A 架构层（Architecture-level，[L2] 级讨论）

| 编号 | 主题 | 风险 | 状态 |
|---|---|---|---|
| **A1** | 控制面与执行面同进程：所有 Ansible 任务在 `ansispire-semaphore` 容器内执行 | 资源/安全边界混合 | 待讨论 |
| **A2** | Secret 管理 5 面无统一模型（`.env` / `.secrets` / Key Store / Ansible Vault / `.vault_pass`） | 责任不清 | 待规划 |
| **A3** | `SEMAPHORE_ACCESS_KEY_ENCRYPTION` 未配置 → Key Store AES 退化 | 中（学习态低；生产高） | T1 修复 |
| **A4** | bootstrap.yml 直接调 ~20 个 Semaphore API 端点，无契约层 | 升级版本时易碎 | T3 规划 |
| **A5** | DB 仅单机命名卷，无备份自动化（README 中手工 tar 命令） | 数据丢失 | T3 规划 |
| **A6** | Compose 无 TLS / 反代 / 资源限制（仅 reactor 有 limits） | 生产不可用 | T3 规划 |
| **A7** | 审计面零可观测性（无 metrics endpoint，无结构化 JSON 日志） | 故障排查盲区 | T3 规划 |
| **A8** | EDA reactor 是自研 Python（~210 行），未用上游 `ansible-rulebook` | 偏离 Ansible 官方 EDA 路线 | 待 IVG 比较成本 |
| **A9** | 单租户假设：bootstrap 只创建 1 主项目 + 1 demo 项目 | 当前 OK；规模化前需重思 | 暂搁置 |
| **A10** | `SEMAPHORE_COOKIE_HASH` / `COOKIE_ENCRYPTION` 未配置 → 容器重启 session 失效 | 低（学习态）/ 中（生产） | T1 修复 |

### 5.B 局部工程层（Engineering-level，[L1] 级修复）

| 编号 | 位置 | 问题 | 风险 |
|---|---|---|---|
| **B1** | `controller/semaphore/docker-compose.yml:27` | `SEMAPHORE_DB_PATH: /var/lib/semaphore/semaphore.db` — wrapper 期望目录，实际把 `semaphore.db` 当目录创建 | 中（语义错误，功能勉强可用） |
| **B2** | `roles/ansispire_hub/tasks/main.yml:131` | Path A 首次部署 slurp 用 stale stat → token fact 未设置 | **高**（首次部署自愈链路失效） |
| **B3** | `controller/semaphore/bootstrap.yml:154` | `git_branch: "master"` 硬编码；当前分支 dev | 中（dev 阶段会跑 master 内容） |
| **B4** | `controller/semaphore/.secrets` | 实际已在 `.gitignore`，**误判**：Codex 未声称泄漏；我也确认未泄漏 | 无 |
| **B5** | `controller/audit/reactor.py:182-184` | webhook action 是 `pass` no-op；rules.json 有 `DB Alert` webhook 配置 | 中（rule 启用后静默失败） |
| **B6** | `controller/audit/reactor.py:204` | rules 热重载每个 poll（默认 1s）盲读盘 | 低 |
| **B7** | `controller/audit/reactor.py:210` | fatal exception 时递归 `main()` 调用 | 低（栈耗尽风险） |
| **B8** | `controller/audit/reactor.py:197` | `f.seek(0, os.SEEK_END)` tail-only → 重启丢失未处理事件 | 低 |
| **B9** | `controller/audit/docker-compose.yml:43-49` & `:112-117` | `apk add logrotate` / `apk add jq` 在容器启动命令里 → 每次重启慢 + 网络依赖 | 低（应做 custom Dockerfile） |
| **B10** | `controller/audit/docker-compose.yml` | audit-relay / audit-reactor 无 healthcheck | 低（观测盲点） |
| **B11** | `roles/ansispire_hub/tasks/main.yml:39-64` | rsync excludes 不包含 `runtime/` → 工作站 VPS manager 状态 leak 到 hub | 中（非密但意外） |
| **B12** | `roles/ansispire_hub/tasks/main.yml:98-106` | `semaphore user add` 仅创建不更新；vault 改密后 admin 密码不轮换 | 低 |
| **B13** | `controller/semaphore/README.md` | 仍提 BoltDB 与端口 3000；实际 SQLite + 3300 | 低（误导操作员） |

---

## 6. 结论与建议 (Conclusion)

### 6.1 与 Codex 分析的交叉对比

#### Codex 5 条具体发现 vs 独立结论
| Codex 编号 | 独立结论 | 备注 |
|---|---|---|
| C#1 ACCESS_KEY_ENCRYPTION | ✅ 独立确认（A3） | 共同结论 |
| C#2 Path A token 首次传播 bug | ✅ 独立确认（B2） | 共同结论；独立读 main.yml 复现链路 |
| C#3 SEMAPHORE_DB_PATH 目录语义 | ✅ 独立确认（B1） | 独立读上游 `server-wrapper` 源码二次确认 |
| C#4 bootstrap git_branch hardcoded master | ✅ 独立确认（B3） | 共同结论 |
| C#5 README 陈旧（BoltDB / 端口 3000） | ✅ 独立确认（B13） | 共同结论 |

#### Codex 4 个架构方向 vs 独立结论
| Codex 方向 | 独立评估 | 偏差 |
|---|---|---|
| Runner 抽象 | ✅ 同意，基础 Runner 是 OSS | Codex 描述准确 |
| Secret Storage 三层模型 | ✅ 同意优先级（先 ACCESS_KEY_ENCRYPTION，再 Vault） | **关键修正**：External Vault 是 Pro feature，Codex 未明确标注 |
| API Schema 契约 | ✅ 同意 | 独立补充：bootstrap.yml 实际耦合 ~20 个端点，应该枚举 |
| 配置项分层（feature flag） | ✅ 同意方向 | 独立建议：复用现有 `config/manifest.yml` SSOT，而非新建 `ansispire_features` 顶层概念 |

#### 独立发现而 Codex 漏掉的项
1. **B5** reactor webhook action 是 no-op stub（rule 启用后静默失败）
2. **B6 / B7 / B8** reactor 三个鲁棒性问题（热重载频率 / 递归 main / tail-only 重启丢失）
3. **B9** audit 容器启动时 `apk add` 反模式
4. **B10** relay / reactor 无 healthcheck
5. **B11** rsync excludes 漏 `runtime/`
6. **B12** admin 密码无法静默轮换
7. **A8** EDA reactor 自研 vs `ansible-rulebook` 的架构选择从未评估
8. **A10** `SEMAPHORE_COOKIE_HASH` / `COOKIE_ENCRYPTION` 一并缺失（Codex 仅提 ACCESS_KEY）

#### Codex 提到但需修正的项
- **External Vault 优先级**：Codex 把"对齐 Vault"列为长期借鉴，但**没说明这是 Pro feature**。OSS 路线下不应规划。
- **优先级排序**：Codex 把 token 首次传播 bug 列为最急，但**B1 DB_PATH 语义错误与 A3 ACCESS_KEY_ENCRYPTION 也是"静默错误状态"**，三者应并列最高。

### 6.2 分档建议（**仅建议，不在本轮实施**）

#### Tier 1 — Hygiene（小修，可单 PR）
- T1.1 修 B1：`SEMAPHORE_DB_PATH` → `/var/lib/semaphore`（或删除该 env，使用 wrapper 默认）
- T1.2 修 B2：mint 后立即 `set_fact ansispire_hub_eda_token`，绕过 stale stat
- T1.3 修 B3：`git_branch: "{{ semaphore_git_branch | default('dev') }}"`
- T1.4 修 B5：在 reactor.py 实现 webhook POST 或从 rules.json 删除 webhook action
- T1.5 修 B11：rsync `--exclude=runtime/`
- T1.6 修 B13：`controller/semaphore/README.md` 同步 SQLite + 端口 3300
- T1.7 加 A3 / A10：`.env.example` 注释 + `semaphore_env.j2` 渲染 `ACCESS_KEY_ENCRYPTION` + `COOKIE_HASH` + `COOKIE_ENCRYPTION`；hub 角色生成一次并持久化到 state dir

**建议 plan-doc**：`docs/reviews/fix-codex-cross-compare/plan-2026-05-17.md`

#### Tier 2 — Engineering（局部架构小决策）
- T2.1 修 B6 / B7 / B8：reactor 鲁棒性 pass
- T2.2 修 B9：`controller/audit/Dockerfile.sink` + `Dockerfile.reactor`（baked-in 工具）
- T2.3 修 B10：relay / reactor healthcheck
- T2.4 加 API preflight：`controller/semaphore/bootstrap_preflight.yml`（在主 bootstrap 跑前先 ping 每个端点 + 校验最小 shape）
- T2.5 修 B12：用 `semaphore user change-by-login` 走密码轮换路径

**建议 plan-doc**：`docs/reviews/feat-audit-hardening/plan-...md`（待范围决策后命名）

#### Tier 3 — Architecture borrows（[L2] 级，需独立 IVG 之后再 plan）
- T3.1 **执行平面抽象**：起 IVG 评估"`ansispire_features.remote_runner` flag + Runner 角色脚手架"vs"继续单容器"——含 OSS Runner 验证、注册 token 流、目录契约
- T3.2 **Secret 治理 doctrine**：起 IVG 起草 `docs/governance/secrets.md` 明确 5 surface 的职责边界 + 哪些走 IaC / 哪些必须 UI 导入
- T3.3 **API 契约层**：在 `controller/audit/test_rules_contract.py` 旁加 `test_semaphore_api_contract.py`，每个 endpoint 一个最小响应 schema assert
- T3.4 **EDA 引擎选型** [A8]：起 IVG 比较"继续自研 reactor"vs"迁移到 `ansible-rulebook`"——含迁移成本、event schema 对齐、reactor.py 14 个单测的去留

### 6.3 经验教训
1. **W-R13 / W-R18 pre-accept verification 起作用**：本次独立调研发现 8 个 Codex 未提的工程项 + 1 个 Codex 未明确的关键修正（Vault 是 Pro），证明"外部 review 必须独立验证而非直接吸收"的纪律是正确的
2. **官方文档语义可能与发行版本之间存在 1-2 个版本的差**：上游官方 docs 没说 `SEMAPHORE_DB_PATH` 是目录还是文件——必须读 `deployment/docker/server/server-wrapper` 的真实代码才能确认（W-R18 §a: 直接看 upstream/reference projects' actual approach）
3. **架构借鉴的"OSS vs Pro"边界容易混淆**：Runner 基础功能 OSS 但 tag-routing Pro；外部 Vault 集成 Pro——规划路线图前要分清，否则可能把不存在于 OSS 的能力当作可借鉴

---

## 7. 关联验证 (Linked Verification)
- **测试规格**：本 IVG 为只读分析，**无代码改动 → 无新增 TSVS**
- **代码验证**：无（read-only）
- **后续验证**：每个 Tier 1/2/3 项目的 plan-doc 应包含独立 TSVS
- **登记入口**：`docs/reference/investigations/INDEX.md` 追加一行

---
*Generated by Ansispire Investigation Engine | 2026-05-17 | branch: dev*
