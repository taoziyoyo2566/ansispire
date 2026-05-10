# Ansispire EDA 自愈系统 — Operator Guide

> 面向**第一次接触本项目**的运维人员。读完整篇按步骤做，可以从「机器一台干净的 Linux + 一个 git clone」走到「自愈链路全绿、可在生产用」。
>
> 与本目录下的 `operations.md` 区别：那一份是给已经熟悉项目的 maintainer 用的速查（命令为主、注释稀疏）；这一份解释**为什么这么做、出错怎么办**。
>
> 适用于 TASK-001（"Advanced Self-Healing Scenarios"）闭环后的 Round 4 状态。最近一次端到端验证：2026-05-10。

---

## 目录

1. [这套系统在做什么](#1-这套系统在做什么)
2. [核心概念 5 分钟速通](#2-核心概念-5-分钟速通)
3. [两条工作路径：Path A vs Path B](#3-两条工作路径path-a-vs-path-b)
4. [事件处理逻辑（自愈生命周期详解）](#4-事件处理逻辑自愈生命周期详解)
5. [Path B：本机开发 / 测试入门](#5-path-b本机开发--测试入门)
6. [Path A：把 Hub 真部署到一台机器](#6-path-a把-hub-真部署到一台机器)
7. [配置项总览（哪个文件管什么）](#7-配置项总览哪个文件管什么)
8. [常见运维任务](#8-常见运维任务)
9. [测试金字塔（4 层）](#9-测试金字塔4-层)
10. [故障排查（Troubleshooting）](#10-故障排查troubleshooting)
11. [安全 / 注意事项](#11-安全--注意事项)
12. [本轮（Round 4）架构变更速查](#12-本轮round-4架构变更速查)
13. [词汇表 / 文件索引](#13-词汇表--文件索引)

---

## 1. 这套系统在做什么

**Ansispire 是一个用 Ansible 做骨干的多机管理系统。** 它的"自愈"能力（TASK-001）解决一个具体痛点：

> 我有一组 Linux 服务器；某台机器出故障（磁盘满 / 数据库连不上 / ...）；我希望系统**自己检测 + 自己修**，不要等我半夜被叫醒。

实现方式：

```
故障发生
   ↓ （Semaphore 任务记录到 audit 日志）
events.jsonl
   ↓ （reactor.py 监听 + 匹配 rules.json 里的规则）
匹配成功
   ↓ （reactor 拿 Bearer Token 调 Semaphore HTTP API）
POST /api/project/1/tasks
   ↓ （Semaphore 启动 ansible-runner 跑修复 playbook）
playbooks/remediation/disk_cleanup.yml 执行
   ↓
任务完成 status=success
```

整个链路**无人介入**。从注入故障到修复完成，正常 < 30 秒。

---

## 2. 核心概念 5 分钟速通

| 概念 | 是什么 | 在哪 |
|---|---|---|
| **Semaphore** | 一个开源的 Ansible 控制台（有 Web UI + REST API + 任务调度） | `controller/semaphore/docker-compose.yml` 起容器 |
| **Audit Plane（审计平面）** | 三个 Python 微服务：sink 收日志、relay 拉 Semaphore 事件转发到 sink、reactor 监听 jsonl 触发 | `controller/audit/` |
| **EDA Reactor** | 监听 `events.jsonl`，按 `rules.json` 匹配，匹配上就调 Semaphore API 启动修复 | `controller/audit/reactor.py` |
| **rules.json** | 规则文件：每条规则定义"什么样的事件 → 跑哪个 Semaphore 模板" | `extensions/eda/rules.json` |
| **events.schema.json** | 事件契约（JSON Schema）；reactor 启动时打 banner 显示版本 | `extensions/eda/events.schema.json` |
| **Remediation Playbook** | 真正在被管节点上执行的修复脚本 | `playbooks/remediation/*.yml` |
| **Bootstrap** | 一个 Ansible playbook，自动建 Semaphore 项目 / 模板 / API token，纯 IaC，UI 零点击 | `controller/semaphore/bootstrap.yml` |
| **manifest.yml** | 端口 + 镜像版本 SSOT（唯一编辑入口） | `config/manifest.yml` |
| **Hub** | 安装了 Semaphore + audit + reactor 的「管理节点」 | inventory `[hub]` 组 |
| **Targets** | 被管理的 VPS（不装 hub，只装 baseline） | inventory `[targets_*]` 组 |

**关键设计原则**：
- **解耦**：control plane（Semaphore）和 data plane（被管 VPS）严格分离
- **IaC**（Infrastructure as Code）：所有 Semaphore 资源通过 bootstrap.yml 创建，不用 UI 手点
- **Bearer Token**：machine-to-machine 永不用明文密码
- **SSOT**（Single Source of Truth）：端口、版本、密钥全在指定的一个文件里

---

## 3. 两条工作路径：Path A vs Path B

项目并存**两条**工作路径。**不要混用**——它们解决不同问题。

| 维度 | **Path B（开发 / 测试）** | **Path A（真部署）** |
|---|---|---|
| 入口 | `make controller-up` 等 | `make hub-deploy HUB_NODE=...` |
| 谁运行 | 你的开发机本地 | 远程 VPS（或 control_node 本机） |
| 部署方式 | 直接 `docker compose` | Ansible role：rsync + apt + docker_compose_v2 |
| 包含 | 只起 hub + audit 的 docker 栈 | 完整：apt 装 docker、建 ansible 用户、起 hub + audit 栈、mint token |
| 何时用 | 调试 reactor 逻辑、写 rules、跑测试 | 把 hub 真装到一台 VPS（生产 / staging） |
| 是否能切换 | 否；本机就一份 | 是；HUB_NODE=local/remote/all |
| 数据持久化 | docker named volumes（`make controller-down` 留数据，`controller-reset` 清空） | docker volumes + `/var/lib/ansispire/state/` |
| 测试入口 | `make test-eda` (L1+L2+L3) / `make test-eda-e2e` (L4) | 本身就是真跑；用 `--check --diff` 干跑 |

**典型选择**：
- 写新规则 / 改 reactor 代码 / 跑回归 → **Path B**
- 准备把 hub 装到一台新的 VPS 上 → **Path A**
- 本机开发 hub，验证 OK 后再迁到远程 → **Path B 起步、Path A 收尾**

---

## 4. 事件处理逻辑（自愈生命周期详解）

完整一次自愈的 7 个阶段。每个阶段在哪个进程、读写哪个文件、出错怎么诊断——都列清楚。

### 阶段 1：故障产生
被管节点上发生异常（磁盘满、服务挂了、…）。这一步 Ansispire 不直接负责——你要自己造一条 Semaphore 任务并让它输出包含「Disk Full」字样的描述，或者用「故障注入」直接写一行 jsonl。

### 阶段 2：审计写盘
- **进程**: `audit-sink`（容器 `ansispire-audit-sink` 或 `*-e2e`）
- **触发方式**:
  - 路径 a：`audit-relay` 容器轮询 Semaphore `/api/events`，拿到事件后 POST 给 sink
  - 路径 b：手动 `curl -X POST http://127.0.0.1:3310/event ...` 注入测试事件
- **输出**: `/var/log/semaphore/events.jsonl`（容器内卷 `audit-data`）
- **每行格式**: 见 `extensions/eda/events.schema.json`，关键是 `payload.event.{description, object_type, status, ...}`

### 阶段 3：reactor 匹配
- **进程**: `audit-reactor`（容器 `ansispire-audit-reactor`）
- **行为**: tail `events.jsonl`；每收到新行解析 JSON，对所有 `rules.json` 里 `enabled: true` 的规则尝试匹配
- **匹配语义**: 规则 `condition` 字段每个 key 必须满足；后缀 `_contains` = 子串匹配；其他 = 精确等值
- **冷却**: 每条规则按 `name` 维护时间戳；冷却期内（默认 600 秒）相同规则不再触发
- **匹配成功 log**:
  ```
  [reactor] MATCH FOUND: Remediation: Disk Full
  ```

### 阶段 4：动态解析 template_id
- **行为**: reactor 拿到匹配规则的 `actions[*].template_name`（字符串 name），通过 Semaphore `/api/project/<id>/templates` 查询拿到 numeric `template_id`
- **缓存**: 同一 reactor 进程内不重复查询同一对名称（in-memory cache）
- **若解析失败 log**:
  ```
  [reactor] remediation failed: could not resolve template <name> in project <id>
  ```
  通常意味着 bootstrap.yml 没注册这个名字（rules.json ↔ bootstrap.yml 漂移）。`make test-eda-contract`（L2）就是来挡这种漂移的。

### 阶段 5：调用 Semaphore API
- **行为**: `POST {SEMAPHORE_URL}/api/project/<id>/tasks`，header `Authorization: Bearer <SEMAPHORE_API_TOKEN>`
- **token 来源**: env 变量 `SEMAPHORE_API_TOKEN`，从 `.secrets` 文件加载（Path B 用 `controller/semaphore/.secrets`，Path A 用部署目标主机上的 `/var/lib/ansispire/state/.eda_token`）
- **成功 log**:
  ```
  [reactor] remediation triggered: template=<id> (Auto Remediation: Disk Cleanup), status=201
  ```
  注意 `<id>` 由 Semaphore 在 bootstrap 时随机分配，不要写死成"应该是 1"。

### 阶段 6：ansible-runner 执行
- **进程**: Semaphore 容器内部 fork 一个 ansible-runner 子进程
- **行为**: 加载 `playbooks/remediation/disk_cleanup.yml`（或对应规则的 playbook），按 inventory 跑
- **可在 Web UI 实时看输出**：http://`{HUB_HOST}`:3300/project/1/tasks

### 阶段 7：状态收尾
- **行为**: ansible-runner 退出码写回 Semaphore 任务记录；Semaphore Web UI 显示 status=success / error
- **下次审计**: 该 task 的状态变化又会被 audit-relay 抓回 jsonl（自我观察）；可以再写规则识别"修复任务自己失败了"做二次反应（不在本轮范围）

---

## 5. Path B：本机开发 / 测试入门

最快上手路径。一次成功后，你机器上就有完整自愈链路。

### 5.1 前置依赖
- Linux（项目当前在 Ubuntu 24.04 + Debian 12 验证过）
- Docker engine 25+ 和 docker compose v2
- Python 3.10+
- 8 GB+ RAM 富余

### 5.2 一次性 setup
```bash
git clone <repo-url> ansispire
cd ansispire

# 创建虚拟环境 + 装 Ansible + collections
make setup

# 复制环境模板
cp controller/semaphore/.env.example controller/semaphore/.env

# 编辑：把 SEMAPHORE_ADMIN_PASSWORD 改成你自己的强密码
vim controller/semaphore/.env
```

`.env` 里 **不要** 自己写 `SEMAPHORE_PORT=` 或 `SEMAPHORE_IMAGE_TAG=` 这类——它们由 `make manifest-sync` 自动渲染管理块管理。

### 5.3 起 Semaphore + 拨备 + 起 audit
```bash
# 1. 起 Semaphore 容器（自动渲染 manifest 到 .env，自动拉镜像）
make controller-up

# 2. 自动建项目 / 模板 / mint API token（写到 .secrets）
make controller-bootstrap

# 3. 起 audit 三件套（sink + relay + reactor），自动加载 .secrets
make controller-audit-up
```

每一步都应该看到大量绿色 `ok` / `changed`。任意一步失败请先看[故障排查](#10-故障排查troubleshooting)。

### 5.4 验证浏览器能开
浏览器打开 http://localhost:3300，用 `.env` 里的 admin 账号密码登录，应该能看到一个名为 `ansispire` 的项目。

### 5.5 跑测试金字塔
```bash
# L1+L2+L3 — 28 cases，纯 Python，不到 1 秒
make test-eda

# L4 — 真容器栈端到端，约 60 秒
make test-eda-e2e
```

L4 全程在隔离的 `ansispire-e2e` compose 项目里跑，**不影响**你 5.3 起的 dev 栈（端口 3320/3330 vs dev 3300/3310）。

### 5.6 手动注入故障 + 观察
```bash
# 注入一行 Disk Full 事件
docker exec ansispire-audit-sink sh -c 'printf "%s\n" \
  "{\"payload\":{\"event\":{\"object_type\":\"task\",\"description\":\"Disk Full on demo-host\"}}}" \
  >> /var/log/semaphore/events.jsonl'

# 实时看 reactor 反应
docker logs -f ansispire-audit-reactor
```

正常应该看到：
```
[reactor] received event: ...
[reactor] MATCH FOUND: Remediation: Disk Full
[reactor] remediation triggered: template=<N> (Auto Remediation: Disk Cleanup), status=201
```

然后到 http://localhost:3300 看 Tasks 页面，会出现一个新跑的 `Auto Remediation: Disk Cleanup` 任务。

### 5.7 收摊
```bash
# 停容器、保留数据
make controller-audit-down
make controller-down

# 完全清空（!!! 删数据库 !!!）
make controller-reset
```

---

## 6. Path A：把 Hub 真部署到一台机器

把 Path B 验证过的 hub 装到一台真 VPS 或者本地永久跑。

### 6.1 前置依赖（管理控制端，即跑 ansible-playbook 的机器）
- Path B §5.1 全套
- 一个 vault 密码文件（用来解密 `inventory/local/vault.yml`）
- 目标机器的 SSH 配置（`~/.ssh/config` 中有别名）

### 6.2 准备 vault 密码
```bash
echo "your-vault-password" > .vault_pass
chmod 600 .vault_pass

# 编辑 vault.yml（设置 vault_semaphore_admin_password）
.venv/bin/ansible-vault edit inventory/local/vault.yml
```

如果 `inventory/local/vault.yml` 不存在，从 example 复制再加密：
```bash
cp inventory/local/vault.yml.example inventory/local/vault.yml
vim inventory/local/vault.yml         # 设置 vault_semaphore_admin_password
.venv/bin/ansible-vault encrypt inventory/local/vault.yml
```

### 6.3 inventory 加目标主机

打开 `inventory/hosts.ini`：

```ini
[hub_local]
control_node ansible_connection=local ansible_python_interpreter=/usr/bin/python3

[hub_remote]
ans-hk01 ansible_python_interpreter=/usr/bin/python3.13
# 加新远程主机：填别名（要先在 ~/.ssh/config 里配好）
# my-new-vps ansible_python_interpreter=/usr/bin/python3

[hub:children]
hub_local
hub_remote
```

`ansible_python_interpreter=` **务必填**（避免 Ansible 自动发现警告 + 未来升级 Python 后解释器漂移）。

测试连通性：
```bash
.venv/bin/ansible -i inventory/hosts.ini hub -m ping
```

### 6.4 干跑（强烈推荐先做这一步）
```bash
# 只对远程节点干跑
make hub-deploy-check HUB_NODE=remote

# 只对本机干跑
make hub-deploy-check HUB_NODE=local

# 全部
make hub-deploy-check HUB_NODE=all
```

期望 `failed=0`，diff 中 **不应** 出现：
- `.claude/` / `.ansible/` / `__pycache__` （都被 rsync excludes 拦了）
- `controller/rbac/.demo_*.pw` / `controller/rbac/users.yml` （凭据；被拦）
- `controller/semaphore/.env` / `.secrets` （秘密；被拦）
- `*deleting .eda_token` （状态文件，已迁出代码目录、不再被 rsync 擦）

如果上述任何一项出现了，**停止部署**，回看[安全 / 注意事项](#11-安全--注意事项)。

### 6.5 真部署
```bash
make hub-deploy HUB_NODE=remote        # 部署到 ans-hk01 等
# 或
make hub-deploy HUB_NODE=local         # 部署到 control_node（本机）
# 或
make hub-deploy HUB_NODE=all
```

首次部署执行：
1. apt 安装 docker engine + 各种基础包
2. 创建 `ansible` 用户 + 配 NOPASSWD sudo + 拷贝 root 的 authorized_keys
3. rsync 仓库到 `/opt/ansispire/`
4. 渲染 `controller/semaphore/.env`
5. `docker compose up -d` 起 Semaphore
6. `semaphore user add` 建 admin
7. 调 API mint token → 写 `/var/lib/ansispire/state/.eda_token`
8. `docker compose up -d` 起 audit 三件套（透传 token 给 reactor 容器）

正常 ~3-5 分钟出结果，最末一行 Summary 显示 hub URL。

### 6.6 部署后验证（在远程主机上跑）
```bash
# SSH 到远程
ssh ans-hk01

# 看容器状态
docker ps | grep ansispire-

# 看 reactor 是否拿到 token + 加载了规则
docker logs ansispire-audit-reactor 2>&1 | head -20

# 注入 Disk Full 事件
docker exec ansispire-audit-sink sh -c 'printf "%s\n" \
  "{\"payload\":{\"event\":{\"object_type\":\"task\",\"description\":\"Disk Full on remote\"}}}" \
  >> /var/log/semaphore/events.jsonl'

# 5 秒内 reactor 应该 MATCH，10–20 秒内 Semaphore 任务跑完
docker logs --tail 50 ansispire-audit-reactor
```

### 6.7 复部署 / 升级
直接重跑 `make hub-deploy HUB_NODE=...`。`ansispire_hub` role 是幂等的：
- 已装的 apt 包 skip
- 已建的 user / group skip
- rsync 只传变化的文件
- 已有 `.eda_token` 时跳过 mint（保留旧 token）

---

## 7. 配置项总览（哪个文件管什么）

```
config/manifest.yml                 ← 编辑这里：端口 + 镜像版本
   │
   ├─→ make manifest-sync           ← 渲染到 .env 的 # BEGIN/END manifest 块
   │     │
   │     ├─→ controller/semaphore/.env   ← 用户编辑：admin/timezone（manifest 块由脚本管）
   │     │
   │     └─→ controller/semaphore/.secrets ← bootstrap 自动写：SEMAPHORE_API_TOKEN
   │
   ├─→ controller/semaphore/bootstrap.yml  ← vars_files 派生 semaphore_url
   │
   └─→ playbooks/deploy_hub.yml            ← vars_files 让 role defaults 读到 ports/versions
         │
         └─→ roles/ansispire_hub/templates/semaphore_env.j2
               ← 模板写到 /opt/ansispire/controller/semaphore/.env

extensions/eda/rules.json           ← 编辑这里：定义"什么事件 → 跑什么模板"
   │
   ├─→ make test-eda-contract       ← L2 测试：rule 引用的 template_name 必须在 bootstrap 注册
   │
   └─→ controller/audit/reactor.py  ← 启动时读 + 在 events.jsonl 上匹配

extensions/eda/events.schema.json   ← 编辑这里：声明 reactor 认识哪些事件字段
   │
   └─→ make test-eda-contract C9    ← rules condition 字段必须在 schema 里声明

inventory/hosts.ini                 ← 编辑这里：物理机器、谁是 hub、谁是 target
   │
   ├─→ [hub_local]    本机管理节点
   ├─→ [hub_remote]   远程 VPS 管理节点
   └─→ [targets_*]    被管 VPS（按 OS 家族分组；下一阶段用）

inventory/local/vault.yml           ← 编辑这里（加密）：Semaphore admin 密码
   │
   └─→ playbooks/deploy_hub.yml vars_files 加载（需要 .vault_pass）

playbooks/remediation/*.yml         ← 编辑这里：真正在 target 上执行的修复脚本
```

**修改流程举例**：
- 想换 Semaphore 端口为 3400：编辑 `config/manifest.yml` 的 `semaphore_host: 3400` → `make controller-down && make controller-up`（自动重 sync）。
- 想升级 Semaphore 镜像到 `v2.19.0`：编辑 `config/manifest.yml` 的 `semaphore_pinned: v2.19.0` → `make controller-down && make controller-up`。
- 想加一条新的 Disk Cleanup-类规则：编辑 `extensions/eda/rules.json` → 编辑 `controller/semaphore/bootstrap.yml` 的 remediation templates loop（加注册项）→ `make test-eda-contract`（必须过）→ Path B 的话 `make controller-audit-down && make controller-audit-up`，Path A 的话重跑 `make hub-deploy`。

---

## 8. 常见运维任务

### 8.1 加一台新远程 VPS 进 hub
```bash
# 1. 在 ~/.ssh/config 配好别名（HostName / Port / User / IdentityFile）

# 2. 在 inventory/hosts.ini 的 [hub_remote] 加一行
echo "vps-tokyo01 ansible_python_interpreter=/usr/bin/python3" >> inventory/hosts.ini

# 3. 测连通
.venv/bin/ansible -i inventory/hosts.ini vps-tokyo01 -m ping

# 4. 部署
make hub-deploy HUB_NODE=remote --limit vps-tokyo01     # 注：Makefile 不直接传 --limit；
# 实际写法：
.venv/bin/ansible-playbook playbooks/deploy_hub.yml \
  -i inventory/hosts.ini --limit vps-tokyo01 \
  --vault-password-file .vault_pass --diff
```

### 8.2 把管理节点从远程切到本机
```bash
# 准备 control_node（本机）vault 等都已就位
make hub-deploy HUB_NODE=local

# 验证
docker ps | grep ansispire-
curl http://localhost:3300/api/ping     # 应返回 "pong" 或 200
```

如果之前 hub 在远程跑，迁移期间两边都跑没问题（端口在不同主机互不干扰）。

### 8.3 加一条新的修复规则
```bash
# 1. 写真实的修复 playbook
vim playbooks/remediation/restart_nginx.yml

# 2. 在 bootstrap.yml 的 'Register remediation templates' loop 加一项
vim controller/semaphore/bootstrap.yml
#   - name: Auto Remediation: Restart Nginx
#     playbook: playbooks/remediation/restart_nginx.yml
#     ...

# 3. 在 rules.json 加一条规则
vim extensions/eda/rules.json
#   {
#     "name": "Remediation: Nginx Down",
#     "condition": { "description_contains": "nginx connection refused" },
#     "actions": [{ "type": "semaphore_api",
#                   "project_name": "ansispire",
#                   "template_name": "Auto Remediation: Restart Nginx",
#                   "name": "Restart Nginx" }]
#   }

# 4. 跑契约测试
make test-eda-contract             # C7 必须过：rules.json 引用的 template_name 在 bootstrap 注册了

# 5. Path B：刷新栈
make controller-bootstrap          # 注册新 template
make controller-audit-down && make controller-audit-up   # reactor 重读 rules.json

# 5'. Path A：重跑部署
make hub-deploy HUB_NODE=...
```

### 8.4 升级 Semaphore 版本
```bash
# 1. 改 manifest.yml
sed -i 's/semaphore_pinned: v2.18.2/semaphore_pinned: v2.19.0/' config/manifest.yml

# 2. Path B：重启
make controller-down && make controller-up

# 2'. Path A：重跑
make hub-deploy HUB_NODE=remote
```

升级失败回滚：把 `semaphore_pinned` 改回旧版本，再跑同样命令。

### 8.5 临时停掉一条规则不删
```json
// extensions/eda/rules.json
{
  "name": "Remediation: DB Connection Failure",
  "enabled": false,
  "_disabled_reason": "playbook 还没真做完，先不要触发",
  ...
}
```

`enabled: false` 会让 reactor 在 match_rule 早返回；本身保留在文件里方便随时打开。

### 8.6 看实时日志
```bash
# Semaphore web 后端
make controller-logs            # = docker compose logs -f semaphore

# Audit JSONL 实时
make controller-audit-tail

# Reactor
docker logs -f ansispire-audit-reactor

# Audit 事件 path 计数
make controller-audit-stats
```

### 8.7 完全推倒重来（生产环境慎用）
```bash
# Path B
make controller-audit-down
make controller-reset           # 会问 y/N；y 后删除所有 docker volume

# Path A
ssh <hub-host>
docker compose -f /opt/ansispire/controller/audit/docker-compose.yml down -v
docker compose -f /opt/ansispire/controller/semaphore/docker-compose.yml down -v
sudo rm -rf /var/lib/ansispire/state/
# 然后从控制端重跑 make hub-deploy HUB_NODE=...
```

---

## 9. 测试金字塔（4 层）

每层用一句话回答两个问题：能挡什么 bug、什么时候跑。

| 层 | 名称 | 用例数 | 时间 | 何时跑 | 挡什么 |
|---|---|---|---|---|---|
| L1 | reactor 单元（`test_reactor.py`） | 14 | < 0.01 s | 每改 reactor.py 都跑 | match_rule 逻辑、cooldown、process_event 错误处理 |
| L2 | rules-bootstrap 契约（`test_rules_contract.py`） | 9 | < 0.1 s | 每改 rules.json / bootstrap.yml / events.schema.json 都跑 | template_name 漂移、schema vs rules 字段对齐、rule name 唯一性 |
| L3 | reactor-Semaphore 协议（`test_reactor_component.py`） | 5 | < 1 s | 每改 reactor 的 HTTP 调用 都跑 | Bearer header 形态、模板缓存、错误响应处理 |
| L4 | 端到端 disposable 栈（`controller/audit/e2e/run.sh`） | 1 | ~60 s | 升级 Semaphore / 改 docker compose / 想做 release smoke | 真容器、真 ansible-runner、整链路 |

入口：
```bash
make test-eda             # L1+L2+L3 一起；< 1 秒；CI 友好
make test-eda-e2e         # L4；要 docker engine；不要进 CI
make verify               # lint + syntax + L1+L2+L3 + dry-run
```

L4 用独立 compose project (`ansispire-e2e`)、独立 network (`controller-net-e2e`)、独立端口 (3320/3330)，**不影响**正在跑的 dev 栈。

每层都有 TSVS 规格说明书：`docs/test-specs/eda-reactor-{unit,component,e2e}.md` + `eda-rules-contract.md`。

---

## 10. 故障排查（Troubleshooting）

按"现象 → 根因 → 修法"组织。先在 `docker logs` / make 输出里 grep 关键字，再来这里找。

| 现象 | 根因 | 修法 |
|---|---|---|
| `Password must be provided via -e semaphore_password=` | 用了 `sem_pass=` 这种旧版（Gemini 158-line 重写）变量名 | 改用 `make controller-bootstrap`，或显式 `-e semaphore_password=...` |
| reactor 启动后日志只有 `SEMAPHORE_API_TOKEN not set` | bootstrap 没跑过 / audit 栈还没拿到新 token | `make controller-bootstrap && make controller-audit-down && make controller-audit-up` |
| reactor 收事件但无 MATCH | rules.json 里 condition 字段拼错 / `_contains` 子串匹配不到 | 比对事件原文与 rules.json，先用 `make test-eda-contract` 跑 |
| reactor MATCH 后报 `could not resolve template <name>` | rules.json 引用了 bootstrap 没注册的 template_name | `make test-eda-contract` 会挡这条；如果直接生产里出，去 `controller/semaphore/bootstrap.yml` Register loop 补 |
| `[reactor] JSON parse error` | 注入命令含物理换行 / 单引号嵌套错 | 用 §5.6 那种一行 printf 写法 |
| Web UI 端口连不上（manifest 改了但容器没重启） | compose 不会因 .env 变就重启容器 | `make controller-down && make controller-up` |
| `make controller-bootstrap` 报权限错 / `.secrets` owner=root | `ansible.cfg` 全局 `become=True` 影响 | 已修：bootstrap.yml + manifest_sync.yml 头部都显式 `become: false`；如再出，检查这两个文件 |
| Token 末尾被截 / 401 Unauthorized | `cut -d= -f2` 截断了 base64 padding | 用 `cut -d= -f2-`（带 `-` 取所有剩余字段） |
| Path A `--check --diff` 报 `cookies_string` 不存在 | `--check` 模式 Login 任务 noop，cookies 自然没有；token 块未跳过 | 已修：role 加 `when: not ansible_check_mode` gate |
| Path A rsync 把 `.claude/` / `.env` 等飞到远程 | 旧版 rsync_opts 只 exclude `.git` `.venv` | 已修：exclude 列表扩到 21 项；如再出，先看 §11 |
| Path A 部署后 `.eda_token` 每次被 rsync delete | 旧版 token 在 `/opt/ansispire/.eda_token` 被 `delete: true` 擦 | 已修：迁到 `/var/lib/ansispire/state/.eda_token`，rsync 看不见 |
| ans-hk01 报 `Host is using the discovered Python interpreter at /usr/bin/python3.13` 警告 | 没钉 ansible_python_interpreter | 已修：`inventory/hosts.ini` 中显式钉死 |
| `ansible.posix.synchronize` 抛 `to_text` deprecation | collection 内部 import 路径滞后；无新版可升 | 静默忽略；ansible-core 2.24 之前不会真破。upstream issue 待跟进。|
| `infra_baseline` 在 Alpine / Rocky 上立即 fail with NOT IMPLEMENTED | 这是 Round 4 的故意守门 | 等 TASK-007 实现 RHEL/Alpine 分支；目前不要把那两类 OS 加入 hub 部署 |

更多硬故障（控制不住的）：去 [`docs/investigations/INDEX.md`](../../investigations/INDEX.md) 检索关键字。

---

## 11. 安全 / 注意事项

**这一节比"故障排查"更重要。读两遍。**

### 11.1 凭据 / 密钥 / 状态文件清单
绝对**不要** commit 进 git，绝对**不要**通过 rsync 上远程：

| 文件 | 类型 | 怎么保护 |
|---|---|---|
| `.vault_pass` | vault 密码 | `.gitignore` 第 2 行；rsync exclude `--exclude=*.vault_pass` |
| `inventory/local/vault.yml`（解密后） | admin 密码 | 加密后才能存盘；`ansible-vault edit` 使用 |
| `controller/semaphore/.env` | admin 密码明文 | `.gitignore` + rsync exclude |
| `controller/semaphore/.secrets` | API token | `.gitignore` + rsync exclude |
| `controller/audit/e2e/.env` / `.secrets` | e2e 密码 + token | `.gitignore` + rsync exclude |
| `controller/rbac/.demo_*.pw` | 演示用户密码 | `.gitignore` + rsync exclude |
| `controller/rbac/users.yml` | 用户凭据集合 | `.gitignore` + rsync exclude |
| `<hub>:/var/lib/ansispire/state/.eda_token` | hub 上的 EDA token | rsync 永远不动这里（迁出代码目录） |

跑过 Path A 后可以 grep 验证：

```bash
make hub-deploy-check HUB_NODE=remote 2>&1 | grep -E "\.env|\.secrets|\.demo_|users\.yml|\.eda_token"
```

应该**只**有 `.env.example` / `controller/semaphore/.env.example` 等模板文件。任何真凭据出现都是 bug。

### 11.2 Path A 的 `--delete` 行为
`Hub | Sync Code` 任务用 `rsync --delete`。这意味着：
- 远程 `/opt/ansispire/` 多出来的文件会被**删除**
- 这是 by design——保证远程是仓库的精确镜像
- **后果**：不要在 `/opt/ansispire/` 里手编文件，会被下次部署擦掉
- **唯一例外**：`.eda_token`（在 `/var/lib/ansispire/state/`，被 rsync 排除）

### 11.3 Vault 密码丢了怎么办
没办法。Ansible vault 是 AES256，没后门。
- 如果 `.vault_pass` 还在但忘了内容：`cat .vault_pass`
- 如果 `inventory/local/vault.yml` 还能解：`ansible-vault rekey` 改密码
- 都丢了：删 `inventory/local/vault.yml`，从 `vault.yml.example` 重建，重新加密；旧 hub 的 admin 密码也得手动重置（`docker exec ansispire-semaphore semaphore user change-by-login --login admin`）

### 11.4 不要在生产 hub 的 Web UI 上手动建项目 / 模板
所有 Semaphore 资源（project、inventory、template、user）必须通过 `controller/semaphore/bootstrap.yml` 创建。
- **理由**：bootstrap 是 IaC，下次重建/迁移能一键还原；UI 手建的资源在重建时丢失
- **唯一例外**：vault key（SSH 密钥、登录密码）等真实凭据，bootstrap 只创建占位符；真凭据导入要在 UI 上做

### 11.5 端口 +300 约定
Ansispire-owned host 端口 = container 端口 + 300（避开 3306/5432/6379/3000 等通用端口）：
- Semaphore: container 3000 → host 3300
- Audit sink: container 3010 → host 3310
- 未来 Prometheus: container 9090 → host 9390
- e2e 隔离栈：再 +20（host 3320/3330）

IANA 标准协议端口（MySQL 3306、PostgreSQL 5432）**不归** Ansispire 管，不走 +300。

### 11.6 状态目录权限
`/var/lib/ansispire/state/` 默认 mode `0700`，只有 root 能进。**不要** chmod 改它，token 暴露给非特权用户会被任何能 cat 文件的人拿去打 Semaphore API。

### 11.7 镜像 `:latest` 的陷阱
docker compose **不会** 自动 `pull`。如果你在 manifest.yml 的 `semaphore_pinned` 写 `latest`，第一次 pull 之后版本就**冻结**——下次重启还是同一个旧 image。生产**永远** pin 具体版本号。

### 11.8 ansible.cfg 全局 become=True 的影响
项目 `ansible.cfg` 设置了 `become = True`（方便绝大多数 task）。但这会让任何"在控制端写本地文件"的 task 默认走 sudo，把文件 own 成 root。受影响的两个 playbook 已显式 `become: false`：
- `controller/semaphore/bootstrap.yml`
- `playbooks/manifest_sync.yml`

**如果你写新的本地播本，记得加 `become: false`**——否则会出现"我跑完后这个文件 owner 是 root，再跑就读不了"的问题。

### 11.9 EDA token 轮换
当前没有自动轮换机制。token 一旦 mint 就长期有效。建议每季度 / 每次重大安全事件后手动轮换：
```bash
ssh <hub>
sudo rm /var/lib/ansispire/state/.eda_token
exit
make hub-deploy HUB_NODE=remote                # 重跑会重新 mint
```

---

## 12. 本轮（Round 4）架构变更速查

如果你之前看过更早版本的文档，注意以下变更：

| 改动 | 之前 | 现在 |
|---|---|---|
| 端口 / 版本管理 | `config/ports.yml`（只管端口） | `config/manifest.yml`（端口 + 镜像版本，含 `default_tag: latest` + `*_pinned` 段） |
| 同步命令 | `make ports-sync` | `make manifest-sync`（`ports-sync` 仍可用一轮，下轮删） |
| Hub inventory | `[hub]` 单组写死远程 | `[hub_local]` + `[hub_remote]` + `[hub:children]`，加 `[targets_*]` 占位组 |
| Path A 部署入口 | 直接 `ansible-playbook deploy_hub.yml ...` | `make hub-deploy HUB_NODE=local|remote|all`（封装 `--limit`） |
| Hub role 模板 | `semaphore_docker_compose.yml.j2`（与 Path B compose 平行存在但漂移） | **已删除**；rsync 直接落 Path B 的 SSOT compose；只剩 `semaphore_env.j2` |
| EDA token 位置 | `/opt/ansispire/.eda_token`（被 rsync `--delete` 擦） | `/var/lib/ansispire/state/.eda_token`（rsync 看不见，永久保留） |
| Rsync excludes | 2 项（`.git` / `.venv`） | 21 项（4 组：local-artefacts / secrets / stateful / docs） |
| `--check` 模式 token 块 | 报 `cookies_string` 错 | 加 `when: not ansible_check_mode` 守护 |
| `infra_baseline` OS 兼容性 | apt-only，Alpine/Rocky 直接报错 | apt 块用 `os_family == "Debian"` 守门；RHEL/Alpine 显式 fail 占位 |
| ans-hk01 Python 解释器 | 自动发现（warn） | inventory 钉死 `/usr/bin/python3.13` |

变更原因详见 [`docs/reviews/feat-eda-advanced-healing/round4-2026-05-10.changelog.md`](../../reviews/feat-eda-advanced-healing/round4-2026-05-10.changelog.md)。

---

## 13. 词汇表 / 文件索引

### 13.1 关键文件
| 路径 | 作用 |
|---|---|
| `config/manifest.yml` | 端口 + 镜像版本 SSOT |
| `inventory/hosts.ini` | 物理拓扑 SSOT |
| `inventory/local/vault.yml` | admin 密码（加密） |
| `extensions/eda/rules.json` | 规则定义 |
| `extensions/eda/events.schema.json` | 事件契约 |
| `controller/semaphore/bootstrap.yml` | IaC 拨备 |
| `controller/audit/reactor.py` | 反应引擎 |
| `controller/audit/sink.py` | 审计日志接收 |
| `controller/audit/relay.py` | Semaphore → sink 转发 |
| `playbooks/deploy_hub.yml` | Path A 入口 |
| `playbooks/manifest_sync.yml` | manifest → .env 渲染器 |
| `playbooks/remediation/*.yml` | 修复脚本（实际执行的 ansible playbook） |
| `roles/infra_baseline/` | OS 基线（apt + docker + ansible 用户） |
| `roles/ansispire_hub/` | Semaphore 容器 + token mint |
| `roles/ansispire_audit/` | audit 三件套容器 |
| `controller/audit/e2e/` | L4 测试隔离栈 |
| `Makefile` | 所有 make 入口 |

### 13.2 测试规格
| 文件 | 层 |
|---|---|
| `docs/test-specs/eda-reactor-unit.md` | L1 |
| `docs/test-specs/eda-rules-contract.md` | L2 |
| `docs/test-specs/eda-reactor-component.md` | L3 |
| `docs/test-specs/eda-reactor-e2e.md` | L4 |

### 13.3 设计文档（演进史）
| 文件 | 内容 |
|---|---|
| `docs/reviews/feat-eda-advanced-healing/plan-2026-05-09.md` | 总体规划 |
| `docs/reviews/feat-eda-advanced-healing/round1-2026-05-09.changelog.md` | Path B 底盘修复 |
| `docs/reviews/feat-eda-advanced-healing/round2-2026-05-09.changelog.md` | L1+L2+L3 测试金字塔 |
| `docs/reviews/feat-eda-advanced-healing/round3-2026-05-09.changelog.md` | L4 e2e + schema + rule.enabled |
| `docs/reviews/feat-eda-advanced-healing/round4-2026-05-10.changelog.md` | Path A 全面硬化 + manifest SSOT |
| `docs/features/eda-core/operations.md` | maintainer 速查（短） |
| `docs/features/eda-core/summary.md` | feature map |
| **本文件** | 用户向 operator guide（长） |

---

*Last updated: 2026-05-10. Aligned with Round 4 (TASK-001 closure). Maintainer：每轮架构改动需同步本文件 §10–§13。*
