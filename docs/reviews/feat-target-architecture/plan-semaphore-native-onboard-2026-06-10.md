# Plan — Semaphore-Native VPS Onboard（去 Worker 化的功能主线闭环）

> **Status**: APPROVED
> **Created**: 2026-06-10
> **Branch**: feat/target-architecture
> **Classification**: [L2] Architecture
> **Supersedes**: `plan-phase-a-onboard-execution-2026-06-07.md`（吸收其 R1/R2 内容，移除 Worker 接线）；同时取代未入库的 change-file 草案 `plan-semaphore-first-wiring-2026-06-09.md`（吸收其 onboard.yml 修复与验证编排，移除 Postgres / API 探针 / 自定义镜像默认化）
> **Approved**: 2026-06-23
> **Updated**: 2026-06-10 — 环境约束修正（Docker daemon 实测可用，W-R24 探针）+ §7 补 testing-governance 同步项；重新呈批
> **Updated**: 2026-06-23 — Saberu 产品方向确认后，本 plan 被定为近期 active execution plan；D2 关闭为 Semaphore UI first，自研 UI/API / 新仓蓝图 deferred，先证明 Semaphore-native audit → onboard → managed-audit `0 changed` 闭环。

---

## §1 Why this plan exists

1. **什么缺失**：Semaphore 作为控制面从未真正跑通过一次 VPS onboard——容器内凭据契约未接线（managed 验证私钥文件不存在、`authorized_keys` 的 `lookup('file')` 在容器内必然失败）、onboard/audit Job Template 未创建、VPS 节点真相还在 repo file inventory 而非 Semaphore static inventory。
2. **为什么重要**：本地 `vps_manager` 已删除，Semaphore 容器内 Ansible 是唯一执行路径。接线不通，目标架构停留在"设计已确认但不可用"，后续所有功能（批量导入、offboard、Worker 回归）都没有可信基线。
3. **为什么现在**：2026-06-10 方向决策——Worker 暂缓（未对外开放、安全非优先），重点转向功能实现。这一刀解除了 R3（Worker blob 无损解析）对 inventory 迁移的前置绑定，功能主线障碍清单缩短为 4 项，全部可立即推进。
4. **Saberu 对齐（2026-06-23）**：产品名已定为 Saberu，短期产品目标是多 VPS 标准化接管/加固/软件安装/服务配置；MVP 操作面已关闭为 **Semaphore UI first**。因此本 plan 是 Saberu MVP 的第一条执行证明链路，不新建自研 UI/API 项目，不绕开 Semaphore。

---

## §2 Current state

**已确认的事实**（2026-06-10 仓内核查 + 既有运行态证据）：

- `IVG-SEMAPHORE-INVENTORY-API §8`（2026-06-06 live probe）：`static` inventory whole-blob CRUD 可用；task-level `environment` JSON string 承载嵌套 `vps_task` 已实测——**无需再探针**。
- `ansible.cfg` 已配置 `collections_path = ~/.ansible/collections:collections`（repo 相对路径，writable-first）；repo 已 vendor `ansible.posix 2.1.0` / `community.general 12.6.0` 等（`collections/ansible_collections/`，与 `requirements.yml` 锁定版本一致）。Semaphore 把 repo 拉到 `/workspace` 后从 repo 根运行 → vendored collections **理论上直接生效**。
- `audit.yml`（68 行）无外部 collection 依赖，官方镜像今天即可运行；`onboard.yml`（553 行）依赖 `ansible.posix.*` + `community.general.ufw`。
- `onboard.yml` 凭据双通道契约：bootstrap 通道走 Semaphore inventory `ssh_key_id`（原生机制）；managed 通道验证在 `onboard.yml:448/535` shell `ssh -i {{ vps_managed.ansible_key.private_key }}`——**执行环境上的私钥文件路径**，容器内不存在。`onboard.yml:30-35` assert 该字段必填。
- `onboard.yml:115` `lookup('ansible.builtin.file', key_item.public_key)` 在容器内求值，`~/.ssh/*.pub` 不存在。
- `controller/semaphore/bootstrap.yml` 已有三处幂等 `POST /templates` 模式（dry-run / remediation / ping）和 placeholder key 创建模式（`REPLACE-VIA-UI`）——新增模板/key 是机械扩展。
- 现有 inventory：`production`（id 1）/ `targets-managed`（id 2）均为 `type: "file"`，有现存模板消费者。
- DB 后端：SQLite，维持现状（`IVG-SEMAPHORE-DB-BACKEND` 2026-06-10 结论：Postgres 归口 TASK-003）。
- 测试面现状：`make vps-lifecycle-syntax`（已在 `verify` 门）、`make test-api-contract`（L4，跑 `bootstrap_preflight.yml`，需 Docker）、`controller-loop-smoke` 提供 API-触发+轮询的 smoke 模式范本。**无任何"Semaphore 执行 VPS playbook"的功能测试或 TSVS 规格**。

**假设（未运行态验证，Phase 0 关闭）**：

- Semaphore task 运行时读取 repo `ansible.cfg` 并解析 vendored collections（依据 cwd 推断，未实测）。

**环境约束**（2026-06-10 实测探针，per `.agents/rules/environment-truth.md`）：本机 **Docker daemon 可用**（server 29.5.3，`ansispire-semaphore` 容器运行中）——Phase 0 探针、`make controller-*`、`make test-api-contract` 均可由 agent 本机执行。仍需用户的部分：Key Store 真实私钥注入（UI 操作，密钥材料不经 agent）、测试 VPS 拨备。`ansible` 不在本机 PATH（容器内 ansible 是执行路径，与架构一致）。缺证据的 gate 标 blocked 不标 passed。

**已决策**（2026-06-10，用户确认）：

- D-A：凭据模型 = fleet-wide 单 keypair（原 phase-a Option A）；私钥经 compose volume mount 投递到容器固定路径（不进镜像、不进 git）。
- D-B：inventory 策略 = bootstrap.yml 新建 `vps-fleet` static inventory 专供 VPS 生命周期；现有 `production` / `targets-managed` file inventory **不动**，绕开消费者分析风险。
- D-C：Worker 推迟正式记录进 TODO.md / backlog（本 plan 批准时同轮执行）。

---

## §3 Scope

**In scope**：

- Phase 0：vendored collections 容器内解析的运行态确认；Worker-deferral 账本同步。
- Phase 1：`bootstrap.yml` 新增 `vps-fleet` static inventory + fleet-key 占位 + `VPS Audit` 模板 + audit Environment；对测试 VPS 跑通 audit。
- Phase 2：`onboard.yml` 双修复（`public_key_content` 内联分支 + managed 验证私钥 volume mount 路径）；examples 同步；`VPS Onboard` 模板 + Environment 进 bootstrap.yml。
- Phase 3：真实 onboard 闭环（可重装 VPS）+ managed 通道幂等 audit。
- 测试基线（贯穿）：`bootstrap_preflight.yml` 扩展断言、新增 TSVS 规格、新增 `make controller-vps-smoke` 回归目标——作为后续功能迭代的回归基线。

**Out of scope**：

- Worker 全部 R 项（R3–R12，含安全/observability）——deferred，回归时机在 onboard 闭环后重估。
- Postgres 迁移（IVG-SEMAPHORE-DB-BACKEND 已定，归 TASK-003）。
- `production` / `targets-managed` file inventory 迁移或退役。
- Offboard / reverse playbook（TASK-010）、批量导入。
- EDA reactor 参数传递改造。

**待决策**：无——D-A/D-B/D-C 已全部关闭。

---

## §4 Implementation plan

### Phase 0 — 账本同步 + collections 运行态确认

**Goal**：批准时效的文档同步落地；关闭 §2 唯一未验证假设。
**Pre-condition**：本 plan 获批准；本机 Docker / Semaphore 运行可用（2026-06-10 已实测，执行前按 environment-truth 复探）。

**Steps**：

1. 账本同步（本 plan 批准当轮，独立可提交）：
   - `TODO.md` target-architecture 条目重写：入口指向本 plan；Worker 各项标 deferred；下一步改为 Phase 0–3。
   - `backlog-2026-06-07.md` 顶部加 dated note：R3–R12 deferred（2026-06-10 方向决策），R1/R2 由本 plan 吸收。
   - `plan-phase-a-onboard-execution-2026-06-07.md` Status 改 `SUPERSEDED`，链接本 plan。
2. collections 解析探针（agent 本机执行；非破坏、无需目标 VPS）：
   ```bash
   make controller-up
   # 在 Semaphore 容器内、repo checkout 目录下做 syntax-check：
   # FQCN 无法解析时 syntax-check 即失败，正好验证 collections 解析路径
   docker exec -w /workspace <semaphore-container> \
     ansible-playbook --syntax-check playbooks/vps/onboard.yml
   ```
   （若容器内尚无 repo checkout，先在 UI 跑一次任意现有模板让 Semaphore 拉取，或 `docker exec git clone`。）

**探针结果决策表**：

| 探针结果 | 下一步 |
|---|---|
| syntax-check 通过（FQCN 全部解析） | 无镜像工作，直接进 Phase 1 |
| 报 `couldn't resolve module` | 启用 fallback：`controller/semaphore/Dockerfile` 基于官方镜像 `ansible-galaxy collection install -r requirements.yml` 烘焙，compose `image:` 改 `build:`；完成后重跑探针再进 Phase 1 |

**Gate**：探针结论记录（chat + Phase 3 changelog 引用）；fallback 若启用，代码改动经用户 review。
**Deliverables**：账本同步 commit；探针结论记录。

---

### Phase 1 — audit 先通（最早可演示功能点）

**Goal**：一台测试 VPS 经 Semaphore 跑通 `audit.yml`（bootstrap 通道 root@22）。
**Pre-condition**：Phase 0 Gate 通过；有一台 root SSH 可达的测试 VPS；fleet keypair 已生成（用户持有）。

**Steps**：

1. `controller/semaphore/bootstrap.yml` 扩展（照抄现有幂等模式）：
   - 新建 key `vps-fleet-key`（type ssh，placeholder `REPLACE-VIA-UI`，沿用 `ssh_lab_key` 模式）。
   - 新建 inventory `vps-fleet`（`type: "static"`，初始 blob `"[vps_targets]\n# add hosts via Semaphore UI/API"`，`ssh_key_id` 指向 `vps-fleet-key`）。
   - 新建 Environment `vps-audit-env`：JSON 含 `vps_task.checks/thresholds`（取自 `playbooks/vps/examples/`）。
   - 新建模板 `VPS Audit`：`playbook: playbooks/vps/audit.yml`，inventory `vps-fleet`，repo 复用现有 repository 资源。
2. `controller/semaphore/bootstrap_preflight.yml` 扩展断言：`GET /inventory/{id}` 响应含 `inventory` 字段且 `type == static`；`VPS Audit` 模板存在。
3. 执行（agent 本机：`make controller-bootstrap`；用户：UI 替换 `vps-fleet-key` 真实私钥——密钥材料不经 agent）→ `vps-fleet` inventory 加测试主机（`ansible_user=root ansible_port=22`）→ 运行 `VPS Audit`。

**Gate**：audit task `status=success`，日志可见 disk/memory/service 检查输出（用户确认）。
**Deliverables**：`bootstrap.yml` / `bootstrap_preflight.yml` diff；用户侧 audit 成功证据（脱敏，入 Phase 3 changelog）。

---

### Phase 2 — onboard 代码修复

**Goal**：`onboard.yml` 在容器执行环境内技术可运行。
**Pre-condition**：Phase 1 Gate 通过。

**Steps**：

1. `playbooks/vps/onboard.yml:110-118` `authorized_keys` task 加显式分支（不用 `default(lookup(...))`——Jinja2 传参时急切求值，`public_key_content` 存在时 lookup 仍会执行并报错）：
   ```yaml
   key: |
     {% for key_item in vps_managed.authorized_keys %}
     {% if key_item.public_key_content is defined %}
     {{ key_item.public_key_content }}
     {% else %}
     {{ lookup('ansible.builtin.file', key_item.public_key) }}
     {% endif %}
     {% endfor %}
   ```
2. managed 验证私钥投递：`controller/semaphore/docker-compose.yml` 加只读 volume mount（宿主路径 gitignored，如 `controller/semaphore/secrets/vps-fleet-key` → 容器 `/etc/ansispire/keys/vps-fleet-key:ro`）；`.env.example` / `.gitignore` 同步注释与排除；onboard Environment JSON 中 `vps_task.managed.ansible_key.private_key` 填该容器路径。
3. `playbooks/vps/examples/onboard.minimal.yml` / `onboard.standard.yml`：`authorized_keys` 改 `public_key_content` 内联示例；`ansible_key.private_key` 注明容器路径约定。
4. `bootstrap.yml` 新增模板 `VPS Onboard`（`playbooks/vps/onboard.yml`，inventory `vps-fleet`）+ Environment `vps-onboard-env`（JSON 参照 examples）；`bootstrap_preflight.yml` 断言模板存在。
5. 静态验证：`make vps-lifecycle-syntax && make lint`。

**Gate**：gate-2 全绿 + 用户 review diff。
**Deliverables**：上述 5 项 diff。

---

### Phase 3 — 真实 onboard 闭环

**Goal**：可重装 VPS 完成 onboard 进入 managed 态，audit 在 managed 通道幂等重跑。
**Pre-condition**：Phase 2 Gate 通过；可重装测试 VPS（root SSH 可达、保留 provider VNC/console 兜底）；fleet 公钥已按 D-A 预置或经 bootstrap 通道首跑安装。

**Steps**（用户 shell + Semaphore UI）：

1. `make controller-bootstrap`（拾取 Phase 2 新资源）。
2. 运行 `VPS Onboard` → 观察 task 日志至 `status=success`。
3. `vps-fleet` inventory 该主机连接参数切 managed 通道（`ansible_user=<managed_user> ansible_port=<managed_port>`）；`vps-fleet-key` 已是同一把 fleet key（D-A），模板无需换 key。
4. 重跑 `VPS Audit` → `status=success` 且 **0 changed**（幂等证明）。
5. 回归基线落地：
   - 新增 `make controller-vps-smoke`：API 触发 `VPS Audit` 模板 + 轮询 task status（照抄 `controller-loop-smoke` 模式）——后续功能迭代的可重复回归钩子。
   - 新增 TSVS `docs/reference/test-specs/vps-semaphore-native-e2e.md`（含 pass conditions：onboard success / managed 可达 / audit 0-changed）+ `INDEX.md` 登记。
6. 写 `round10-YYYY-MM-DD.changelog.md`（脱敏终端日志；含 Phase 0 探针结论与 Phase 1 audit 证据）。

**Gate**：步骤 2 / 4 全部 success（步骤 4 同时 0 changed）+ `controller-vps-smoke` 首跑通过 → 用户确认关闭本 plan。
**Deliverables**：Makefile diff、TSVS 文件、round10 changelog。

---

## §5 Verification

| Phase | 验证方法 | 通过条件 | 证据 artifact |
|---|---|---|---|
| 0-probe | 容器内 `ansible-playbook --syntax-check onboard.yml` | exit 0，无 unresolved FQCN | round10 changelog 引用 |
| 0-ledger | `git diff` 复核 + 链接可达 | TODO/backlog/phase-a 三处一致 | 同步 commit |
| 1 | `make controller-bootstrap` 幂等重跑 + `make test-api-contract`（扩展断言）+ UI 跑 `VPS Audit` | bootstrap 重跑无 fail；preflight 断言绿；audit `status=success` | round10 changelog（脱敏） |
| 2 | `make vps-lifecycle-syntax && make lint` | 全绿 | round10 changelog |
| 3 | UI 跑 onboard + audit；`ssh <managed_user>@<VPS> -p <managed_port>`；`make controller-vps-smoke` | onboard success；managed SSH 可登录；audit success 且 0 changed；smoke 通过 | round10 changelog（脱敏）+ TSVS |

**测试基线映射**（本 plan 成果 ↔ 持续迭代的回归面）：

| 成果 | 守护它的测试 | 状态 |
|---|---|---|
| VPS playbook 语法/契约 | `make vps-lifecycle-syntax`（已在 `verify` 门） | 已有 |
| bootstrap.yml 控制面资源契约 | `make test-api-contract`（`bootstrap_preflight.yml` 扩展断言） | 本 plan 扩展 |
| Semaphore→VPS 执行链路 | `make controller-vps-smoke`（新增） | 本 plan 新增 |
| e2e 行为规格 | TSVS `vps-semaphore-native-e2e.md`（新增） | 本 plan 新增 |

后续任何 onboard/audit 功能改动的最小回归集 = `vps-lifecycle-syntax` + `test-api-contract` + `controller-vps-smoke`，全部命令化、不依赖 UI 手工。

---

## §6 Risks and fallbacks

| Risk | Likelihood | Impact | Mitigation | Fallback |
|---|---|---|---|---|
| Phase 0 探针失败（collections 不解析） | low-med | med | ansible.cfg 路径机制已静态核实 | Dockerfile 烘焙 fallback（决策表内置，版本走 `requirements.yml` 锁定） |
| `onboard.yml` 中途失败致目标 SSH 中间态 | med | high | 仅用可重装 VPS；UFW 规则保持 bootstrap 口直到最终验证（`onboard.yml:285-294` 已实现） | bootstrap key 重登手工恢复 sshd；或重装 VPS |
| fleet 单 key 单 inventory `ssh_key_id` 限制并发异 key onboard | low（单租户） | low | D-A 已知取舍，记录在案 | 需要时回归 phase-a Option B/C 评估 |
| volume mount 私钥的宿主文件权限/泄漏 | low | high | 宿主路径 gitignored + `:ro` mount + detect-secrets 在 `verify` 门 | 泄漏即轮换 fleet key（Key Store 重录成本 1 把） |
| bootstrap_preflight 扩展引入 false-negative | low | low | 断言独立 task，可 `-e skip_preflight=true` | 跳过后修断言 |
| 环境能力随时间漂移（如 Docker 可用性变化） | low | med | 关键 gate 执行前按 `environment-truth.md` 重新探针，不信记忆 | 探针失败时降级为用户 shell 委托执行，证据缺失标 blocked |

---

## §7 Post-completion checklist

- [ ] `ARCHITECTURE.md` — VPS 生命周期入口矩阵更新（Worker deferred；UI/API + 手工为现役入口）
- [ ] `docs/reference/feature-map/vps-lifecycle.md` + `INDEX.md` — 模板/inventory/凭据模型同步（触及 `controller/` + `playbooks/` + `Makefile`，INDEX 为 Sync Guard 强制项）
- [ ] `CHANGELOG.md [Unreleased]` — 新 make 目标 + onboard 契约变化（`public_key_content`）为 user-visible
- [ ] `docs/operations/` — onboard runbook（fleet key 准备、容器路径约定、smoke 用法）
- [ ] `docs/governance/testing-governance.md` — §3 决策树 `playbooks/vps/**` / `controller/semaphore` 行补 `controller-vps-smoke` 功能门；§4 命令表登记新 make 目标（per `docs-sync.md` 新增测试面同步规则）
- [ ] `TODO.md` — Phase 0–3 标完成；下一步改为 Worker 回归评估 / TASK-010
- [ ] `round10-YYYY-MM-DD.changelog.md`
- [ ] 本 plan `§0 Status` → `COMPLETED` + `> **Completed**: YYYY-MM-DD`
- [ ] 解锁：Worker R 项回归重估（接线已验通的模板 id 直接可用）；TASK-010 offboard；批量导入

---

*Plan 作者：方向重梳理对话 2026-06-10（Worker 暂缓决策 + D-A/D-B/D-C 关闭）| Owner branch：`feat/target-architecture`*
