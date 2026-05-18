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
| **`infra_baseline`** | ⚠ 部分 | Debian 路径已实现（Docker repo + 管理用户 + sudoers + ssh key + 可选 swap）；**RHEL/Alpine 路径为 Fail Stub**（待 TASK-007 真实化） |
| **`geerlingguy.docker`** | ✅ Vendor | 第三方角色，含本项目特定补丁（FQCN / octal 修复，见 `docs/governance/vendor-patches.md`） |

---

## 2. 剧本矩阵 (Playbooks)

| 剧本 | 分类 | 用途 |
| :--- | :--- | :--- |
| `site.yml` | **全栈** | 主入口：`common (all) → webserver (webservers) → database (dbservers)` |
| `deploy_hub.yml` | **控制面** | Hub 部署：`infra_baseline → ansispire_hub → ansispire_audit` |
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
| `plugins/vps_manager/playbooks/onboard.yml` | `vps_manager` | VPS 纳管/重装后重新纳管：bootstrap SSH → managed user/key/sudo → UFW/fail2ban → 非 22 SSH 管理端口 |
| `plugins/vps_manager/playbooks/modify.yml` | `vps_manager` | 已纳管 VPS 的包、防火墙、fail2ban、网络参数修改 |
| `plugins/vps_manager/playbooks/audit.yml` | `vps_manager` | VPS 健康巡检（磁盘 / 内存 / failed services / reboot marker） |
| `plugins/vps_manager/playbooks/remove.yml` | `vps_manager` | 本地取消纳管为主，远端清理 opt-in |
| `plugins/vps_manager/playbooks/docker_host.yml` | `vps_manager` | 安装 Docker Engine 与 daemon 安全默认值 |
| `plugins/vps_manager/playbooks/deploy_compose.yml` | `vps_manager` | 上传并运行 Compose，非公网模式强制 `127.0.0.1` 绑定 |

---

## 3. 控制面模块 (Controller / Hub-side)

### 3.1 Semaphore Web UI (`controller/semaphore/`)
- **功能**：基于 Docker Compose 的可视化管理界面（默认 host 端口 3320）
- **自动化**：`bootstrap.yml` 实现零点击创建 Project / Inventory / Environment / Job 模板 / RBAC

### 3.2 审计与自愈链路 (`controller/audit/`)
- **`sink.py`** — Python 轻量 HTTP 接收器（host 端口 3330），将 Semaphore webhook POST 固化为追加型 `events.jsonl`
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
- **`vps_manager`** — YAML task 驱动的 VPS 生命周期插件：
  - inbox 生命周期：`pending → processing → done|failed`
  - 长期状态：`runtime/state/vps_inventory.yml`
  - 安全策略：拒绝内联密码、强制 managed SSH 端口非 22、Ansible 专用 key 与个人 key 分离、active alias 重复 onboard 拒绝、归档脱敏
  - 扩展面：`onboard` / `recover` / `modify` / `audit` / `remove` / `docker_host` / `deploy_compose`
  - 详见 [`vps-manager.md`](vps-manager.md)

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
- **管理节点组**：`[hub_local]`（工作站）/ `[hub_remote]`（远端 VPS）/ `[hub:children]`（联合）
- **被管节点占位组**：`[targets_debian]` / `[targets_rhel]` / `[targets_alpine]` —— 等 TASK-007 接入真实 VPS

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
- **L5（Molecule）**：4 场景跨 Ubuntu 22.04 + Debian 12
  - `common` / `database` / `webserver` / `full-stack`，各 8 阶段 destroy → … → destroy
  - 入口：`make molecule-all` 串行（CI matrix 并行）
  - 单独：`molecule test -s <scenario>`
  - 断言规格：[`docs/reference/test-specs/molecule-{common,webserver,database,full-stack}.md`](../test-specs/)
- **CI**（`.github/workflows/ci.yml`）：6 job —— `yamllint` → `{ansible-lint, syntax-check}` → `{dry-run, molecule matrix}`，外加独立 `detect-secrets`；触发 push `dev|master|hotfix/*` + PR `dev|stg|master`；Dependabot 周维度提依赖升级 PR
- **测试卫生**：失败的 L4/L5 必须先清 ephemeral state（`~/.ansible/tmp/molecule.*`）+ leave-running stack 才能复测——见 testing-governance.md §9
- **VPS Manager**：`make test-vps-manager` 覆盖本地任务生命周期、inventory/SSH config、脱敏、防重复和 compose 暴露 guard；`make vps-manager-syntax` 用原生 Ansible syntax-check 覆盖插件 action playbook。

---

## 8. Make UX 层（操作员入口）

| 类别 | 目标 | 说明 |
| :--- | :--- | :--- |
| **质量闸口** | `verify-quick` / `verify` / `verify-full` | commit / push / release 三档（~3 s / ~30–60 s / ~10–20 min） |
| **部署** | `deploy-{dev,stag,prod}` + `-check` | 按环境部署，`-check` 是 dry-run |
| **Hub 部署** | `hub-deploy [HUB_NODE=local|remote|all]` + `hub-deploy-check` | Path A 入口 |
| **Controller 生命周期** | `controller-{up,down,logs,reset,bootstrap}` | Path B 入口 |
| **审计链路** | `controller-audit-{up,down,tail,stats}` | sink + relay 容器管理 |
| **测试** | `test-eda*` 三 L 拆分 / `test-eda-e2e` / `molecule-all` / `vps-manager-syntax` / smoke 系列 | 见 §7 |
| **VPS 管理插件** | `vps-new` / `vps-submit` / `vps-manager-init` / `vps-manager-process` / `vps-manager-validate` / `test-vps-manager` | YAML task inbox 驱动的 VPS 纳管与本地状态维护 |
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
- VPS Manager MVP：通过 YAML task 纳管/修改/巡检/取消纳管 VPS，强制非 22 SSH 管理端口，归档脱敏，维护本地 VPS inventory
- 失败安全：dry-run 对全栈兼容（check-mode safety）

### 不能做什么 ❌ / 半完成 ⚠
- ❌ **RHEL/Rocky/Alpine 真实部署**（`infra_baseline` 占位 fail，待 TASK-007）
- ❌ **数据库真 failover**（playbook placeholder + EDA rule disabled，待 TASK-008）
- ❌ **Prometheus 监控集成**（待 TASK-002）
- ❌ **Multi-node Semaphore HA + DB 升级 SQLite→PG**（待 TASK-003）
- ⚠ **Stag 环境真机**（结构就绪等接入）
- ⚠ **多 OS target fleet**（占位组就绪，等 4 台 VPS 上线）
- ⚠ **`molecule/hub/` scenario**（hub role 目前无独立 molecule 测试，靠 `make hub-deploy-check` 间接 dry-run）
- ⚠ **VPS Manager 实机闭环**（MVP 已有 L1 本地生命周期测试；真实远端 onboard / SSH 回滚路径仍需实机或 Molecule 场景验证）

---
*最后更新：2026-05-14 | 对应分支：`feat/eda-advanced-healing` | PR #12 → `dev`*
