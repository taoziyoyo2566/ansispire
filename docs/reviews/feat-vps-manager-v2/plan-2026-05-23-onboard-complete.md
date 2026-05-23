---
# Plan - Round 12b: onboard first-time 状态机 + fail2ban 闭环强化

> Supersedes: [`plan-2026-05-22c-onboard-fix.md`](./plan-2026-05-22c-onboard-fix.md)
> Branch: `feat/vps-manager-v2`
> Date: 2026-05-23
> Level: **L2** (连接状态机调整 + CLI 恢复语义 + onboard/modify 双路径服务闭环)
> Trigger: R11 wizard smoke 暴露 onboard 连接切换 false-negative 与 fail2ban failed 状态；R12c plan review 发现 gather_facts 时序、fail2ban 条件变量、modify 路径覆盖不足。

---

## §0 目标

R12b 的目标不是只修最后一个 `wait_for_connection`，而是把 first-time onboarding 做成可解释、可重跑、可恢复的完整闭环：

1. 新机器首次接入时，Ansible 从一开始就走 bootstrap 通道。
2. managed 用户、managed 端口、标准 automation key 可用后，playbook 明确切到 managed 通道。
3. 最终锁定 sshd/UFW 之前必须证明 managed login + sudo 可用。
4. 如果上一次 run 已经完成锁定但后续 task 失败，下一次修复应走 managed repair，不再误用已经关闭的 bootstrap 端口。
5. fail2ban 的配置、restart、active verify 在 onboard 和 modify 两条路径一致。

---

## §1 R12c 审核后的关键修正

| R12c 方向 | 结论 | R12b 修正 |
|---|---|---|
| 用 `vps_first_time_*` marker 代替 `ansible_user/ansible_port` extra-vars | 正确 | 保留 |
| 在 `pre_tasks` 用 `set_fact` 切到 bootstrap | 不完整 | 当前 `gather_facts: true` 会先连接；改为 `gather_facts: false`，bootstrap `set_fact` 后显式 `setup` |
| line 495/571 的 task vars 改 set_fact | 正确 | 加 `become: false` + `meta: reset_connection`，形成唯一 managed switch task |
| fail2ban wait active | 正确但条件变量错 | 条件统一用 `vps_fail2ban.enabled` / `vps_fail2ban_changes.enabled` |
| 只改 onboard.yml | 不完整 | 同步覆盖 `modify.yml`，否则 toggle-on 后仍可留下 failed service |
| `bootstrap_key` 改名 `bootstrap_key_path` | 没必要 | R12b 不做字段迁移，继续使用既有 `vps_runner.bootstrap_key`，减少测试和文档 churn |
| jpntt 重跑 `--first-time` | 错误 | jpntt 已关 bootstrap 22，应走 managed repair；新机器 smoke 才跑 first-time |

---

## §2 范围

### In scope

- `plugins/vps_runner/playbooks/onboard.yml`
  - first-time 连接状态机
  - 显式 fact gathering
  - managed switch + final validation
  - fail2ban start/restart/active/jail verify
- `plugins/vps_runner/playbooks/modify.yml`
  - fail2ban toggle-on 与 onboard 使用同一套 backend/restart/verify 语义
- `plugins/vps_runner/playbooks/templates/fail2ban_sshd.local.j2`
  - systemd backend 默认配置
  - managed port 保持现有语义
- `plugins/vps_runner/cli.py`
  - first-time extra-vars marker 化
  - wizard password/key 分支使用同一套 marker
  - `--first-time` recovery preflight，managed 已可达时自动走 managed repair
- `plugins/vps_runner/tests/test_vps_runner.py`
  - CLI marker 断言
  - bootstrap key retry
  - managed recovery preflight
  - playbook/fail2ban 结构回归
- docs/changelog
  - 更新操作说明和 R12b changelog

### Out of scope

- wizard 输入从「粘贴私钥」改为「粘贴公钥 + 本地匹配私钥」。这是 R13 候选，不混入 R12b。
- 多机并发 onboard。
- Docker 或其他新 feature。
- inventory schema 大迁移。
- 改 ansible-runner 密码注入机制。R11 的 `passwords={regex: value}` 继续保留。

### NFR 优先级

no-lockout safety > correctness > idempotence > recovery UX > maintainability > backward compatibility

---

## §3 连接状态机设计

### §3.1 数据边界

host_vars 的 top-level `ansible_host/ansible_port/ansible_user` 永远表示 **managed channel**。

first-time bootstrap channel 只来自 run-time marker：

```yaml
vps_first_time: true
vps_first_time_user: debian
vps_first_time_port: 22
vps_first_time_key: /path/to/temp.key   # 仅 key branch 或 retry key branch 有
```

这些 marker 只进 `extravars`，不写入 host_vars。host_vars 中继续只保存：

```yaml
vps_runner:
  bootstrap_user: debian
  bootstrap_port: 22
  bootstrap_key: /path/to/temp.key      # 仅失败后保留，成功后置 null
```

### §3.2 onboard.yml play 入口

当前 `gather_facts: true` 必须改成：

```yaml
- name: Onboard VPS into Ansispire management (vps_runner)
  hosts: vps_targets
  become: true
  gather_facts: false
```

然后 pre_tasks 第一段做连接选择：

```yaml
pre_tasks:
  - name: First-time bootstrap - select password/bootstrap channel
    ansible.builtin.set_fact:
      ansible_user: "{{ vps_first_time_user }}"
      ansible_port: "{{ vps_first_time_port | int }}"
    become: false
    when:
      - vps_first_time | default(false) | bool
      - vps_first_time_key is not defined

  - name: First-time bootstrap - select key/bootstrap channel
    ansible.builtin.set_fact:
      ansible_user: "{{ vps_first_time_user }}"
      ansible_port: "{{ vps_first_time_port | int }}"
      ansible_ssh_private_key_file: "{{ vps_first_time_key }}"
    become: false
    when:
      - vps_first_time | default(false) | bool
      - vps_first_time_key is defined

  - name: Reset connection after bootstrap channel selection
    ansible.builtin.meta: reset_connection
    when: vps_first_time | default(false) | bool

  - name: Gather minimal facts after connection selection
    ansible.builtin.setup:
      gather_subset:
        - min
    check_mode: false
```

注意：password branch 不尝试清空 inventory 里的 `ansible_ssh_private_key_file`。现有实现也会带着 group_vars 的 standard key 再使用 ask-pass；R12b 不在这里引入新 SSH option 语义。

### §3.3 managed switch

只保留一个明确的 managed switch block，放在 transitional sshd reload 与 final lockdown 之间：

```yaml
- name: Wait for managed SSH port to answer
  ansible.builtin.wait_for:
    host: "{{ ansible_host }}"
    port: "{{ vps_ssh.managed_port | int }}"
    timeout: 30
  delegate_to: localhost
  become: false
  when: not ansible_check_mode

- name: Switch Ansible connection to managed channel
  ansible.builtin.set_fact:
    ansible_user: "{{ vps_managed.user }}"
    ansible_port: "{{ vps_ssh.managed_port | int }}"
    ansible_ssh_private_key_file: "{{ vps_managed.ansible_key.private_key }}"
  become: false
  when: not ansible_check_mode

- name: Reset connection after managed channel switch
  ansible.builtin.meta: reset_connection
  when: not ansible_check_mode

- name: Wait for managed-user connection
  ansible.builtin.wait_for_connection:
    timeout: 30
  when: not ansible_check_mode

- name: Validate managed user sudo
  ansible.builtin.command: id -u
  become: true
  changed_when: false
  when: not ansible_check_mode
```

final lockdown 后只 reset + wait，不再重复 task-level vars：

```yaml
- name: Reset Ansible connection after final lockdown
  ansible.builtin.meta: reset_connection
  when: not ansible_check_mode

- name: Wait for managed-user connection after lockdown
  ansible.builtin.wait_for_connection:
    timeout: 30
  when: not ansible_check_mode
```

### §3.4 lockout safety invariant

R12b 必须保持这条顺序：

1. 写入 managed user + authorized_keys + sudoers。
2. transitional sshd 同时允许 bootstrap 和 managed。
3. local `wait_for` 确认 managed port 已监听。
4. Ansible 自身切 managed channel。
5. managed login + sudo validation 成功。
6. 写入 final locked-down sshd config。
7. reload sshd。
8. 关闭 bootstrap UFW allow。
9. final managed reconnect validation。

如果第 5 步之前失败，bootstrap port 仍应保持开放。只有第 5 步成功后才允许进入 final lockdown。

---

## §4 CLI 行为设计

### §4.1 first-time extra-vars marker

`_cmd_onboard --first-time`、wizard password branch、wizard key branch 统一使用：

```python
extravars = {
    "vps_first_time": True,
    "vps_first_time_user": bootstrap_user,
    "vps_first_time_port": int(bootstrap_port),
}
if bootstrap_key:
    extravars["vps_first_time_key"] = str(bootstrap_key)
```

不再把 `ansible_user`、`ansible_port`、`ansible_ssh_private_key_file` 作为 first-time extra-vars 注入。

### §4.2 managed recovery preflight

`--first-time` 可能被用于两种不同状态：

1. 真 fresh VPS：managed user/port 还不可达，应走 bootstrap。
2. partial success：managed user/port 已可达，bootstrap port 可能已关闭，应走 managed repair。

因此 `_cmd_onboard` 在 `args.first_time` 时先做一个短 managed probe：

```python
ok, reason = core.ssh_probe(
    data["ansible_host"],
    int(data["ansible_port"]),
    data["ansible_user"],
    core.DEFAULT_AUTOMATION_PRIVATE_KEY,
    timeout=5,
)
if ok:
    print("==> managed channel already works; running managed repair mode")
    extravars = {}
else:
    extravars = first_time_markers(...)
```

这样 jpntt 这种「最终 SSH/UFW 已锁定，但 playbook 后置 task 失败」的状态不会再错误尝试 `debian@22`。

规则：

- managed probe 成功：忽略 first-time markers，跑普通 onboard。
- managed probe 失败：按 first-time marker 跑 bootstrap。
- onboard 成功后：如果 `vps_runner.bootstrap_key` 存在，置为 null；临时 key 文件的清理仍由 key-branch 成功验证负责。

### §4.3 wizard branches

password branch 继续传：

```python
cmdline="--ask-pass" 或 "--ask-pass --ask-become-pass"
passwords={...}
extravars=vps_first_time markers
```

key branch 继续：

1. 写 temp key 到 `runtime/keys/vps_runner/<alias>.key`。
2. 用 `vps_first_time_key` marker 跑 onboard。
3. 成功后跑 `verify_standard_key()`。
4. verify 成功才清理 temp key + 清空 host_vars `bootstrap_key`。
5. onboard 或 verify 失败时保留 temp key + 写 `bootstrap_key` retry hint。

### §4.4 操作提示修正

失败提示区分两类：

- 如果 managed probe 成功但 onboard 失败：提示重跑普通 `onboard <alias> --env <env>`。
- 如果 managed probe 失败且 first-time 路径失败：提示重跑 `onboard <alias> --env <env> --first-time`。

---

## §5 fail2ban 设计

### §5.1 template

`fail2ban_sshd.local.j2` 改为：

```ini
# Managed by Ansispire vps_runner
[sshd]
enabled = true
port = {{ (vps_ssh.managed_port if vps_ssh is defined else 'ssh') }}
backend = {{ vps_fail2ban.get('backend', 'systemd' if ansible_facts.service_mgr == 'systemd' else 'auto') }}
bantime = {{ vps_fail2ban.get('sshd', {}).get('bantime', 3600) }}
findtime = {{ vps_fail2ban.get('sshd', {}).get('findtime', 600) }}
maxretry = {{ vps_fail2ban.get('sshd', {}).get('maxretry', 5) }}
```

Debian 12+ 默认缺 `/var/log/auth.log` 时，`backend = systemd` 避免 sshd jail 因找不到 auth log 文件而无法启动。

### §5.2 packages

Debian + systemd + fail2ban enabled 时确保安装：

- `fail2ban`
- `python3-systemd`

`python3-systemd` 是 systemd backend 的运行依赖，避免只写 backend 但 backend import 不可用。

### §5.3 onboard/modify 一致语义

onboard 和 modify 的 fail2ban enable path 都必须包含：

1. install packages
2. render jail template
3. notify restart fail2ban
4. flush handlers 或显式 restart
5. ensure enabled + started
6. wait until `ActiveState == active`
7. `fail2ban-client status sshd` 验证 sshd jail 实际 loaded

条件变量：

- onboard: `vps_fail2ban.enabled | default(false) | bool`
- modify: `vps_fail2ban_changes.enabled | default(false) | bool`

不得再使用不存在的 `vps_profile.fail2ban`。

### §5.4 handler

两个 playbook 都加：

```yaml
- name: Restart fail2ban
  ansible.builtin.systemd:
    name: fail2ban
    state: restarted
    enabled: true
  when: not ansible_check_mode
```

如果 template changed，必须 restart；仅 `state: started` 不足以应用新 jail 配置。

---

## §6 测试计划

### Unit tests

更新或新增：

1. `test_cli_onboard_first_time_uses_vps_marker_vars`
   - 断言没有 `ansible_user/ansible_port` extra-vars。
   - 断言存在 `vps_first_time_user/port`。
2. `test_onboard_first_time_auto_injects_bootstrap_key_as_marker`
   - `vps_runner.bootstrap_key` 转成 `vps_first_time_key`。
3. `test_cli_onboard_first_time_managed_probe_success_runs_repair_mode`
   - mock `core.ssh_probe` 返回 ok。
   - 断言 `extravars == {}`，不使用 bootstrap marker。
4. wizard password branch test
   - 断言 `passwords` dict 保留。
   - 断言 extra-vars marker 化。
5. wizard key branch test
   - 断言 temp key path 进入 `vps_first_time_key`。
   - 失败仍 persist `bootstrap_key`。
6. playbook structure regression
   - `onboard.yml` 顶层 `gather_facts` 为 false。
   - `setup` task 位于 `service_facts` 之前。
   - managed switch 使用 `set_fact`，后续 wait task 不含 task-level connection vars。
7. fail2ban template regression
   - template 包含 `backend =`。
   - onboard/modify 都有 restart/active/status verify。

### Syntax / integration

执行：

```bash
make test-vps-runner
make vps-runner-syntax
```

如改动 ansible-runner 调用路径，再执行：

```bash
make test-vps-runner-integration
```

### Smoke

#### jpntt partial-success recovery

前提：jpntt 已经是 managed reachable，bootstrap 22 可能已关闭。

1. `python -m plugins.vps_runner.cli onboard jpntt --env dev`
2. 验证 recap failed=0。
3. 验证：
   - `ssh -i ~/.ssh/ansispire_ed25519 ansible@116.80.96.126 -p 1156 true`
   - `systemctl is-active fail2ban` 为 `active`
   - `fail2ban-client status sshd` 成功
   - 22 端口保持不可用或 UFW 不再 allow

不再要求 jpntt 跑 `--first-time`。

#### fresh VPS first-time key branch

1. wizard 选 key branch。
2. onboarding 成功。
3. temp key 清理。
4. `bootstrap_key` 置 null。
5. managed login + sudo + fail2ban active 全通过。

#### fresh VPS first-time password branch

有新机可用时执行；如果没有新机，本轮至少保证 unit + syntax + key branch smoke。

---

## §7 实施拆分

| Sub | 文件 | 内容 |
|---|---|---|
| T1 | `plugins/vps_runner/playbooks/onboard.yml` | `gather_facts: false`、bootstrap marker set_fact、explicit setup、managed switch block |
| T2 | `plugins/vps_runner/cli.py` | first-time marker helper、managed recovery preflight、wizard branches 统一 marker |
| T3 | `plugins/vps_runner/playbooks/templates/fail2ban_sshd.local.j2` | 加 backend systemd/auto |
| T4 | `plugins/vps_runner/playbooks/onboard.yml`, `plugins/vps_runner/playbooks/modify.yml` | fail2ban package/restart/active/status verify 双路径一致 |
| T5 | `plugins/vps_runner/tests/test_vps_runner.py` | unit + structure regression |
| T6 | docs/changelog | 操作说明、R12b changelog、旧 plan superseded 标注 |
| T7 | smoke | jpntt managed repair + fresh VPS first-time |

建议顺序：T1 -> T2 -> T5 partial -> T3/T4 -> T5 full -> T6 -> T7。

---

## §8 风险与回滚

### 风险 R1: set_fact 是否足够早

缓解：`gather_facts: false`，first pre_task 只做 controller-side `set_fact`，然后显式 `setup`。如果实际运行显示 play-level `become` 影响 set_fact，给 bootstrap set_fact tasks 加 `become: false`。

### 风险 R2: password branch 带着 standard key

现状也是如此。R12b 不额外改变 SSH key selection，只保证 user/port 不再被 extra-vars 锁死。若 smoke 显示 password auth 被 key 干扰，再单独加 SSH option 覆盖，不在本轮预设。

### 风险 R3: systemd backend 依赖缺失

缓解：Debian + systemd 下安装 `python3-systemd`，并用 `fail2ban-client status sshd` 做真实 jail verify。

### 风险 R4: managed recovery preflight 增加 5 秒延迟

仅 `--first-time` 才执行。换来 partial success 场景不会误连已关闭的 bootstrap port，值得。

---

## §9 Definition of Done

- `--first-time` 不再向 ansible-runner extra-vars 注入 `ansible_user/ansible_port/ansible_ssh_private_key_file`。
- `onboard.yml` 在 first-time 下能先选 bootstrap，再 gather facts。
- managed switch 后的两个 validation task 实际使用 managed user/port/key。
- final lockdown 后 reconnect 不再尝试 bootstrap port。
- fail2ban 在 onboard 和 modify toggle-on 后都被 restart、active verify，并且 sshd jail loaded。
- jpntt partial-success 状态可用普通 onboard 修复。
- 新 VPS key branch first-time smoke 通过。
- `make test-vps-runner` 和 `make vps-runner-syntax` 通过。

---

*Plan written 2026-05-23. Ready for implementation after sign-off.*
