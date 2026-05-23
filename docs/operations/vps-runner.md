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
make vps-add-host ALIAS=de-d12-1 IP=203.0.113.42  # 等价 add-host (flag mode)
make vps-add-host                                  # 等价 add-host (wizard 模式 — R11)
make vps-reonboard ALIAS=de-d12-1                  # 等价 onboard (key-only re-onboard; 首次接入用 wizard)
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

### 3.1b `add-host` — 创建新管理节点的 inventory 条目（Round 7 起三种入口）

三种入口终点相同（host_vars/&lt;alias&gt;.yml + hosts.yml 加 alias 行 + 可选直接 onboard），按操作习惯任选其一：

```text
① Wizard:        make vps-add-host                       # 4 字段交互式填
② Flag:          make vps-add-host ALIAS=x IP=y          # 一键 scaffold
③ 手写模板:      cp plugins/vps_runner/examples/host_vars.yml.template \
                   inventory/vps_runner/dev/host_vars/<alias>.yml
                 # 编辑文件填 ansible_host 等 4 个字段
                 # 在同一目录 hosts.yml 手动加 `  <alias>:` 行
```

**Wizard 模式**（无参数，**R11 重写**——首次接入唯一推荐入口）：

```bash
make vps-add-host                          # 等价 python -m plugins.vps_runner.cli add-host --env dev
```

依次提示 8 个字段（默认值回车接受）：

```text
Alias [必填]:                          de-d12-1
IP / hostname [必填]:                  203.0.113.42
User (bootstrap) [root]:                ↩
认证方式: (p) 密码 / (k) 密钥 [p]:       k     ← 选 k 走密钥分支，选 p 走密码分支
Private key (PEM …自动结束):            -----BEGIN OPENSSH PRIVATE KEY-----
                                       …
                                       -----END OPENSSH PRIVATE KEY-----
Port (bootstrap) [22]:                  ↩
Managed user [ansible]:                 ↩
Managed port [1156]:                    ↩
==> created host_vars/de-d12-1.yml
==> added 'de-d12-1' to hosts.yml
==> wrote temp bootstrap key: runtime/keys/vps_runner/de-d12-1.key
==> first-time mode: connecting as root@22 with temp key ...
==> vps-runner onboard alias=de-d12-1 env=dev
...   (real ansible-runner output) ...
==> verifying standard automation key against ansible@1156 ... ✓
==> cleaned up temp key
==> host_vars/de-d12-1.yml updated (status=active, bootstrap_key cleared)
==> wrote local SSH alias: ~/.ssh/config.d/de-d12-1.conf
```

**字段语义**：

- bootstrap `User` / `Port`：首次连接的用户和端口（默认 `root@22`）；onboard 完成后这条通道关闭（防火墙 + sshd 配置）。
- **认证方式**：`p` 密码 → wizard 用 `getpass` 收一次密码（不回显，不写盘，通过 `ansible_runner` 的 `passwords=` 字典注入）；`k` 密钥 → 粘贴 PEM 私钥全文，wizard 自动以 `-----END … PRIVATE KEY-----` 行识别结束，写到 `runtime/keys/vps_runner/<alias>.key`（0600，gitignored），onboard 用完即删（密钥分支 happy path）。
- bootstrap user 非 root：额外问一次 sudo 密码（默认复用 SSH 密码 / 留空尝试 NOPASSWD）。
- managed `User` / `Port`：onboard 完成后的稳定态（默认 `ansible@1156`）。

**密钥分支生命周期**：

1. wizard 收 PEM → 写 `runtime/keys/vps_runner/<alias>.key`（0600）
2. onboard 跑（用临时 key 连 bootstrap channel；装好标准自动化公钥 `ansispire_ed25519.pub` 到 managed user）
3. 后置验证：ansible 用标准自动化密钥 ping managed user → 通即清理临时 key
4. **失败保留**：onboard 或 verify 失败时，临时 key 不删，`vps_runner.bootstrap_key` 字段记录路径；下次 `onboard --first-time` 自动读这条 hint 注入 extravars 重试

**预检失败**：wizard 启动时检查 `~/.ssh/ansispire_ed25519` / `.pub` 和 `~/.ssh/id_ed25519.pub` 三把密钥都在；任一缺失立刻 rc=3 退出并提示对应的 `ssh-keygen` 命令。

**同名 alias 已存在**（4 选项菜单）：

```
==> 检测到 alias 'de-d12-1' 已存在:
  IP:          203.0.113.42
  Bootstrap:   root@22
  Managed:     ansible@1156
  Status:      active  (last_run: onboard)

请选择处理方式:
  1) 跳过并结束                              [默认]
  2) 使用新的 alias 继续
  3) 验证现有配置并运行 audit        ← 基础验证 + 合规检查；发现差异后可选择 managed repair
  4) 强制覆盖现有配置 (use when current is broken)
```

选择 3 时，CLI 先做 host_vars schema / managed SSH / Ansible ping 基础验证；通过后继续运行 `audit.yml`，按当前项目规则列出未正确配置或未正常运行的项目（例如 managed sudo、sshd 策略、UFW、fail2ban）。若有 findings，用户可选择 `y` 直接运行 managed repair（等价 `onboard <alias> --env <env>`）来修正或补全。

**非 TTY 拒绝**：stdin 不是终端（pipe / here-doc / CI），wizard 模式立刻退出 rc=2 并提示用 flag 模式。

**Flag 模式**（一键 scaffold，等价 Round 6 行为）：

```bash
python -m plugins.vps_runner.cli add-host <alias> --ip <IP> \
  [--port 1156] [--user ansible] [--status pending] [--env dev]

# 或 Make wrapper（用 MANAGED_PORT / MANAGED_USER 避免和 shell env 的 USER 撞）
make vps-add-host ALIAS=<alias> IP=<IP> [MANAGED_PORT=1156] [MANAGED_USER=ansible] [ENV=dev]
```

**手写模板模式**：直接复制 `plugins/vps_runner/examples/host_vars.yml.template`（slim — 只 4 个用户填字段），编辑后手动在同一目录的 `hosts.yml` 加 alias 行。适合需要预填 status/自定义 vps_runner 字段的场景。

**共同行为**：在 `inventory/vps_runner/<env>/host_vars/<alias>.yml` 生成 slim 文件（只放每机特有覆盖，共享默认从 `group_vars/vps_targets.yml` 继承），同时把 alias 追加到 `hosts.yml` 的 `vps_targets.hosts` 块。**不调 Ansible，无网络操作**。

**字段默认**：`port=1156`、`user=ansible`、`status=pending`（onboard 成功后自动改 `active`）。

**校验**：
- alias 必须未在 `hosts.yml` 出现，且 `host_vars/<alias>.yml` 不存在（防止覆盖）
- port 必须在 `[1024, 65535]` 且不能是 `22`（与 onboard.yml `pre_tasks` assert 对齐）

**SSH 密钥分离**（Round 7 起）：Ansible 自动化和 operator 直连使用两把独立密钥：

| 用途 | 文件 | 配置位置 |
|---|---|---|
| Ansible 自动化连接 managed VPS | `~/.ssh/ansispire_ed25519` | `group_vars/vps_targets.yml::vps_runner_defaults.identity_file` |
| 你 (operator) 手动 `ssh <alias>` | `~/.ssh/id_ed25519` | `~/.ssh/config.d/<alias>.conf`（onboard 成功后由 CLI 自动写入） |

两条路径互不交叉：Ansible 永远不读 `id_ed25519`，本地 SSH 配置永远不引用 `ansispire_ed25519`。

**典型新机三步流程**（wizard 模式）：
```bash
make vps-add-host                             # 填 4 字段，回车 Y 直接进 onboard
make vps-audit ALIAS=de-d12-1                 # 验证可达
ssh de-d12-1                                  # 用 ~/.ssh/config.d/de-d12-1.conf 直连
```

### 3.2 `audit` — 健康探测

```bash
python -m plugins.vps_runner.cli audit --env dev
python -m plugins.vps_runner.cli audit --env dev --limit hy-hk-u24
python -m plugins.vps_runner.cli audit --env dev --forks 5 --quiet
```

**做什么**：对每个 host 跑 ping / uptime / df / free / 操作系统 facts，并执行 inventory 中声明的 `vps_runner_audit_rules`。规则是数据化配置：每条规则声明 `command`、`expected_*` 和可选 `enabled` 条件，CLI 只展示 findings。**幂等，只读**。

当前 dev 默认规则在 `inventory/vps_runner/dev/group_vars/vps_targets.yml`，覆盖 managed sudo、sshd 策略、UFW、fail2ban。后续调整检查项、期望值、开关条件时，优先改 `vps_runner_audit_rules`；单机差异用 host_vars 里的 `vps_runner_audit_rules_disabled` 或 `vps_runner_audit_rules_extra`，不改 CLI。

**典型输出**（`--quiet` 模式）：
```
==> vps-runner audit env=dev limit=*
==> run_id: vps-runner-20260516T120000Z-dev-audit
==> artifact: runtime/logs/vps_runner/vps-runner-20260516T120000Z-dev-audit
==> status:   successful (rc=0)

Host results:
  ✓ hy-hk-u24        ok
  ✓ hk-d13           ok

Project policy audit:
  ✓ hy-hk-u24: compliant
  ✗ hk-d13: 1 finding(s)
      - fail2ban service: expected active; actual failed
```

### 3.3 `onboard` — 重新应用（key-only re-onboard）

> **首次接入走 wizard（§3.1）**：`make vps-add-host` 或 `python -m plugins.vps_runner.cli add-host --env dev` —— 由 wizard 收集 bootstrap 凭据并自动完成首次 onboard。`onboard` 子命令本身**只支持密钥认证**（R11 起 `--ask-pass` / `--ask-become-pass` flag 已移除——它们经 ansible-runner 不可用且首次接入路径已被 wizard 接管）。

```bash
# 已配置好 ansible 公钥 + sudo NOPASSWD 的「重新 onboard」（最常见）
python -m plugins.vps_runner.cli onboard hy-hk-u24 --env dev

# 重跑 wizard 首次失败后的 first-time（auto-injects bootstrap_key 从 host_vars）
python -m plugins.vps_runner.cli onboard hy-hk-u24 --env dev --first-time
```

**前置**：`host_vars/<alias>.yml` 必须已存在（wizard 在 add-host 阶段写入）；标准自动化密钥 `~/.ssh/ansispire_ed25519` 已能登上 managed user。

**`--first-time` 语义**：CLI 先用标准自动化密钥短探测 managed channel。如果 managed 已可达，自动转为普通 repair onboard，不再尝试已经关闭的 bootstrap port；如果 managed 不可达，则传 `vps_first_time_*` marker，让 `onboard.yml` 在 fact gathering 前切到 `vps_runner.bootstrap_user@bootstrap_port`。如果上一次 wizard 失败留下 `vps_runner.bootstrap_key`，本次重跑会自动作为 `vps_first_time_key` 注入，**无需 `--extra-vars`**；任意 onboard 成功后该 retry hint 会清空。host_vars 中的 `ansible_user/port` 始终表示「目标态」。

**`make vps-reonboard`**：等价 `python -m plugins.vps_runner.cli onboard <alias> --env <env>`（不带 `--first-time`，纯密钥重跑）。

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

**R11 起首次接入唯一推荐入口 = wizard**。下面把 wizard 的 8 字段流程 + 临时密钥生命周期串成一遍。

### 步骤 0：前置检查

操作员本机必须存在三把密钥（wizard 启动会强制检查；缺失 rc=3 + 提示 ssh-keygen 命令）：

```bash
ls -la ~/.ssh/ansispire_ed25519 ~/.ssh/ansispire_ed25519.pub ~/.ssh/id_ed25519.pub
# 若任一缺失，先跑：
ssh-keygen -t ed25519 -f ~/.ssh/ansispire_ed25519 -N ''
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519       -N ''
```

并且操作员**手上要有**首次能登上目标 VPS 的凭据（密码或可粘贴的私钥），目标用户拥有 root 或 NOPASSWD-sudo 权限。

### 步骤 1：启动 wizard

```bash
make vps-add-host         # 或 .venv/bin/python -m plugins.vps_runner.cli add-host --env dev
```

### 步骤 2：按提示填 8 字段

见 §3.1 wizard 详细字段说明。关键点：

- 密钥分支：粘贴 PEM 全文（多行；`-----END … PRIVATE KEY-----` 行自动结束输入）
- 密码分支：getpass 不回显，仅内存使用，不写盘
- bootstrap user 非 root：额外问 sudo 密码

### 步骤 3：onboard 自动跑（wizard 内置）

playbook 会：
1. 装 base packages + unattended-upgrades
2. 创建 managed user，授权 SSH key，配置 sudo NOPASSWD（默认）
3. 写 sshd drop-in（迁端口、禁 root、禁密码、禁 kbd-interactive）
4. 重载 sshd 并验证新端口连通
5. 关闭 bootstrap port（若 `vps_runner.close_bootstrap_port_after_success: true`）
6. 配置 UFW / fail2ban（按 `features.*`）；fail2ban 会重启、等待 active，并验证 `sshd` jail 已加载。**docker 当前不在 onboard 范围内**——见 §7 设计沿革。
7. onboard 成功后 CLI 写本地 `~/.ssh/config.d/<alias>.conf`（per-alias 文件，`IdentityFile=~/.ssh/id_ed25519`，operator 直连密钥）。若 `~/.ssh/config` 缺 `Include …config.d/…` 行，CLI 会打印一次提示，加一行 `Include config.d/*` 即可一劳永逸。

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
| `Permission denied (publickey)` | wizard 密钥分支：粘贴的私钥与远端 authorized_keys 不配；wizard 密码分支：密码错；onboard 重跑：自动化标准密钥 ansispire_ed25519 没装到 managed user | 首次接入走 wizard，确认目标用户能凭粘贴的密钥/密码登入；onboard 重跑前 `ssh -i ~/.ssh/ansispire_ed25519 <managed_user>@<host> -p <managed_port>` 验证手工连通 |
| `host_vars not found` | 你没创建 `host_vars/<alias>.yml` | 见 §4 步骤 1 |
| onboard 中途失败但 ssh 已迁端口 | 部分配置已落，节点处于半配状态 | 优先直接重跑 `onboard <alias>`。若你误传 `--first-time`，CLI 会先探测 managed channel；探测成功时自动转为 managed repair，不再连 bootstrap 端口 |
| fail2ban 安装后 `failed` | Debian 12+ 默认无 `/var/log/auth.log`，fail2ban sshd jail 若走文件 backend 会启动失败 | 当前 jail 模板默认 `backend = systemd`（systemd 主机）并安装 `python3-systemd`；重跑 `onboard` 或 `modify --toggle-fail2ban on` 会 restart + active/jail verify |
| `ssh.managed_port must be a non-22 high port` assert 失败 | host_vars 里 `managed_port: 22` 或 `< 1024` | 改 host_vars，重跑 |
| audit `unreachable` 但 ssh 手工能上 | `ansible_python_interpreter` 路径不存在 / known_hosts 不匹配 | 进 `runtime/logs/.../stdout` 看 ansible 报错；known_hosts 不匹配时手工 `ssh-keygen -R '[host]:port'` |
| `summary.hosts` 是空集 | host_vars 里 YAML 语法错误，ansible-runner 提前退出 | `python -c "import yaml; yaml.safe_load(open('...').read())"` 自检 |

### 5.3 恢复半配节点

如果 onboard 卡在 SSH 迁端口之后但 UFW / fail2ban 之前：
1. 先确认 managed SSH 是否可用：`ssh -i ~/.ssh/ansispire_ed25519 <managed_user>@<host> -p <managed_port> true`。
2. 可用时直接 `onboard <alias>` 重跑；playbook 是幂等的，已完成的任务会跳过。
3. 如果只记得失败来自 first-time 流程，也可以跑 `onboard <alias> --first-time`；CLI 会先探测 managed channel，成功时自动进入 managed repair。
4. 还不行就看 `runtime/logs/vps_runner/<latest>/stdout` 定位具体 failed task。

---

## 6. 速查表

```bash
# 看清单
python -m plugins.vps_runner.cli list --env dev

# 健康检查（全部 / 单台）
python -m plugins.vps_runner.cli audit --env dev
python -m plugins.vps_runner.cli audit --env dev --limit hy-hk-u24

# 首次接入（wizard 唯一入口；密钥或密码都支持）
python -m plugins.vps_runner.cli add-host --env dev

# 重新 onboard（idempotent refresh，纯密钥）
python -m plugins.vps_runner.cli onboard <alias> --env dev
# 等价: make vps-reonboard ALIAS=<alias>

# wizard 首次失败后的 retry（先探测 managed；必要时自动读 bootstrap_key 注入临时密钥）
python -m plugins.vps_runner.cli onboard <alias> --env dev --first-time

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
*Last updated: 2026-05-23 (VPS Runner Round 12b)*
