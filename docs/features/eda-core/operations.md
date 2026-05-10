# 高级自愈场景速查手册 (Advanced Self-Healing — Maintainer Reference)

> **本手册定位**：给已熟悉本项目的 maintainer 用的速查参考，命令为主、注释稀疏。
>
> **第一次接触？** 先去看 [`operator-guide.md`](operator-guide.md) — 那一份从零开始、含原理 + 故障路径，不假设你看过其他文档。

本手册按 `docs/TESTING_GOVERNANCE.md` §2，凡验证阶段实际跑过的命令、捕获的日志、踩过的坑，必须立即在此文件同步——本文件即"实战通过的、干净的、无占位符的"操作真相。

最近一次端到端验证：2026-05-10 Round 4，含 Path A 真部署 + Path B docker compose 双路径。证据链：[`round4-2026-05-10.changelog.md`](../../reviews/feat-eda-advanced-healing/round4-2026-05-10.changelog.md) §4 + [`round3-2026-05-09.changelog.md`](../../reviews/feat-eda-advanced-healing/round3-2026-05-09.changelog.md) §6。

---

## 1. 逻辑架构：自愈生命周期 (Mechanism)

Ansispire 的自愈是高度解耦的闭环系统：

1. **产生信号 (Trigger)**：数据面发生故障 → 报错被审计平面捕获，落 `events.jsonl`。
2. **内容识别 (Matching)**：`reactor.py` v2.3 用 `_contains` 匹配 `extensions/eda/rules.json`。
3. **身份通行 (Auth)**：Reactor 用 bootstrap 自动 mint 的 **Bearer Token** 调用 Semaphore API（无明文密码）。
4. **远程调用 (Action)**：Reactor `POST /api/project/<id>/tasks`，按 `template_name` 动态解析 template_id。
5. **物理修复 (Execution)**：Semaphore 启动 Ansible runner 跑 `playbooks/remediation/*.yml`。

文件入口：

| 角色 | 路径 |
|---|---|
| 反应引擎 | `controller/audit/reactor.py` |
| 规则定义 | `extensions/eda/rules.json` |
| 事件契约 | `extensions/eda/events.schema.json` |
| IaC 引导 | `controller/semaphore/bootstrap.yml` |
| 端口 + 镜像版本 SSOT | `config/manifest.yml` |
| 修复剧本 | `playbooks/remediation/*.yml` |
| Token 落盘（Path B） | `controller/semaphore/.secrets` (gitignored) |
| Token 落盘（Path A） | `<hub>:/var/lib/ansispire/state/.eda_token`（rsync exclude） |

---

## 2. 操作规程 (Operations)

### 2.1 Path B（dev / 测试入口）

```bash
make controller-up           # 起 Semaphore（自动 manifest-sync 渲染 .env）
make controller-bootstrap    # IaC 拨备 + mint API token → .secrets
make controller-audit-up     # 起 sink/relay/reactor（自动加载 .secrets）
```

`make controller-bootstrap` 会从 `controller/semaphore/.env` 读 admin 账号/密码，把它们以 `-e semaphore_user=... -e semaphore_password=...` 形式传给 playbook。**不要** 自己拼 `sem_pass=...` 之类的简写——HEAD 版 bootstrap 期待的变量名是 `semaphore_password`。

### 2.1' Path A（真部署入口）

```bash
make hub-deploy-check HUB_NODE=remote   # 干跑（强烈推荐先做）
make hub-deploy HUB_NODE=remote         # 真部署到 [hub_remote] 主机
# HUB_NODE 可选：local|remote|all
# 自动加载 .vault_pass；密码文件路径可用 VAULT_PASSWORD_FILE=... 覆盖
```

### 2.2 直接调用 playbook（备选）

```bash
PASS=$(grep '^SEMAPHORE_ADMIN_PASSWORD=' controller/semaphore/.env | cut -d= -f2-)
.venv/bin/ansible-playbook controller/semaphore/bootstrap.yml \
  -e semaphore_password="$PASS"
```

`semaphore_url` 不再需要传 —— bootstrap 通过 `vars_files: config/manifest.yml` 派生。

### 2.3 故障注入（防呆测试）

```bash
docker exec ansispire-audit-sink sh -c 'printf "%s\n" \
  "{\"payload\":{\"event\":{\"object_type\":\"task\",\"description\":\"Disk Full on ans-hk01\"}}}" \
  >> /var/log/semaphore/events.jsonl'
```

注：`-it` 标志在脚本场景下可省（避免 TTY 错误）。

### 2.4 日志审计（PASS 判定）

观察 reactor 输出：

```
docker logs -f ansispire-audit-reactor
```

期望三行（顺序出现，时间戳省略）：

```
[reactor] received event: unknown
[reactor] MATCH FOUND: Remediation: Disk Full
[reactor] remediation triggered: template=<id> (Auto Remediation: Disk Cleanup), status=201
```

`template=<id>` 中的 `<id>` 由 Semaphore 在创建时分配，不是常量；reactor v2.3 按 `template_name` 动态解析。**不要把 `template=1` 写死为判定标准**——这是 Round 1 之前 Gemini 文档里的具体例子，不普遍。

### 2.5 在 Semaphore 端确认任务确实执行

```bash
TOKEN=$(grep '^SEMAPHORE_API_TOKEN=' controller/semaphore/.secrets | cut -d= -f2-)
curl -sS -H "Authorization: Bearer $TOKEN" \
  'http://localhost:3300/api/project/1/tasks?limit=3' | python3 -m json.tool
```

期望最近一条：

```json
{
  "template_id": <id>,
  "status": "success",
  "tpl_alias": "Auto Remediation: Disk Cleanup",
  "tpl_playbook": "playbooks/remediation/disk_cleanup.yml"
}
```

注意 token 末尾经常有 `=` 号（base64-padding），用 `cut -d= -f2-`（带 `-`），不是 `-f2`。

### 2.6 测试金字塔 (L1+L2+L3+L4)

```bash
make test-eda             # L1 (14) + L2 (9) + L3 (5)；< 1 秒；可进 verify
make test-eda-e2e         # L4 (1)；真 docker；~60 秒；不进 verify
```

L1 期望 `Ran 14 tests ... OK`，L2 9 cases，L3 5 cases。L4 在隔离的 `ansispire-e2e` compose project（端口 3320/3330）跑，不影响 dev 栈。

### 2.7 Syntax 校验（治理强制项）

```bash
make syntax
```

stag 与 prod 双 inventory 全绿后才可进入下一轮。

---

## 3. 设计标准 (LTS Standards)

| 维度 | 标准 | 实施位置 |
|---|---|---|
| 数据库 | 强制 SQLite，BoltDB 已弃用 | `controller/semaphore/docker-compose.yml` `SEMAPHORE_DB_DIALECT=sqlite`；image pinned `v2.18.2`（SQLite 默认） |
| 认证 | M2M 必须 Bearer Token，禁明文密码 | bootstrap mint → `.secrets`；reactor/relay env-file 加载 |
| 端口 + 镜像 | host port = container + 300（IANA 标准协议端口除外）；版本默认 `latest`、生产显式 pin | `config/manifest.yml` SSOT；`make manifest-sync` 渲染到 `.env` |
| 镜像 | 禁用 `:latest` 在生产（compose 不自动 pull → 实质冻结），显式 pin | `config/manifest.yml` `*_pinned` 字段 |
| 自动化 | UI 零点击；project/repo/inventory/template/token 全部 IaC | `controller/semaphore/bootstrap.yml` |
| Path A 凭据 | 永远不进 git、永远不进 rsync 上行 | `inventory/local/vault.yml`（加密），rsync excludes 见 `roles/ansispire_hub/tasks/main.yml` |
| Path A 状态 | 状态文件离 rsync target dir | `<hub>:/var/lib/ansispire/state/.eda_token` |

---

## 4. 故障排查 (Troubleshooting)

| 症状 | 根因 | 修复 |
|---|---|---|
| `Password must be provided via -e semaphore_password=` | 用了 `sem_pass=` 这类旧版（Gemini 158 行重写）变量名 | 用 `make controller-bootstrap`，或直接 `-e semaphore_password=...` |
| reactor 日志 `remediation failed: SEMAPHORE_API_TOKEN not set` | bootstrap 没跑过，或 audit 栈未重启 | `make controller-bootstrap && make controller-audit-down && make controller-audit-up` |
| reactor 收到事件但无 MATCH | rules.json 里的 `template_name` 与 bootstrap 注册的不一致 | `curl -H "Authorization: Bearer $TOKEN" /api/project/1/templates` 比对 name |
| `[reactor] JSON parse error` | `printf` 注入命令含物理换行 / 单引号嵌套错 | 命令一行写完，外层用单引号包内层用 `\"` |
| Semaphore 启动后 web UI 端口连不上 | 本地 `.env` 端口 drift | `make manifest-sync`（重新渲染管理块）后 `make controller-down && make controller-up` |
| `make controller-bootstrap` 报权限错 / `.secrets` owner=root | `ansible.cfg` 全局 `become=True` 影响了 control-host 文件写入 | 已修复：bootstrap.yml 与 manifest_sync.yml 头部显式 `become: false` |
| `cut -d= -f2` 拿到的 token 不是完整值 | token 末尾有 `=`，被 `-f2` 截断 | 用 `cut -d= -f2-`（带 `-`） |
| Path A `--check` 报 `cookies_string` 缺失 | --check 下 Login API 不真发，token 块未跳过 | 已修复：role 加 `when: not ansible_check_mode` |
| Path A rsync 把 `.env` / `.secrets` / `.demo_*.pw` 上传 | 旧 rsync_opts 只 exclude `.git` / `.venv` | 已修复：见 `roles/ansispire_hub/tasks/main.yml` 21-项 excludes |
| Path A 部署后 `.eda_token` 每次被 rsync delete | 旧版状态文件在 rsync target dir | 已修复：迁到 `/var/lib/ansispire/state/` |

---

## 5. 端口 / 版本 / 认证（SSOT 速查）

```
config/manifest.yml                     ← 唯一端口 + 镜像版本编辑入口
   ├── playbooks/manifest_sync.yml      ← 渲染 4 键到 .env 的 # BEGIN/END manifest 块
   ├── controller/semaphore/bootstrap.yml ← vars_files 派生 semaphore_url
   └── playbooks/deploy_hub.yml         ← vars_files 让 role defaults 读到

controller/semaphore/.env               ← 用户编辑：admin/timezone（manifest 块由脚本管理）
controller/semaphore/.secrets           ← bootstrap 自动写入 SEMAPHORE_API_TOKEN（Path B）
<hub>:/var/lib/ansispire/state/.eda_token ← bootstrap 自动写入（Path A）
```

修改端口 / 版本流程：编辑 `config/manifest.yml` → `make manifest-sync`（Path B 自动；Path A 由 deploy_hub 派生）→ `make controller-down && make controller-up` 或 `make hub-deploy HUB_NODE=...`。

---

## 6. 当前已实施 vs 后续计划

✅ Round 1 (2026-05-09)：Path B 底盘修复 + 端口 SSOT + bootstrap M2M token + operations.md 重写
✅ Round 2 (2026-05-09)：测试分层 L1+L2+L3 进 verify
✅ Round 3 (2026-05-09)：`extensions/eda/events.schema.json` 契约化、L4 e2e harness、DB Failover rule `enabled: false`
✅ Round 4 (2026-05-10)：Path A 全面硬化 + manifest SSOT + inventory `[hub_local]`/`[hub_remote]` 拓扑 + rsync 强 excludes + state 迁出 + OS-family 守门 + `make hub-deploy HUB_NODE=` 包装。**TASK-001 闭环。**

后续：
- TASK-007（多 OS target fleet）：4 台 VPS 接入 `[targets_*]`、实现 `infra_baseline` RHEL/Alpine 分支
- TASK-008（DB Failover 真实化）：实现 `playbooks/remediation/db_failover.yml`、把 rule `enabled: true`、加 L4 用例

---
*Manual Version: aligned with `feat/eda-advanced-healing` Round 4, 2026-05-10. 维护人：每轮架构改动需同步本文件 §1 表格 + §3 设计标准 + §4 排查表 + §6 进度。*
