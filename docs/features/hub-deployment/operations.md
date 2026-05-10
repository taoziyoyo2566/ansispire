# Ansispire Hub 运维指南 (Operational Reference)

> **本文档定位**：Hub 部署 / 运维的速查参考。命令为主、注释稀疏。
>
> **第一次接触？** 先看 [`docs/features/eda-core/operator-guide.md`](../eda-core/operator-guide.md) — 用户向长文，含原理 + 故障路径。

---

## 1. 核心架构

Ansispire Hub 采用 **All-in-One** 架构：管理平面 + 审计平面 + 执行平面共存于一台主机。

- **控制中心 (Semaphore)**：Web UI + REST API 调度
- **审计平面 (Audit Plane)**：sink + relay + reactor 三件套
- **反应引擎 (EDA Reactor)**：监听 `events.jsonl`，匹配规则后调 Semaphore API

详细组件说明：`docs/features/eda-core/operator-guide.md` §2 + §4。

---

## 2. 端口与镜像

由 `config/manifest.yml` 单一管理（SSOT）：

```yaml
ansispire_ports:
  semaphore_host: 3300       # → host port = container port + 300
  audit_sink_host: 3310
ansispire_versions:
  semaphore_pinned: v2.18.2
  audit_python_pinned: 3.12-alpine
```

修改：编辑 `manifest.yml` → `make manifest-sync`（Path B 自动；Path A 由 `deploy_hub.yml` 派生）→ 重启容器栈。

约定：**Ansispire-owned host 端口 = container 端口 + 300**（避开 3306 / 5432 / 6379 / 3000）。IANA 标准协议端口（如 MySQL 3306）不归项目管，不走 +300。

---

## 3. 用户与权限

- **`ansible` 用户**：`infra_baseline` role 自动建，NOPASSWD sudo，从 `/root/.ssh/authorized_keys` 拷 SSH key
- **SSH**：后续维护建议用 `ansible@<host>` 替代 `root`
- **基础设施维护禁忌**：禁止通过 Hub 自身的 Semaphore 调度任务来维护 Hub 基础设施（自我观察 / 升级 docker / 改 compose）。Hub 升级必须从外部（开发机）通过 `playbooks/deploy_hub.yml` 触发。

---

## 4. 部署生命周期 (Lifecycle)

项目采用 **Config-as-Code (IaC)** 模式。**严禁** 在 Web UI 手动配置生产级资源（项目 / 模板 / inventory）；这些必须通过 `controller/semaphore/bootstrap.yml` 创建。

### 4.1 inventory 拓扑（Round 4 引入）

```ini
# inventory/hosts.ini
[hub_local]
control_node ansible_connection=local

[hub_remote]
ans-hk01 ansible_python_interpreter=/usr/bin/python3.13

[hub:children]
hub_local
hub_remote

[targets_debian]
[targets_rhel]
[targets_alpine]
[targets:children]
targets_debian
targets_rhel
targets_alpine
```

`[targets_*]` 占位组为下一阶段 4 台多 OS VPS 准备。

### 4.2 部署到远程 hub（Path A）

```bash
# 干跑（强烈推荐先做）
make hub-deploy-check NODE=remote

# 真部署
make hub-deploy NODE=remote
```

`NODE=local|remote|all` 三选一控制 `--limit` 范围；vault 密码默认从 `.vault_pass` 读，可用 `VAULT_PASSWORD_FILE=...` 覆盖。

### 4.3 部署到本机（Path A scenario 2）

```bash
make hub-deploy NODE=local
```

需要先把 `control_node` 的依赖（docker、python venv）准备好，且 SUDO 不需要密码。本机部署用于"先本地起，后迁远程"的过渡场景。

### 4.4 IaC 业务资源拨备

```bash
# Path B（在开发机本地 Semaphore 上）
make controller-bootstrap

# Path A（部署后自动跑；如需手动重跑，到 hub 上）
ssh <hub-host>
cd /opt/ansispire
PASS=$(grep '^SEMAPHORE_ADMIN_PASSWORD=' controller/semaphore/.env | cut -d= -f2-)
.venv/bin/ansible-playbook controller/semaphore/bootstrap.yml \
  -e semaphore_password="$PASS"
```

**变量名是 `semaphore_password`**，不是 `sem_pass`。后者是已经废弃的 Gemini 158-line 重构遗留，不再支持。

### 4.5 彻底重置（核能选项）

⚠ 删数据库 / 删容器卷。生产慎用。

```bash
# Path B
make controller-audit-down
make controller-reset

# Path A
ssh <hub-host>
docker compose -f /opt/ansispire/controller/audit/docker-compose.yml down -v
docker compose -f /opt/ansispire/controller/semaphore/docker-compose.yml down -v
sudo rm -rf /var/lib/ansispire/state/
exit
make hub-deploy NODE=remote   # 重跑等于全新装
```

### 4.6 闭环验证 (Verification Loop)

每次部署后跑一遍故障注入：

```bash
# 在 Hub 宿主机上
docker exec ansispire-audit-sink sh -c 'printf "%s\n" \
  "{\"payload\":{\"event\":{\"object_type\":\"task\",\"description\":\"Disk Full on demo\"}}}" \
  >> /var/log/semaphore/events.jsonl'

# 看 reactor
docker logs --tail 20 ansispire-audit-reactor
# 期望：MATCH FOUND → remediation triggered status=201

# 看 Semaphore
TOKEN=$(sudo cat /var/lib/ansispire/state/.eda_token)
curl -sS -H "Authorization: Bearer $TOKEN" \
  http://localhost:3300/api/project/1/tasks?limit=1 | python3 -m json.tool
# 期望：最近一条 status=success
```

### 4.7 库存完整性 (Inventory Integrity)

Ansible 2.20+ inventory 解析严格：引用了未定义的子组 → **整个配置被忽略**。即使是空组也必须显式声明。已在 `inventory/hosts.ini` 落实（`[targets_*]` 即使无主机也有空组占位）。

---

## 5. 故障排查

| 现象 | 修法 |
|---|---|
| `Password must be provided via -e semaphore_password=` | 用 `make controller-bootstrap` 或显式 `-e semaphore_password=...`；不要用 `sem_pass=` |
| `Status code 201/200 mismatch` | API 创建资源时返回 201 是预期；bootstrap.yml 已兼容（`status_code: [200, 201]`） |
| `YAML parsing failed` | 检查 task 剧本未转义的冒号或非法 YAML 语法 |
| `Inventory parsing warning: undefined group X` | 检查 `[group:children]` 下的子组都已显式定义 |
| Path A `--check` 失败 `cookies_string` | 已修：role 加 `when: not ansible_check_mode`；如重现，检查 `roles/ansispire_hub/tasks/main.yml` |
| Path A rsync 把 `.env` / `.secrets` / `.demo_*.pw` 上传 | 已修：21 项 rsync excludes；如重现，检查 `roles/ansispire_hub/tasks/main.yml` rsync_opts |
| 远程 `.eda_token` 每次部署被擦 | 已修：状态文件迁 `/var/lib/ansispire/state/.eda_token`；rsync 看不见 |
| `infra_baseline` 在 Alpine/Rocky 上立即 fail | 故意：Round 4 守门，等 TASK-007 实现 RHEL/Alpine 分支 |

更多细节见 [`docs/features/eda-core/operator-guide.md`](../eda-core/operator-guide.md) §10。

---

## 6. 关键引用

| 路径 | 说明 |
|---|---|
| `config/manifest.yml` | 端口 + 镜像版本 SSOT |
| `inventory/hosts.ini` | 物理拓扑 SSOT（hub_local/remote、targets_*） |
| `inventory/local/vault.yml` | 加密的 admin 密码 |
| `playbooks/deploy_hub.yml` | Path A 主入口 |
| `roles/infra_baseline/` | OS 基线（apt + docker + ansible 用户）；OS-family 守门已就绪 |
| `roles/ansispire_hub/` | Hub 服务部署（rsync + .env 渲染 + token mint） |
| `roles/ansispire_audit/` | Audit 三件套部署 |
| `Makefile` | `hub-deploy` / `hub-deploy-check` / `manifest-sync` / `controller-*` / `test-eda*` |

---
*Updated: 2026-05-10 (Round 4 closure of TASK-001).*
