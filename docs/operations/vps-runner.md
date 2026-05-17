# VPS Runner 运维指南 (Operator Guide)

> **本文档定位**：操作员手册——面向需要在没有 AI 辅助情况下独立操作的人员。命令完整、含 rationale 与 recovery 路径。
>
> **如果你只想速查命令**：见 §6 速查表。

---

## 1. 概览

`vps_runner` 是 Ansispire 的 VPS 生命周期管理插件，基于 [`ansible-runner`](https://ansible.readthedocs.io/projects/runner/) 与标准 Ansible inventory。

**核心设计**：
- 执行模型：`ansible_runner.run()` 直接驱动 playbook；无 subprocess 包装。
- 状态模型：`inventory/vps_runner/<env>/hosts.yml` + `host_vars/<alias>.yml`——单一 SSOT。
- 调度模型：CLI 直接命令，无 inbox / state machine。
- 并发模型：Ansible native `forks=20`（默认），单次 `run()` 处理整个 inventory。

**前置条件**：
- VPS 已装 python3（项目目标场景：Ubuntu / Debian / 带 python3 的 Alpine）。
- 操作员工作站已通过 `uv sync` / `pip install -e ".[test]"` 安装 `ansible-runner>=2.4.0`。

---

## 2. Inventory 结构

```text
inventory/vps_runner/
  dev/
    hosts.yml                   # vps_targets group → hosts (aliases)
    host_vars/<alias>.yml       # 每个 alias 的连接 + 角色变量 + 元数据
  stag/                         # placeholder
  prod/                         # placeholder
```

**host_vars 结构（核心字段）**：

```yaml
---
# 连接（Ansible 标准）
ansible_host: <ip>
ansible_port: <managed_port>     # 通常 1024-65535 高位端口
ansible_user: deploy
ansible_python_interpreter: /usr/bin/python3
ansible_ssh_private_key_file: /home/netcup/.ssh/ansispire_ed25519

# 角色变量（playbook 直接读）
security:
  root_login_disabled: true
  password_login_disabled: true
  ufw_enabled: true
  fail2ban_enabled: true
features:
  base_packages: true
  unattended_upgrades: true
  ufw: true
  fail2ban: true

# vps_runner 元数据（CLI 读写）
vps_runner:
  bootstrap_port: 22            # 首次连接端口
  bootstrap_user: root          # 首次连接用户
  managed_port: 1156            # onboard 后的目标端口（必须 != 22）
  managed_user: deploy          # 目标用户
  identity_file: <path>         # 私钥路径（控制端）
  ansible_public_key: <path>    # 公钥路径
  personal_keys:                # 可选额外 authorized_key
    - name: operator
      public_key: <path>
  status: active                # CLI 维护
  last_run:                     # CLI 维护
    id: vps-runner-...-onboard
    action: onboard
    status: successful
    completed_at: 2026-05-16T...
  updated_at: 2026-05-16T...
```

---

## 3. CLI 子命令

入口：`python -m plugins.vps_runner.cli <subcommand>` —— 或 Round 4 后通过 Makefile target。

**前置（必须先做一项）**：本仓库的 Python 依赖装在 `.venv/` 里，本机系统 `python` 通常不存在（Debian/Ubuntu 只有 `python3`）。下面任选其一：

```bash
# 方式 A（推荐，shell session 内全局生效）
source .venv/bin/activate
python -m plugins.vps_runner.cli list --env dev

# 方式 B（每次显式 venv 路径，无 shell 状态依赖；适合脚本 / CI）
.venv/bin/python -m plugins.vps_runner.cli list --env dev

# 方式 C（最省事，Round 6 起所有日常子命令都有 Make wrapper）
make vps-list                                      # 等价 list
make vps-audit ALIAS=hk-d12                        # 等价 audit --limit
make vps-add-host ALIAS=de-d12-1 IP=203.0.113.42  # 等价 add-host
make vps-onboard ALIAS=de-d12-1                    # 等价 onboard --first-time --ask-pass --ask-become-pass
make vps-modify ALIAS=hk-d12 ARGS='--add-package=htop'  # 等价 modify
make vps-remove ALIAS=hk-d12                       # 等价 remove --yes --cleanup-remote
```

下文示例统一写作 `python -m ...`（假设方式 A）。要 bare shell 直接跑，把 `python` 换成 `.venv/bin/python` 即可，或用方式 C 的 Make wrapper。

所有子命令都接受 `--env {dev,stag,prod}`（默认 `dev`）。

### 3.1 `list` — 查看清单（不调 Ansible）

```bash
python -m plugins.vps_runner.cli list --env dev
python -m plugins.vps_runner.cli list --env dev --format json
```

**输出**：alias / host / port / user / status / last_action / updated_at 表格或 JSON。**完全本地读 host_vars 文件，无网络调用**。

### 3.1b `add-host` — 创建新管理节点的 inventory 条目（Round 6 起）

```bash
python -m plugins.vps_runner.cli add-host <alias> --ip <IP> \
  [--port 1156] [--user ansible] [--status pending] [--env dev]

# 或 Make wrapper（注意：用 MANAGED_PORT / MANAGED_USER 避免和 shell env 的 USER 撞）
make vps-add-host ALIAS=<alias> IP=<IP> [MANAGED_PORT=1156] [MANAGED_USER=ansible] [ENV=dev]
```

**做什么**：根据传入字段在 `inventory/vps_runner/<env>/host_vars/<alias>.yml` 生成 slim 格式文件（只放每机特有覆盖，共享默认从 `group_vars/vps_targets.yml` 继承），同时把 alias 追加到 `hosts.yml` 的 `vps_targets.hosts` 块。**不调 Ansible，无网络操作**。

**字段默认**：`port=1156`、`user=ansible`、`status=pending`（onboard 成功后自动改 `active`）。

**校验**：
- alias 必须未在 `hosts.yml` 出现，且 `host_vars/<alias>.yml` 不存在（防止覆盖）
- port 必须在 `[1024, 65535]` 且不能是 `22`（与 onboard.yml `pre_tasks` assert 对齐）

**输出**：成功时给下一步提示：
```
==> created inventory/vps_runner/dev/host_vars/de-d12-1.yml
==> added 'de-d12-1' to inventory/vps_runner/dev/hosts.yml

Next: vps-runner onboard de-d12-1 --env dev --first-time --ask-pass
  (add --ask-become-pass if the bootstrap user's sudo requires a password)
```

**典型新机三步流程**：
```bash
make vps-add-host ALIAS=de-d12-1 IP=203.0.113.42
make vps-onboard ALIAS=de-d12-1               # terminal 输 root 密码
make vps-audit ALIAS=de-d12-1                 # 验证可达
```

### 3.2 `audit` — 健康探测

```bash
python -m plugins.vps_runner.cli audit --env dev
python -m plugins.vps_runner.cli audit --env dev --limit hy-hk-u24
python -m plugins.vps_runner.cli audit --env dev --forks 5 --quiet
```

**做什么**：对每个 host 跑 ping / uptime / df / free / 操作系统 facts。**幂等，只读**。

**典型输出**（`--quiet` 模式）：
```
==> vps-runner audit env=dev limit=*
==> run_id: vps-runner-20260516T120000Z-dev-audit
==> artifact: runtime/logs/vps_runner/vps-runner-20260516T120000Z-dev-audit
==> status:   successful (rc=0)

Host results:
  ✓ hy-hk-u24        ok
  ✓ hk-d13           ok
```

### 3.3 `onboard` — 首次接入或重新应用

```bash
# 已配置好 ansible 公钥 + sudo NOPASSWD 的「重新 onboard」（最常见）
python -m plugins.vps_runner.cli onboard hy-hk-u24 --env dev

# 首次接入（节点还在 root@22 + sudo 需密码状态）
python -m plugins.vps_runner.cli onboard hy-hk-u24 --env dev \
    --first-time --ask-pass --ask-become-pass
```

**前置**：`host_vars/<alias>.yml` 必须已存在（操作员手动创建——见 §4 流程）。

**`--first-time` 语义**：临时把 `ansible_user` / `ansible_port` 用 extravars 覆盖为 `vps_runner.bootstrap_user@bootstrap_port`（默认 `root@22`）。**只影响这一次运行**——host_vars 中的 `ansible_user/port` 保持「目标态」。

**`--ask-pass` / `--ask-become-pass`**：交互式输入 SSH / sudo 密码。`onboard` 成功后这两者通常都不再需要（密钥 + NOPASSWD 已就位）。

**幂等**：成功后写回 `vps_runner.status: active` + `vps_runner.last_run`。再次跑相同命令是安全的。

### 3.4 `modify` — Ad-hoc 修改

```bash
python -m plugins.vps_runner.cli modify hy-hk-u24 --env dev \
    --add-package "htop,ncdu" \
    --add-port "8080,9090" \
    --toggle-fail2ban on
```

**支持的修改**：
- `--add-package` / `--remove-package`：CSV 包名
- `--add-port` / `--remove-port`：CSV TCP 端口（UFW allow/deny）
- `--toggle-fail2ban on|off`

CLI 把这些组装成 `vps_changes` extravar 传给 `modify.yml`，每个 section 都是可选的。**空修改集会被拒绝**（exit 64 / EX_USAGE）。

### 3.5 `remove` — 移除

```bash
# 只删本地 inventory 条目（保留远端配置——节点回到 distro 默认状态由你手动接管）
python -m plugins.vps_runner.cli remove hy-hk-u24 --env dev --yes

# 同时清理远端的 Ansispire sshd 配置 drop-in
python -m plugins.vps_runner.cli remove hy-hk-u24 --env dev --yes --cleanup-remote
```

**必须传 `--yes`**——防止误删（exit 64 否则）。

**`--cleanup-remote` 语义**：调用 `remove.yml`，删除 `/etc/ssh/sshd_config.d/00-ansispire.conf` + `99-ansispire.conf` 并重跑 `sshd -t` 验证。**UFW 规则与 managed user 故意保留**（安全默认：把节点交还的时候手工处理）。

---

## 4. 首次 Onboard 完整流程

### 步骤 1：创建 `host_vars/<alias>.yml`

```bash
# 参照已有节点为模板
cp inventory/vps_runner/dev/host_vars/hy-hk-u24.yml \
   inventory/vps_runner/dev/host_vars/<new-alias>.yml
$EDITOR inventory/vps_runner/dev/host_vars/<new-alias>.yml
```

**关键字段（onboard 前必填）**：
- `ansible_host`：节点 IP
- `ansible_port`：onboard 后的**目标**端口（必须 != 22，建议 1024-65535）
- `ansible_user`：目标用户（onboard 会创建）
- `vps_runner.bootstrap_port` / `bootstrap_user`：当前**实际**端口/用户（首次通常 `22` / `root`）
- `vps_runner.managed_port` / `managed_user`：与 `ansible_port` / `ansible_user` 保持一致
- `vps_runner.identity_file`：操作员私钥路径

### 步骤 2：把 alias 加入 `hosts.yml`

```yaml
all:
  children:
    vps_targets:
      hosts:
        hy-hk-u24:    # 已有
        <new-alias>:  # 新增
```

### 步骤 3：跑 onboard

```bash
python -m plugins.vps_runner.cli onboard <new-alias> --env dev \
    --first-time --ask-pass --ask-become-pass
```

输入 root 的 SSH 密码 + sudo 密码。playbook 会：
1. 装 base packages + unattended-upgrades
2. 创建 managed user，授权 SSH key，配置 sudo NOPASSWD（默认）
3. 写 sshd drop-in（迁端口、禁 root、禁密码、禁 kbd-interactive）
4. 重载 sshd 并验证新端口连通
5. 关闭 bootstrap port（若 `vps_runner.close_bootstrap_port_after_success: true`）
6. 配置 UFW / fail2ban（按 `features.*`）。**docker 当前不在 onboard 范围内**——见 §7 设计沿革。
7. 写本地 `~/.ssh/config.d/ansispire.conf` 条目供后续直连

成功后再跑一次 audit 验收：
```bash
python -m plugins.vps_runner.cli audit <new-alias> --env dev
```

---

## 5. 失败排查

### 5.1 找 artifacts

每次 ansible-runner 调用都会落地：
```text
runtime/logs/vps_runner/<run_id>/
  status              # successful | failed | timeout
  rc                  # process exit code
  command             # 实际命令行
  stdout              # 完整 ansible 输出
  job_events/*.json   # 每个 task 的结构化事件（per-host）
  fact_cache/         # gather_facts 收集到的 facts
```

`<run_id>` 形如 `vps-runner-20260516T120000Z-dev-onboard`。最近 10 个保留，更早的自动淘汰。

### 5.2 常见失败模式

| 症状 | 可能原因 | 排查 |
|---|---|---|
| `Permission denied (publickey)` | 公钥没在远端 / 私钥路径错 / sudo NOPASSWD 未生效 | 检查 `vps_runner.identity_file`；首次 onboard 加 `--ask-pass --ask-become-pass` |
| `host_vars not found` | 你没创建 `host_vars/<alias>.yml` | 见 §4 步骤 1 |
| onboard 中途失败但 ssh 已迁端口 | 部分配置已落，节点处于半配状态 | 修改 `vps_runner.bootstrap_port: <new>` + `bootstrap_user: deploy`，重跑 `onboard` 续刷 |
| `ssh.managed_port must be a non-22 high port` assert 失败 | host_vars 里 `managed_port: 22` 或 `< 1024` | 改 host_vars，重跑 |
| audit `unreachable` 但 ssh 手工能上 | `ansible_python_interpreter` 路径不存在 / known_hosts 不匹配 | 进 `runtime/logs/.../stdout` 看 ansible 报错；known_hosts 不匹配时手工 `ssh-keygen -R '[host]:port'` |
| `summary.hosts` 是空集 | host_vars 里 YAML 语法错误，ansible-runner 提前退出 | `python -c "import yaml; yaml.safe_load(open('...').read())"` 自检 |

### 5.3 恢复半配节点

如果 onboard 卡在 SSH 迁端口之后但 UFW / fail2ban 之前：
1. 在 host_vars 中把 `vps_runner.bootstrap_port` / `bootstrap_user` 改成「当前实际」状态（通常已经是 `managed_port` / `managed_user`）。
2. **不**加 `--first-time`，直接 `onboard` 重跑——playbook 是幂等的，已完成的任务会跳过。
3. 还不行就看 `runtime/logs/vps_runner/<latest>/stdout` 定位具体 failed task。

---

## 6. 速查表

```bash
# 看清单
python -m plugins.vps_runner.cli list --env dev

# 健康检查（全部 / 单台）
python -m plugins.vps_runner.cli audit --env dev
python -m plugins.vps_runner.cli audit --env dev --limit hy-hk-u24

# 首次 onboard
python -m plugins.vps_runner.cli onboard <alias> --env dev \
    --first-time --ask-pass --ask-become-pass

# 重新 onboard（idempotent refresh）
python -m plugins.vps_runner.cli onboard <alias> --env dev

# 改包 / 防火墙 / fail2ban
python -m plugins.vps_runner.cli modify <alias> --env dev \
    --add-package "htop" --add-port "8080" --toggle-fail2ban on

# 移除（仅本地 inventory）
python -m plugins.vps_runner.cli remove <alias> --env dev --yes

# 移除（同时清远端 sshd drop-in）
python -m plugins.vps_runner.cli remove <alias> --env dev --yes --cleanup-remote
```

**测试**：
```bash
# 单元测试（快）
pytest plugins/vps_runner/tests/ -m 'not integration'

# 集成测试（真调 ansible-runner 对 TEST-NET-1，~11s）
pytest plugins/vps_runner/tests/ -m integration
```

---

## 7. 设计沿革

历史上 ansispire 曾有一个 `plugins/vps_manager/` 插件（YAML inbox + subprocess wrapper + 自写 callback + `runtime/state/vps_inventory.yml`），已于 2026-05-16 (Round 4-b cutover) 整体移除。新旧对照仅供理解既有 `runtime/state/` 目录残留 + git 历史：

| 维度 | 旧 `vps_manager` | 新 `vps_runner` |
|---|---|---|
| 执行 | `subprocess.Popen("ansible-playbook ...")` | `ansible_runner.run(...)` |
| 状态 | `runtime/state/vps_inventory.yml`（自写 schema） | `inventory/vps_runner/<env>/host_vars/`（Ansible 标准） |
| 调度 | inbox/pending/processing/done state machine | CLI 直接命令 |
| 结果 | 自写 callback plugin | `Runner.host_events()` / `Runner.stats` |
| Lint | 通过但有 path-based 反 idiom | `ansible-lint --profile production` 通过 |

**runtime/state/vps_inventory.yml 处理**：未被 git 追踪，cutover 后不再读写。本地可由操作员直接 `rm` 清理（保留也无害——新插件不读它）。

**为什么换**：详见 [`docs/reference/investigations/IVG-MULTI-SERVER-ANSIBLE-PRACTICE.md`](../reference/investigations/IVG-MULTI-SERVER-ANSIBLE-PRACTICE.md) 与 [`IVG-REFLECT-BESTPRACTICE-GAP.md`](../reference/investigations/IVG-REFLECT-BESTPRACTICE-GAP.md)——简短说：旧实现是「在 Ansible 之上手工加层」的反范式，不可扩展，不能复用社区工具。

---
*Last updated: 2026-05-16 (Round 4-a)*
