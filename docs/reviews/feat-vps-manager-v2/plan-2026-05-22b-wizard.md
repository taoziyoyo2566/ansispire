---
# Plan — Round 11: wizard 重设计（首次接入闭环）

> Branch: `feat/vps-manager-v2`
> Topic: VPS Manager v2 wizard for first-time onboarding
> Date: 2026-05-22
> Level: **L1.5 → L2** (UX state model + ansible-runner password injection mechanism + 临时密钥生命周期管理)
> Sibling plans: [`plan-2026-05-22.md`](./plan-2026-05-22.md) (R7 add-host triple-entry + post-onboard SSH alias write)

---

## §0 失败反思（pre-design retrospective）

R7 wizard 在真实使用第一次就暴露了三个问题：

1. **password flow 经 ansible-runner 必死锁**（cli.py 把 `--ask-pass --ask-become-pass` append 到 cmdline，但 `ansible_runner.run()` 默认不给子进程分配 PTY，密码 prompt 既看不到也读不到 stdin）。结论：自从 R4-b 切到 ansible-runner，**密码登录路径从未被真实验证过**。
2. **wizard 默认 Y 强推密码 flow + 字段不全**（不问 bootstrap user/port，硬当 root@22；想用密钥登录的操作员被默认值拖进错误分支）。
3. **失败信息不可执行**（`Permission denied (publickey)` 之后没有「下一步该敲什么」提示）。

设计层面我自己也犯了两个错（W-R13/R14 都警告过）：

- **强行对齐结构**：原设计把「密码 = 字符串 content」和「密钥 = 私钥 content」对齐到同一个 prompt 形态，忽略了密钥在 SSH 客户端层有更标准的处理路径，制造了不必要的复杂度。
- **过度征询**：把 3 个落地策略当选项问用户（实际只有「临时 key + 后清理」一种合理方案），消耗用户耐心。

本 plan 在 §2 起按照「**field 序列由用户拍板 + 密钥临时使用后清理 + 同名 alias 4 选项菜单**」的具体规约展开，不再发散。

### §0.1 W-R18 框架最佳实践 pre-check

| 子问题 | 检查源 | 结论 |
|---|---|---|
| 非交互注入 SSH/sudo 密码到 ansible-playbook | [ansible-runner docs: passwords](https://ansible-runner.readthedocs.io/en/stable/intro.html#ansible-runner-passwords) | `passwords={regex: value}` 字典是官方推荐，**不**进 artifact envvars，规避 `--ask-pass` 的 TTY 依赖 |
| 私钥临时使用 + 后清理 | inventory + `extravars` 注入 `ansible_ssh_private_key_file=<temp_path>` | extravars 是 per-run override，比改 inventory 干净；artifact 会记录该字段，但只是路径（不是私钥内容） |
| 多行 PEM 输入终止识别 | PEM RFC 7468 + OpenSSH key format | `-----BEGIN ... PRIVATE KEY-----` / `-----END ... PRIVATE KEY-----` 是标准 marker，自动检测 = 标准做法 |
| post-onboard 用标准密钥再 ping 一次验证 | ansible-runner `module='ping'` ad-hoc 调用 | 标准能力，比再起一遍 onboard 轻 |

direction: 全部匹配框架原生模式，无 anti-pattern。

---

## §1 范围

### In scope

- 重写 `plugins/vps_runner/vps_runner.py::prompt_new_host()` + `cli.py::_cmd_add_host()` 的 wizard 流程
- 新增私钥临时落盘 + 清理机制
- 修复 `--ask-pass`/`--ask-become-pass` 死锁（passwords dict）
- 同名 alias 检测 + 4 选项菜单
- onboard.yml **不动**（已经做了装两把公钥 + 关密码登录的工作）
- 弃用 `make vps-onboard` Make wrapper
- 弃用 `onboard` 子命令的 `--ask-pass`/`--ask-become-pass` flag（首次接入唯一入口 = wizard）

### Out of scope（明确不做）

- 多机批量 onboard（IVG-VPS-BATCH-PARALLEL 专项）
- ssh-copy-id 在 wizard 里内嵌（要读密码 + 写 known_hosts，复杂度爆涨）
- audit / modify / remove 加 wizard（先聚焦 add-host + onboard 闭环）
- `~/.ssh/config` 的 `Include config.d/*` 自动加（R7 已经是「提示一次」语义）

### NFR 优先级

correctness > UX > maintainability > backwards-compatibility

向后兼容性故意排在最后：R7 wizard 上线 < 1 天，无真实用户依赖；R11 是修不通的实现，破坏式重写比兼容性补丁更便宜。

---

## §2 重设计后的 wizard 字段序列与交互

### §2.1 启动预检（ENTRY GATE）

进入 wizard 第一步检查操作员本机的 SSH 链路前提：

```python
def _wizard_entry_check() -> bool:
    """Verify operator's local SSH setup is ready for the two-key model."""
    missing: list[str] = []
    for k in (DEFAULT_AUTOMATION_PRIVATE_KEY,  # ~/.ssh/ansispire_ed25519
              DEFAULT_AUTOMATION_PUBLIC_KEY,   # ~/.ssh/ansispire_ed25519.pub
              DEFAULT_PERSONAL_PUBLIC_KEY):    # ~/.ssh/id_ed25519.pub
        if not k.exists():
            missing.append(str(k))
    if missing:
        sys.stderr.write(
            "vps-runner wizard prerequisite missing:\n"
            + "".join(f"  - {p}\n" for p in missing)
            + "\nGenerate them once with:\n"
            "  ssh-keygen -t ed25519 -f ~/.ssh/ansispire_ed25519 -N ''\n"
            "  ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519       -N ''\n"
        )
        return False
    return True
```

预检失败 → rc=3 早退，不进入字段收集。

### §2.2 字段序列（用户拍板的顺序）

```
==> vps-runner wizard — 新增一个 managed VPS（环境: dev）

Alias [必填]:                        jpntt
IP / hostname [必填]:                116.80.96.126

[如果 alias 已存在 → 进入 §4 同名 alias 菜单，不走下面流程]

User                  [默认 root]:   ↩
认证方式: (p) 密码 / (k) 密钥 [默认 p]: k
                                     ↑ 选 k 直接跳到 Port 提示
                                     ↑ 选 p 才走「输入 SSH password」分支

[p 分支]
SSH password for root@116.80.96.126: ********
[非 root 时多问一次]
Sudo password (留空=同 SSH):         ↩

[k 分支]
Private key for root@116.80.96.126 (粘贴 PEM 全文，以 -----END … PRIVATE KEY----- 自动结束):
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZ...
... (operator pastes lines)
-----END OPENSSH PRIVATE KEY-----
[wizard 自动识别 -----END 行后停止收集]
[非 root 时单独问 sudo 密码：密钥能登 ≠ sudo 免密]
Sudo password (留空=尝试 NOPASSWD):  ↩

[共同后续]
Port (bootstrap) [默认 22]:          ↩
Managed user     [默认 ansible]:     ↩
Managed port     [默认 1156]:        ↩

==> 写入 inventory
==> created host_vars/jpntt.yml
==> added 'jpntt' to hosts.yml
==> SSH probe (仅密钥分支): ✓
==> running onboard jpntt --first-time (auth=key)
... (real ansible-runner output) ...
==> post-onboard verify (ping via ~/.ssh/ansispire_ed25519): ✓
==> cleanup runtime/keys/vps_runner/jpntt.key: ✓
==> wrote ~/.ssh/config.d/jpntt.conf
==> done. Try: ssh jpntt
```

### §2.3 校验与重提

每个字段独立 try/except，校验失败只重提该字段（不重启 wizard）：

| 字段 | 校验器（已有：R9）| 失败重提 |
|---|---|---|
| Alias | `_validate_alias` | ✓ |
| IP / hostname | `_validate_hostname` | ✓ |
| Bootstrap user / Managed user | `_validate_ssh_user` | ✓ |
| Bootstrap port | int + (1..65535) | ✓ |
| Managed port | int + (1024..65535) + ≠22 | ✓ |
| 认证方式 | `p` or `k`（默认 `p`） | ✓ |
| SSH password / Sudo password | 非空（密码可以任意字符；不做 charset） | ✓ |
| Private key | `-----BEGIN.*PRIVATE KEY-----` 头存在 + `-----END.*PRIVATE KEY-----` 尾闭合 | ✓ |

任何字段如果是 Ctrl-C / EOF：清理已写盘内容（如果有），rc=130 退出。

---

## §3 密钥临时生命周期

### §3.1 落盘

```python
_TEMP_KEY_DIR = PROJECT_ROOT / "runtime" / "keys" / "vps_runner"

def _write_temp_key(alias: str, private_key_text: str) -> Path:
    """Write pasted PEM to <project>/runtime/keys/vps_runner/<alias>.key (0600).

    Project-local (not ~/.ssh/) so operator's SSH ecosystem is untouched.
    Validator already ensured -----BEGIN/-----END markers; we normalize CRLF
    to LF and ensure trailing newline.
    """
    _TEMP_KEY_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    target = _TEMP_KEY_DIR / f"{alias}.key"
    _assert_path_in_dir(target, _TEMP_KEY_DIR)  # R9 belt-and-braces
    normalized = private_key_text.replace("\r\n", "\n")
    if not normalized.endswith("\n"):
        normalized += "\n"
    target.write_text(normalized, encoding="utf-8")
    target.chmod(0o600)
    return target
```

`.gitignore` 加：

```
runtime/keys/vps_runner/*.key
```

### §3.2 onboard 注入

```python
extravars = {"ansible_ssh_private_key_file": str(temp_key_path)}
# ... existing extravars from --first-time ...
summary = core.run_playbook(
    action="onboard",
    env=env,
    playbook="onboard.yml",
    limit=alias,
    extravars=extravars,
    # 密码分支才需要 passwords dict：
    passwords=passwords_dict if auth_method == "p" else None,
    ...
)
```

> `run_playbook()` 当前没接受 `passwords=` 参数。本轮要给它加一个可选 kwarg，原样转发到 `ansible_runner.run()`。

### §3.3 post-onboard 验证

onboard `summary.status == "successful"` 后做一次独立 ping：

```python
def _verify_standard_key(env: str, alias: str) -> bool:
    """After onboard, ansispire_ed25519 should now work against managed user.
    Run a 1-task ansible ping that explicitly uses the standard automation key.
    Returns True iff the host responds OK."""
    summary = run_playbook(
        action="verify",
        env=env,
        playbook="_verify_post_onboard.yml",  # tiny new playbook: ping only
        limit=alias,
        extravars={
            # explicit override even though it's the group default — defensive
            "ansible_ssh_private_key_file": str(DEFAULT_AUTOMATION_PRIVATE_KEY),
        },
        quiet=True,
    )
    return summary.status == "successful"
```

新增 `plugins/vps_runner/playbooks/_verify_post_onboard.yml`：

```yaml
---
- name: Post-onboard verification — standard automation key reachability
  hosts: all
  gather_facts: false
  tasks:
    - name: Ping via ansispire_ed25519
      ansible.builtin.ping:
```

### §3.4 清理

```python
def _cleanup_temp_key(alias: str) -> None:
    target = _TEMP_KEY_DIR / f"{alias}.key"
    if target.exists():
        # No content shred — Python `unlink` is enough; on shared hosts
        # the operator who controls the project tree is the only attacker
        # model. If they wanted shred-grade, ~/.ssh is the wrong tree anyway.
        target.unlink()
```

### §3.5 失败路径

| 阶段 | 行为 |
|---|---|
| §3.1 写盘失败 | 直接抛 `VpsRunnerError`，inventory 已写，提示「修复磁盘问题后重跑 wizard」 |
| §3.2 onboard 失败 | **不清理临时 key**；提示「inventory + temp key 已保留，修复后重跑 `onboard <alias> --env dev --first-time` 即可（CLI 会自动读 host_vars 里的 extravars hint）」 |
| §3.3 验证失败 | **不清理**；提示「onboard 装的 ansispire 公钥可能没生效，请人工检查 `ssh -i ~/.ssh/ansispire_ed25519 ansible@<IP>` 后决定是否手动 rm temp key」 |
| §3.4 rm 失败 | warn only（temp key 留下不阻塞流程；operator 自己处理） |

§3.2 提到的「CLI 自动读 host_vars extravars hint」需要新增 host_vars 字段：

```yaml
vps_runner:
  bootstrap_key: runtime/keys/vps_runner/jpntt.key  # 临时；onboard 成功后删 + 清此字段
```

`onboard` 子命令在 `--first-time` 模式启动时检查 `vps_runner.bootstrap_key`，存在则注入到 extravars。这样重试不需要操作员手敲 `--extra-vars`。

---

## §4 同名 alias 处理状态机（4 选项菜单）

进入点：在 §2.2 第二步 IP 后、第三步 User 前，如果 alias 已在 `hosts.yml` 或 `host_vars/<alias>.yml`：

```
==> 检测到 alias 'jpntt' 已存在：

  IP:          116.80.96.126
  Bootstrap:   root@22
  Managed:     ansible@1156
  Status:      pending   (last_run: 无)

请选择处理方式：
  1) 跳过并结束 (no-op)                          [默认]
  2) 使用新的 alias 继续                          → 回到 Alias 字段重提
  3) 验证现有配置
  4) 强制覆盖现有配置 (use when current is broken)
选择 [1]:
```

| 选项 | 行为 |
|---|---|
| 1 | 直接 rc=0 退出，不动任何状态 |
| 2 | 清掉已收集的 alias，goto Alias 重提；其他字段（如果已填）保留 |
| 3 | 进入 §4.1「验证现有配置」子流程 |
| 4 | 进入 §4.2「强制覆盖」子流程 |

### §4.1 验证子流程

```python
def _verify_existing(env: str, alias: str) -> tuple[bool, str]:
    """Returns (ok, message). ok=True iff:
      (a) host_vars schema valid (required fields present + value types)
      (b) SSH reachable using standard automation key
      (c) ansible ping succeeds
    """
    # (a) schema check
    data = read_host_vars(env, alias)
    required = [("ansible_host", str), ("ansible_port", int),
                ("ansible_user", str)]
    for key, typ in required:
        if not isinstance(data.get(key), typ):
            return False, f"host_vars missing or wrong type: {key}"
    # (b) SSH probe with standard automation key
    if not _ssh_probe(data["ansible_host"], data["ansible_port"],
                      data["ansible_user"], DEFAULT_AUTOMATION_PRIVATE_KEY):
        return False, f"SSH probe failed for {data['ansible_user']}@..."
    # (c) ansible ping
    if not _verify_standard_key(env, alias):
        return False, "ansible ping failed (host reachable but mgmt broken)"
    return True, "OK"
```

输出：

```
==> 验证 'jpntt' 现有配置 ...
    [✓] host_vars schema
    [✓] SSH probe (ansible@1156, ~/.ssh/ansispire_ed25519)
    [✓] ansible ping

==> 配置正确，无需变更。
```

或：

```
==> 验证 'jpntt' 现有配置 ...
    [✓] host_vars schema
    [✗] SSH probe: Permission denied (publickey)

==> 现有配置失效。是否覆盖? (y/N): _
```

`y` → 进入 §4.2 强制覆盖；`N` → rc=0 退出，不动状态。

### §4.2 强制覆盖子流程

当前 `core.add_host()` 在 alias 重复时 raise `VpsRunnerError`。强制覆盖需要新增 `overwrite=True` flag：

```python
def add_host(env, alias, *, ip, port=1156, user="ansible",
             status="pending", overwrite=False) -> Path:
    ...
    hv_path = host_vars_path(env, alias)
    if hv_path.exists() and not overwrite:
        raise VpsRunnerError(f"host_vars already exists: {hv_path}")
    if alias in list_aliases(env) and not overwrite:
        raise VpsRunnerError(f"alias '{alias}' already in hosts.yml ...")
    # ↓ if overwrite=True: silently replace
    ...
```

强制覆盖时 wizard 还要清理可能存在的临时 key 残留：

```python
if force_overwrite:
    _cleanup_temp_key(alias)  # 若存在的话
    delete_host_vars(env, alias)
    remove_alias_from_hosts(env, alias)
    # 然后走正常 add_host 路径
```

警告 prompt 一次：

```
==> 警告：将覆盖 'jpntt' 的现有 host_vars 和 hosts.yml 条目。原有配置会丢失。
继续? (y/N): _
```

---

## §5 实施拆分（建议 3 个子任务，单 PR 推到 dev）

| Sub | 主题 | 影响文件 | 约时 |
|---|---|---|---|
| T1 | field collector + auth 分支 + passwords dict | `vps_runner.py` (prompt_new_host 重写 / run_playbook 加 passwords kwarg) + `cli.py` (_cmd_add_host 重写) | 90 min |
| T2 | 密钥临时生命周期 + 验证 playbook | `vps_runner.py` (temp key write / cleanup / verify) + `playbooks/_verify_post_onboard.yml` (新) + `.gitignore` | 60 min |
| T3 | 同名 alias 4 选项菜单 + add_host overwrite | `vps_runner.py` (overwrite flag) + wizard 状态机 + `_verify_existing` | 60 min |
| T4 | 清理：弃用 make vps-onboard + onboard 子命令 ask-pass flag + 文档同步 | `Makefile` (rm vps-onboard) + `cli.py` (rm flags) + `docs/operations/vps-runner.md` (§3.3 改写) | 45 min |

合计 ~4 h。T1→T2→T3→T4 顺序执行，每步独立 verify (W-R15 3 gates) + commit。

---

## §6 测试矩阵

### Unit (no SSH, no network)

| 用例 | 验证点 |
|---|---|
| `_write_temp_key` 写入 + 权限 | content + 0o600 |
| `_write_temp_key` CRLF 归一化 | windows-style PEM 进来变 unix |
| `_write_temp_key` 拒绝无 BEGIN marker | raise VpsRunnerError |
| `_cleanup_temp_key` 幂等 | 文件不存在时 no-op |
| `prompt_new_host` 密码分支 happy path | 用 monkeypatch stub stdin + getpass |
| `prompt_new_host` 密钥分支 happy path | stub stdin 喂 PEM 多行 |
| `prompt_new_host` 同名 alias menu 选 1 | 返回 None，无副作用 |
| `prompt_new_host` 同名 alias menu 选 2 | 重提 alias |
| `add_host(overwrite=True)` 覆盖现有 | host_vars / hosts.yml 都更新 |
| `_verify_existing` schema fail | 返回 False + 明确 message |

### Integration (real ansible-runner)

| 用例 | 验证点 |
|---|---|
| `passwords=` dict 传到 ansible-runner | artifact `command` 文件**不含**密码值 |
| 密码分支 onboard 不再死锁 | 跑一遍 against TEST-NET-1 unreachable，rc 非阻塞地返回 |
| 临时 key + extravars 注入 | artifact `extravars.json` 记录的路径正确 |
| post-onboard verify playbook 调用 | `_verify_post_onboard.yml` 跑得起来（unreachable case 也要清晰报错） |

### Smoke (real VPS)

用 jpntt（116.80.96.126）作为真实复测目标，按 §2.2 走密钥分支端到端：
1. 操作员准备：`ssh-copy-id -i ~/.ssh/ansispire_ed25519.pub root@116.80.96.126`（一次性补足前提）
2. wizard 跑完 → expect: status=active + `ssh jpntt` 直连成功
3. 再跑 wizard 一次 → expect: §4.1 验证通过分支 → 「配置正确，无需变更」

---

## §7 弃用清单

| 项 | 状态 | 替代 |
|---|---|---|
| `make vps-onboard ALIAS=...` | 删除 Makefile target | 首次：wizard；重跑：`.venv/bin/python -m plugins.vps_runner.cli onboard <alias> --env dev` |
| `onboard` 子命令 `--ask-pass` flag | 删除 argparse argument | 首次密码登录走 wizard |
| `onboard` 子命令 `--ask-become-pass` flag | 删除 | 同上 |
| `onboard` 子命令 `--bootstrap-user/--bootstrap-port` flag | **保留**（重跑场景需要） | — |
| `onboard` 子命令 `--first-time` flag | **保留** | — |
| 现 wizard「继续 onboard? [Y/n]」分支硬编码 ask_pass=True | 重写为本 plan §2 流程 | — |

---

## §8 W-R20 destructive-sink 评估

| 操作 | 是否 destructive sink | 处理 |
|---|---|---|
| `_cleanup_temp_key` 调 `unlink()` | 本机本项目内单文件删除，可恢复（重跑 wizard 重粘贴） | **不算** destructive sink。Sibling to W-R19: 不动 git ref，不动远程，不动 shared state |
| `add_host(overwrite=True)` 覆盖 host_vars | 本地 inventory 文件覆盖（git 可恢复） | 不算 |
| `delete_host_vars` / `remove_alias_from_hosts` (强制覆盖路径里调用) | 同上 | 不算 |
| onboard 本身 | 远程 VPS 上做大量变更（user / 端口 / 防火墙 / sshd） | 算 destructive，但**这是 onboard.yml 一直就做的事**，本 plan 不引入新的远程 destructive sink |

结论：R11 实施完后不需要额外 `/ultrareview` 触发（与 R7-R10 同等级）；merge-to-dev 时仍按标准走整体外审。

---

## §9 Next Steps（plan 通过后）

1. 用户 sign-off this plan
2. 开 R11 实施：T1 → T2 → T3 → T4 顺序，每个子任务结束跑 3-gate + commit
3. R11 实施完毕后跑真实 smoke（jpntt 或新机），写 round11 changelog
4. 全 branch（R7+R8+R9+R10+R11）一起 open PR → dev，触发 /ultrareview 外审

**Open questions（用户已拍板 2026-05-22）**：

- (Q1) **决议：早退 + 提示 ssh-keygen 命令**。wizard 不内嵌密钥生成。`_wizard_entry_check()` 缺密钥时 rc=3 退出，stderr 打印两行可复制粘贴的 ssh-keygen 命令。
- (Q2) **决议：加 `vps_runner.bootstrap_key` 字段**。onboard 成功后设为 `null` 视为 unset（YAML key 保留，便于阅读 schema）；onboard `--first-time` 启动时检查该字段，存在则自动注入 extravars。R7 `examples/host_vars.yml.template` 同步加注释版字段。

---

*Plan written 2026-05-22. Two open questions resolved 2026-05-22. Awaiting explicit "go" for R11 T1 implementation kickoff.*
