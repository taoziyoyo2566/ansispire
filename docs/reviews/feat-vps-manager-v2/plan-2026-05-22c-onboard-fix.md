---
# Plan — Round 12: onboard.yml 连接切换 + fail2ban 启动稳定性

> Branch: `feat/vps-manager-v2`
> Topic: 修 R11 wizard smoke 暴露的 2 个 onboard.yml 问题
> Date: 2026-05-22
> Level: **L1.5** (engineering fix on top of existing onboard.yml architecture)
> Sibling plans: [`plan-2026-05-22.md`](./plan-2026-05-22.md) (R7), [`plan-2026-05-22b-wizard.md`](./plan-2026-05-22b-wizard.md) (R11)

---

## §0 出发点 — R11 smoke 暴露的两个独立问题

2026-05-22 18:59 用 R11 wizard 对 jpntt (116.80.96.126, bootstrap=`debian@22`) 跑完整密钥分支 onboard，wizard 字段收集 + temp key + extravars 注入 + 80% 的 onboard tasks 全跑通。**实机最终状态正确**（独立 SSH 验证：ansible@1156 + NOPASSWD sudo + sshd 锁定 + UFW deny-by-default + 1156 allow），但 onboard.yml 在最后两步上出问题：

### §0.1 onboard.yml line 571 false-negative

```
TASK [Wait for managed-user connection after lockdown]
[ERROR]: ssh: connect to host 116.80.96.126 port 22: Connection timed out
```

任务 `vars:` 块明明声明了 `ansible_port: 1156 / ansible_user: ansible / ansible_ssh_private_key_file: ansispire_ed25519`，ansible 仍然尝试 `port 22` 导致 timeout。

**根因**：Ansible 变量优先级里 `extra-vars` 凌驾 task-level `vars:`。R11 `_wizard_onboard_key_branch` 传 `extravars = {ansible_user: debian, ansible_port: 22, ansible_ssh_private_key_file: <temp>}` 后，整个 play 周期这三个 key 被锁死，task `vars:` 无法切回 managed 通道。

**为什么没在 R3-R10 暴露**：之前的 onboard 测试不是用 ansible-runner 真跑首次密码登录（`--ask-pass` 经 ansible-runner 死锁，从来跑不通完整 play）。R11 first-time 真跑到 lockdown 才暴露。另外 line 495 的「Wait for connection as managed user on new port」是个同样有 bug 的 false-positive：bootstrap port 此时还开着，extravars 把它指向 `debian@22`，连得上，但任务名声称的「on new port」实际验的还是老端口。

### §0.2 fail2ban service `failed`

onboard.yml 三个 fail2ban task (`Install`, `Configure sshd jail`, `Ensure enabled`) 都 changed/ok，但实机 `systemctl is-active fail2ban` = **failed**。

**根因待诊断**（智能猜测，按可能性排序）：

1. **Debian 12+ 默认无 `/var/log/auth.log`** — sshd 日志走 systemd journal；fail2ban sshd jail 默认 `logpath=%(sshd_log)s` 展成文件路径 → fail2ban 启动找不到文件 → 退出
2. **jail port hardcode 22** — 不影响 service active 状态，仅影响 ban action；可能性低
3. **systemd dependency 顺序** — 几乎不可能

操作员需提供：

```bash
ssh -i ~/.ssh/ansispire_ed25519 ansible@116.80.96.126 -p 1156 \
    'sudo systemctl status fail2ban --no-pager -l | tail -25; \
     sudo journalctl -u fail2ban --no-pager -n 30; \
     sudo cat /etc/fail2ban/jail.d/*.conf; \
     ls -la /var/log/auth.log 2>&1'
```

诊断输出决定 §3 修复路径。

---

## §1 范围

### In scope

- 修 onboard.yml 的 extravars-vs-task-vars 优先级问题（架构性，影响所有 first-time 模式）
- 修 fail2ban startup 不稳定（具体改法待 §3 诊断决定）
- 同步改 R11 `_wizard_onboard_key_branch` / `_cmd_onboard` 的 extravars 命名空间
- 修 onboard.yml line 495 那个 false-positive verify task（既然 571 改了，495 同步改）

### Out of scope

- 把 R11 密钥分支从「粘贴私钥」改成「粘贴公钥」这条线 —— 见 §4 deferred
- 多机并发 onboard（IVG-VPS-BATCH-PARALLEL 专项）
- onboard.yml 任何 feature 添加（如 docker 安装）

### NFR 优先级

correctness > backwards-compatibility > UX > maintainability

backwards-compatibility 第二是因为 onboard.yml 既有用户少（只我一个 + 现役 fleet 4 台已 onboard），安全破坏式重构。

---

## §2 修复 §0.1：extravars → set_fact 重构

**核心思路**：CLI 不再用 `ansible_user/ansible_port/ansible_ssh_private_key_file` 这种 ansible 保留变量名作为 extravars。改用项目命名空间 marker，让 playbook `pre_tasks` 用 `set_fact` 把 marker 转成连接变量。`set_fact` 创建的 host facts 优先级**低于** extravars，但比 inventory/group_vars 高，且可以在 play 中途被新的 `set_fact` 覆盖。

### §2.1 CLI 端改动 (cli.py)

R11 当前的 `_wizard_onboard_key_branch`：

```python
extravars = {
    "ansible_user": bootstrap_user,
    "ansible_port": int(bootstrap_port),
    "ansible_ssh_private_key_file": str(temp_key_path),
}
```

→ R12 改为：

```python
extravars = {
    "vps_first_time": True,
    "vps_first_time_user": bootstrap_user,
    "vps_first_time_port": int(bootstrap_port),
    "vps_first_time_key": str(temp_key_path),  # absent for password branch
}
```

同样 `_cmd_onboard` 的 `--first-time` 处理改用同套 marker（替代 `extravars["ansible_user"]=...`）。`bootstrap_key` host_vars 字段的 retry hint 也改成填到 `vps_first_time_key`。

### §2.2 onboard.yml 端改动

加 `pre_tasks` 段：

```yaml
pre_tasks:
  - name: First-time bootstrap — switch connection to bootstrap channel
    ansible.builtin.set_fact:
      ansible_user: "{{ vps_first_time_user }}"
      ansible_port: "{{ vps_first_time_port | int }}"
      ansible_ssh_private_key_file: "{{ vps_first_time_key | default(omit) }}"
    when: vps_first_time | default(false) | bool
```

`vars:` 块（line 495/498 + line 571/574）的 connection 三件套改成 `set_fact`：

```yaml
- name: Switch to managed connection (port 1156 + ansible user + standard key)
  ansible.builtin.set_fact:
    ansible_user: "{{ vps_managed.user }}"
    ansible_port: "{{ vps_ssh.managed_port | int }}"
    ansible_ssh_private_key_file: "{{ vps_managed.ansible_key.private_key }}"

- name: Wait for managed-user connection after lockdown
  ansible.builtin.wait_for_connection:
    timeout: 30
  when: not ansible_check_mode
```

这样后面所有 task 用的连接参数都来自 host facts，extravars 不再阻塞。

### §2.3 影响 onboard.yml line 495 (transitional 阶段验证) 同步修

老结构是 task vars 覆盖（被 extravars 压死的 false-positive）；新结构是 `set_fact` 切换 + `wait_for_connection`。两个 task 用同一个 `set_fact: 切到 managed` —— 实际上只需要一次切换（第一次切完就稳定，line 571 不必再切）。重构后整个 lockdown 区段一目了然：

```yaml
- name: <transitional sshd reload>
- name: Wait for managed SSH port to answer (delegate localhost)
- name: Switch ansible facts to managed connection      # NEW: set_fact
- name: Reset connection                                  # meta: reset_connection
- name: Wait for managed-user connection                  # validate
- name: Validate managed sudo
- name: <install final lockdown drop-in>
- name: <Close bootstrap port>
- name: Reset connection                                  # second reset
- name: Wait for managed-user connection after lockdown   # final validate
```

---

## §3 修复 §0.2：fail2ban startup

**修复细节待 §0.2 诊断输出确认**。三个可能路径（按诊断结果分支）：

| 诊断 | 修复 |
|---|---|
| journalctl 显示 `Failed to open file /var/log/auth.log` | jail.d/ansispire.conf 加 `backend = systemd` |
| port 22 hardcoded | 改 jail 用 `port = ssh` 或 `port = {{ vps_ssh.managed_port }}` |
| python error / version mismatch | apt full-upgrade fail2ban 或固定版本 |

**额外加固**（无论根因如何都要做）：onboard.yml `Ensure fail2ban is enabled` task 之后再加一步等 service active：

```yaml
- name: Wait for fail2ban to reach active state
  ansible.builtin.wait_for:
    path: /var/run/fail2ban/fail2ban.sock
    timeout: 30
  when: vps_profile.fail2ban | default(true) | bool
```

或：

```yaml
- name: Verify fail2ban service active
  ansible.builtin.systemd:
    name: fail2ban
    state: started
  register: f2b_status
  until: f2b_status.status.ActiveState == 'active'
  retries: 6
  delay: 5
  when: vps_profile.fail2ban | default(true) | bool
```

后者更地道（Ansible-native 等待 service 进入稳定态）。

---

## §4 deferred 设计决策 — wizard 密钥分支输入形式

R11 smoke 之前我曾提议把「粘贴私钥」改为「粘贴公钥 + ~/.ssh/ 匹配私钥」，理由是私钥不该离开 `~/.ssh/`。讨论被 smoke 截断；用户用粘贴私钥模式完成 smoke 没失败。

**这条问题保留为 R13 候选**，不进 R12 范围。R12 优先级是修 onboard.yml 让 smoke 真能跑通，不是再翻 wizard 设计。R12 落地后真实场景跑顺了再回头评估「私钥粘贴」vs「公钥粘贴」哪个 UX 更合理。

如果 R12 期间还想顺手清理这条，再开 plan-2026-05-22d。

---

## §5 实施拆分

| Sub | 主题 | 文件 | 约时 |
|---|---|---|---|
| T1 | onboard.yml extravars→set_fact 重构 + line 495/571 切到 set_fact 模式 | `playbooks/onboard.yml` | 60 min |
| T2 | CLI 端 extravars 命名空间迁移 (vps_first_time_*) | `cli.py`, `vps_runner.py` (host_vars `bootstrap_key` 字段改名 → `bootstrap_key_path`，向后兼容读取) | 30 min |
| T3 | fail2ban startup hardening (wait-active 模式) + 根因修复（依赖 §3 诊断） | `playbooks/onboard.yml` | 30-60 min |
| T4 | 测试 + 文档 + R12 changelog | tests + ops doc + changelog | 30 min |

合计 ~2.5-3 h。

---

## §6 测试矩阵

### Unit

- 现有 R11 wizard 测试更新：extravars 断言改名（`ansible_user` → `vps_first_time_user` 等），新增 happy path 对一致性。

### Integration

- 现有 TEST-NET-1 集成测试不会因 onboard.yml 改动失败（target 永远 unreachable，play 在 Gathering Facts 就 fail），但要 verify play 加载时 pre_tasks set_fact 不报语法错。

### Smoke

- **jpntt 重跑** —— 这次 R12 实施完后，wizard 选项 3 (验证现有) 应该通过，因为实机 80% onboard 已经成功，只 fail2ban 一项。R12 fail2ban hardening 修完后第二次 onboard --first-time retry 应该 PLAY RECAP failed=0。
- **新机 onboard** —— 给一台新 VPS（你提供凭据），走完整 wizard 密钥分支，验 PLAY RECAP 干净。

---

## §7 W-R20 destructive sink 评估

| 操作 | destructive sink? |
|---|---|
| 重写 onboard.yml pre_tasks + 连接切换 | 否（playbook 重构，影响远程 VPS 是 onboard 一贯就有的，本 plan 不引入新的远程动作） |
| 改 CLI extravars 命名 | 否（本地代码） |
| `Wait for fail2ban active` task 加在远程 | 边界 case：仅等待 service active，不删数据；不算 destructive |

R12 与 R8/R9/R10/R11 同级，不触发额外 `/ultrareview`；merge-to-dev 时整体外审。

---

## §8 Next Steps

1. **诊断 fail2ban** — 用户提供 §0.2 诊断输出 → 确定 §3 具体修复路径
2. **plan sign-off** —— 用户确认本 plan 范围
3. **实施 T1→T2→T3→T4** —— 每个 3-gate + commit
4. R12 完成后**第二次 jpntt smoke**（`onboard --first-time` retry 利用 host_vars 里的 bootstrap key hint）
5. smoke 通过后整 branch (R7+R8+R9+R10+R11+R12) 一起开 PR → dev，外审

---

*Plan written 2026-05-22 19:30. Pending §0.2 fail2ban 诊断 + plan sign-off。*
