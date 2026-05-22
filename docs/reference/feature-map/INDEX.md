# docs/reference/feature-map/INDEX.md — 项目功能索引 (Functional Index)

> 本文件是 Ansispire 项目的"功能地图"，记录当前系统的功能全貌、状态以及已知边界。
> 它是项目的 **操作真理 (Operational Truth)** 之一，用于对齐人工操作与 AI 协作的上下文。
>
> **同步纪律**：动 `roles/` / `playbooks/` / `controller/` / `extensions/eda/` / `inventory/` / `Makefile` / `config/manifest.yml` 的 PR **必须**同回合更新本文件（CLAUDE.md §0 Sync Guard #5）。

---

## 1. Ansible 角色 (Roles)

| 角色 | 状态 | 核心功能 |
| :--- | :--- | :--- |
| **`common`** | ✅ 完整 | 系统基线：包安装 / 时区 (UTC) / app 用户 + 目录 / SSH 加固 / UFW 防火墙（含 R5/R6 loopback allow）/ sysctl 调优 / MOTD / fail2ban 检测。Debian + RHEL 双家族任务文件 |
| **`webserver`** | ✅ 完整 | Nginx 安装 + 配置 + 多 vhost (`webserver__vhosts` 列表) + default index + handlers + 配置 syntax 自检 |
| **`database`** | ✅ 完整 | MySQL 安装 + `my.cnf` 模板（`ansible_managed` 包 `comment` filter）+ root 密码幂等设置 (`check_implicit_admin: true`) + 库/用户创建 + 备份脚本（可选） |
| **`ansispire_hub`** | ✅ 完整 | Hub 部署：rsync 代码到 `/opt/ansispire/`（21 项 exclude）+ 渲染 `.env`（端口/镜像/admin）+ 启 Semaphore docker stack + EDA token mint/复用（state 在 `/var/lib/ansispire/state/`） |
| **`ansispire_audit`** | ✅ 完整 | 审计链路部署：relay / sink / reactor 容器栈到 hub |
| **`infra_baseline`** | ✅ Debian + RHEL | Debian 路径（Docker repo + 管理用户 + sudoers + ssh key + 可选 swap）；**RHEL 路径**（TASK-007 round 1，2026-05-19）：dnf docker repo + python3.11 pivot + SELinux container_manage_cgroup + wheel 组；**Alpine 路径仍为 fail stub**（TASK-007.B）。详见 [`multi-os-fleet.md`](multi-os-fleet.md) |
| **`geerlingguy.docker`** | ✅ Vendor | 第三方角色，含本项目特定补丁（FQCN / octal 修复，见 `docs/governance/vendor-patches.md`） |

---

## 2. 剧本矩阵 (Playbooks)

| 剧本 | 分类 | 用途 |
| :--- | :--- | :--- |
| `site.yml` | **全栈** | 主入口：`common (all) → webserver (webservers) → database (dbservers)` |
| `deploy_hub.yml` | **控制面** | Hub 部署：`infra_baseline → ansispire_hub → ansispire_audit` |
| `deploy_target.yml` | **数据面** | TASK-007 Target 部署：仅 `infra_baseline` 应用到 `[targets:children]`（4 VPS, Debian+RHEL） |
| `ping_targets.yml` | **数据面** | TASK-007 全 fleet 连通性探针，对应 Semaphore "Ping all targets" 模板 |
| `manifest_sync.yml` | **工具** | SSOT 同步：把 `config/manifest.yml` 渲染到 `controller/semaphore/.env` 的 managed block |
| `rolling_update.yml` | **运维** | 滚动更新（`serial: 1` 模式） |
| `remediation/disk_cleanup.yml` | **自愈** | ✅ EDA：磁盘清理（实战可用，Debian 路径） |
| `remediation/fix_nginx.yml` | **自愈** | ✅ EDA：Nginx 服务重启（剧本就绪，当前 EDA 规则未自动触发；可手工调） |
| `remediation/db_failover.yml` | **自愈** | ⚠ Placeholder（仅 debug，待 TASK-008 真实化） |
| `advanced_patterns.yml` | **示例** | 高级 pattern 教学（block/rescue/handler 等），非生产功能 |
| `vault_demo.yml` | **示例** | Vault 用法演示，非生产功能 |

### 2.1 插件内剧本

| 剧本 | 插件 | 用途 |
| :--- | :--- | :--- |
| `plugins/vps_runner/playbooks/onboard.yml` | `vps_runner` | host_vars 驱动的 VPS 纳管：bootstrap SSH → managed user/key/sudo → UFW/fail2ban → 非 22 SSH 管理端口 |
| `plugins/vps_runner/playbooks/modify.yml` | `vps_runner` | `vps_changes` extravar 驱动的修改：包 / UFW / fail2ban / network_tuning |
| `plugins/vps_runner/playbooks/audit.yml` | `vps_runner` | per-host 健康探测：ping / uptime / disk / memory / OS facts |
| `plugins/vps_runner/playbooks/remove.yml` | `vps_runner` | 默认仅删本地 inventory；`--cleanup-remote` 才剥离远端 sshd drop-ins **并反向还原 `# ANSISPIRE-COMMENTED:` 注释的 sshd_config 指令（Round 5）** |

---

## 3. 控制面模块 (Controller / Hub-side)

### 3.1 Semaphore Web UI (`controller/semaphore/`)
- **功能**：基于 Docker Compose 的可视化管理界面（默认 host 端口 3320）
- **自动化**：`bootstrap.yml` 实现零点击创建 Project / Inventory / Environment / Job 模板 / RBAC
- **API 契约保护 (post-WU-4)**：`bootstrap_preflight.yml` 在 `bootstrap.yml` 顶部 `import_playbook`。schema mode（默认 ~2 s）验证 `/api/auth/login` + `/api/projects` + `/api/users` 的字段形状；full mode（`make test-api-contract`，~30–60 s）在临时 `__preflight__` 项目上走完所有 5 个 project-scoped GETs + token mint。CI 矩阵 `[pinned, latest]` 跑 full mode，`latest` 配 `continue-on-error` —— 上游 schema 漂移作为预警，不阻断主合并。`-e skip_preflight=true` 可逐次跳过（仅用于刻意探测未 bootstrap 的实例的测试）

### 3.2 审计与自愈链路 (`controller/audit/`)
- **`sink.py`** — Python 轻量 HTTP 接收器（host 端口 3310，container 内 3010；`AUDIT_PORT` 可覆盖），将 Semaphore webhook POST 固化为追加型 `events.jsonl`
- **`relay.py`** — Python，cursor-based 分页拉 Semaphore tasks → POST 到 sink；重启可续传（heartbeat 60 s）
- **`reactor.py` (v2.3)** — Python，tail `events.jsonl`，匹配 `rules.json`，触发自愈：
  - Bearer Token 身份验证（无明文 admin）
  - 动态模板解析：`template_name → template_id`
  - 冷却期（per-rule cooldown，默认 600 s）
  - 启动 banner：读 `events.schema.json` 输出 `event schema: <$id>@<version>`
  - `enabled: false` 软禁用
- **`e2e/`** — 一次性 docker-compose 栈 + `run.sh`，端口 3320 隔离命名（`*-e2e` 后缀），跑完默认 leave-running 给手动检查

### 3.3 RBAC 模型 (`controller/rbac/`)
- **三角色**：`owner`（全权限）/ `task_runner`（仅运行）/ `guest`（仅查看）
- **验证**：`smoke.sh` 每次 deploy 后跑（也是 `make controller-rbac-smoke` 入口）

### 3.4 插件层 (`plugins/`)
- **`vps_runner`** — `ansible-runner` 原生范式的 VPS 生命周期插件：
  - 执行：`ansible_runner.run()` + 标准 inventory `inventory/vps_runner/<env>/`，无 subprocess wrapper / 无自写 callback / 无自定义 state
  - 状态：`host_vars/<alias>.yml`（`vps_runner.status` / `last_run` / `updated_at` 由 CLI 维护）
  - 子命令：`list` / `audit` / `onboard` / `modify` / `remove`
  - 测试：22 cases（21 unit + 1 ansible-runner integration vs TEST-NET-1）
  - 详见 [`vps-runner.md`](vps-runner.md)

---

## 4. EDA 规则库 (Event-Driven Automation)

实际定义在 [`extensions/eda/rules.json`](../../../extensions/eda/rules.json)（schema 在 [`extensions/eda/events.schema.json`](../../../extensions/eda/events.schema.json)）：

| 规则 | 触发条件 | 响应 | 状态 |
| :--- | :--- | :--- | :--- |
| **Remediation: Disk Full** | event `description_contains: "Disk Full"` | Semaphore template `Auto Remediation: Disk Cleanup` → `disk_cleanup.yml` | ✅ enabled，cooldown 600 s |
| **Remediation: DB Connection Failure** | event `description_contains: "database connection failed"` | webhook + `Auto Remediation: DB Failover` template | ⚠ enabled=false（playbook 是 placeholder，待 TASK-008） |

---

## 5. Inventory & Target 分类

| 环境 | 用途 | 状态 |
| :--- | :--- | :--- |
| `inventory/dev/` | 本地开发，`localhost ansible_connection=local` | ✅ |
| `inventory/stag/` | 预发布，结构对齐 prod | ⚠ 占位结构（无真实 host） |
| `inventory/prod/` | 生产，含 `hub_management` + `targets_debian` 等组 | ✅ 结构就绪，等真机接入 |
| `inventory/local/` | Vault 容器（`vault.yml.example`） | ✅ |
| `inventory/dynamic/` | 动态 inventory 占位 | — 未启用 |

**Target Taxonomy**（`inventory/prod/hosts.ini` 与 `inventory/hosts.ini`）：
- **管理节点组**：`[hub_local]`（工作站）/ `[hub_remote]`（远端 VPS — ⚠ 当前 `ans-hk01` 引用的 IP 已被 OS 重装抹掉，待清理）/ `[hub:children]`（联合）
- **被管节点组**（TASK-007 round 1 已接入，2026-05-19）：
  - `[targets_debian]` = d13 (Debian 13) + u24 (Ubuntu 24.04)
  - `[targets_rhel]` = rocky9 (Rocky 9.7) + alma9 (AlmaLinux 9.7)
  - `[targets_alpine]` = 空（TASK-007.B 占位）
  - `[targets:children]` + `[targets:vars]` —— 详见 [`multi-os-fleet.md`](multi-os-fleet.md)

---

## 6. SSOT 配置层

- **`config/manifest.yml`** —— 端口、镜像 tag、admin 等的**唯一来源**
- **`make manifest-sync`** —— 把 manifest 渲染到 `controller/semaphore/.env` 的 managed block；其他 secrets 不动
- **覆盖范围**：所有 docker-compose `${VAR}` interpolation + Ansible vars_files（`deploy_hub.yml`、`controller/semaphore/bootstrap.yml`）+ CI 测试栈
- **写法纪律**：在 manifest 里改一处 → 散播到所有消费者；不允许在 compose / playbook 里硬编码端口或镜像 tag

---

## 7. 测试基础设施 (Test Matrix)

完整治理见 [`docs/governance/testing-governance.md`](../../governance/testing-governance.md)（含 §9 测试卫生）+ [`docs/governance/test-plan.md`](../../governance/test-plan.md)（surface × quality 矩阵 + 9 G 缺口）。

- **L1–L3（pytest，`controller/audit/test_*.py`）**：28 cases + 1 schema gate
  - L1 reactor unit 14 / L2 rules contract 9 / L3 reactor component 5
  - L1 schema gate `test-rules-schema`：`extensions/eda/rules.json` ↔ `extensions/eda/rules.schema.json`（Draft-07，inline `jsonschema.validate`）
  - 入口：`make test-eda`（< 1 s）— 已含 schema gate
- **L4（disposable e2e）**：`controller/audit/e2e/run.sh` 真 docker 栈
  - 入口：`make test-eda-e2e`（~60 s）
- **L4（API contract）**：`controller/semaphore/preflight/run.sh` 真 docker 栈，纯 Semaphore（无 audit stack）
  - 入口：`make test-api-contract`（~30–60 s）；CI 矩阵 `[pinned, latest]`
- **L5（Molecule）**：4 场景跨 Ubuntu 22.04 + Debian 12
  - `common` / `database` / `webserver` / `full-stack`，各 8 阶段 destroy → … → destroy
  - 入口：`make molecule-all` 串行（CI matrix 并行）
  - 单独：`molecule test -s <scenario>`
  - 断言规格：[`docs/reference/test-specs/molecule-{common,webserver,database,full-stack}.md`](../test-specs/)
- **CI**（`.github/workflows/ci.yml`）：6 job —— `yamllint` → `{ansible-lint, syntax-check}` → `{dry-run, molecule matrix}`，外加独立 `detect-secrets`；触发 push `dev|master|hotfix/*` + PR `dev|stg|master`；Dependabot 周维度提依赖升级 PR
- **测试卫生**：失败的 L4/L5 必须先清 ephemeral state（`~/.ansible/tmp/molecule.*`）+ leave-running stack 才能复测——见 testing-governance.md §9
- **VPS Runner**：`make test-vps-runner` 跑 121 个 unit 测试（pure helpers + CLI dispatch + R9 验证器 + R10 list_hosts chokepoint + R11 wizard 8 字段 / 临时密钥生命周期 / 同名 alias 4 选项菜单 / passwords-dict 注入）；`make test-vps-runner-integration` 跑 3 个 integration 测试（真调 ansible-runner 打 TEST-NET-1 + P1.3 envvars allowlist canary + P1.4 PATH 自足 regression guard，~33 s）；`make vps-runner-syntax` 覆盖 onboard/modify/remove/audit 四个 playbook。R11 起首次接入唯一推荐入口是 wizard（`make vps-add-host` 无参数），Make wrapper：`vps-list / vps-audit / vps-add-host / vps-reonboard / vps-modify / vps-remove`（注：`vps-onboard` 在 R11 弃用——其 `--ask-pass --ask-become-pass` 经 ansible-runner 死锁；首次走 wizard，重 onboard 走 `vps-reonboard`）。

---

## 8. Make UX 层（操作员入口）

| 类别 | 目标 | 说明 |
| :--- | :--- | :--- |
| **质量闸口** | `verify-quick` / `verify` / `verify-full` | commit / push / release 三档（~3 s / ~30–60 s / ~10–20 min） |
| **部署** | `deploy-{dev,stag,prod}` + `-check` | 按环境部署，`-check` 是 dry-run |
| **Hub 部署** | `hub-deploy [HUB_NODE=local|remote|all]` + `hub-deploy-check` | Path A 入口 |
| **Target 部署** | `target-deploy [TARGET_NODE=debian\|rhel\|all\|<alias>] [ANSIBLE_USER=root]` + `target-deploy-check` + `target-ping` | TASK-007 managed fleet 入口；ANSIBLE_USER 是 fresh-host bootstrap knob |
| **Controller 生命周期** | `controller-{up,down,logs,reset,bootstrap}` | Path B 入口 |
| **审计链路** | `controller-audit-{up,down,tail,stats}` | sink + relay 容器管理 |
| **测试** | `test-eda*` 三 L 拆分 / `test-eda-e2e` / `molecule-all` / `vps-manager-syntax` / smoke 系列 | 见 §7 |
| **VPS Runner — 测试 / 语法** | `test-vps-runner` / `test-vps-runner-integration` / `vps-runner-syntax` | 33 unit + 3 integration + 4 playbook syntax-check |
| **VPS Runner — 日常 ops** | `vps-list` / `vps-audit` / `vps-add-host` / `vps-onboard` / `vps-modify` / `vps-remove` | Round 6 起 6 个 daily wrapper；都接 `ENV=dev` 默认；`add-host` / `onboard` / `modify` / `remove` 要 `ALIAS=`；`add-host` 额外要 `IP=`；`modify` 要 `ARGS='--add-package=...'` |
| **Vault** | `vault-edit FILE=...` / `vault-encrypt` | Vault 操作包装 |
| **EE** | `ee-build` / `navigator` / `navigator-local` | Execution Environment 模式 |
| **SSOT** | `manifest-sync` / `ports-sync` (deprecated alias) | 见 §6 |

---

## 9. 当前能力边界

### 能做什么 ✅
- 一键部署完整 LAMP 基线到 Debian/Ubuntu（Tier 1）
- 自动化构建带自愈能力的控制面（Path A 真部署 / Path B 本地 dev）
- 基于审计日志的闭环自愈（当前实战级：**Disk Full**；剧本就绪未挂规则：Nginx restart）
- 工业级 lint + syntax + unit + component + e2e + molecule 测试链
- Hub 远端部署（含 SSH 用户拨备 / rsync 代码同步 / EDA token 持久化）
- **VPS Runner**：ansible-runner 原生范式的 VPS 生命周期管理（list / audit / onboard / modify / remove），标准 inventory + 强制非 22 SSH 管理端口，22 tests green incl. real ansible-runner integration
- 失败安全：dry-run 对全栈兼容（check-mode safety）

### 不能做什么 ❌ / 半完成 ⚠
- ✅ **Rocky/AlmaLinux 9 真实部署**（TASK-007 round 1，2026-05-19）；❌ Alpine 仍 fail stub（TASK-007.B）
- ❌ **数据库真 failover**（playbook placeholder + EDA rule disabled，待 TASK-008）
- ❌ **Prometheus 监控集成**（待 TASK-002）
- ❌ **Multi-node Semaphore HA + DB 升级 SQLite→PG**（待 TASK-003）
- ⚠ **Stag 环境真机**（结构就绪等接入）
- ⚠ **多 OS target fleet**（占位组就绪，等 4 台 VPS 上线）
- ⚠ **`molecule/hub/` scenario**（hub role 目前无独立 molecule 测试，靠 `make hub-deploy-check` 间接 dry-run）
- ⚠ **VPS Runner 实机并发**（22 tests + ansible-runner integration green；3 节点真并发实测因 dev VPS SSH 阻塞待恢复后验收 plan §1.4）

---
*最后更新：2026-05-16（Round 4-b：vps_manager cutover）| 对应分支：`feat/vps-manager-v2`*
