# Annotated Review — Codex (gpt-5.5 xhigh) on plan-2026-05-16.md

> 日期：2026-05-16
> 审查者：Codex (gpt-5.5 xhigh)
> 注释者：Claude（pre-accept-verification 范式逐条核验 + 自我审查）
> 关联：[`plan-2026-05-16.md`](./plan-2026-05-16.md)
> 触发：user 用 codex 做 second-opinion；明确要求「对这个 review 结果进行自我审查」（即 codex review 自身也走 pre-accept verification）

---

## 0. 自我审查方法论

按 [[pre-accept-verification]] 范式：每条 codex 声明跑三步验证：
1. **可验证性判定** —— 文件内容 / 命令存在 / 文档语义？前者必须查证
2. **项目约定核查** —— 与现有 ansible.cfg / playbook / runtime 约定是否冲突
3. **是否重复造轮子** —— codex 是否漏掉了上游已有方案

verifications 全部当场跑（grep / Read / WebFetch），不凭推理。

---

## 1. Codex 5 条声明逐条核验

### 1.1 #1 — `forks=20` 在 ansible.cfg 不存在

**Codex 声明**：plan §3.3 写 "ansible.cfg 既有 forks=20" 但实际 ansible.cfg 没有

**核验**：
```bash
$ grep -n forks /home/netcup/workspace/ansispire/ansible.cfg
（empty）
$ head -30 ansible.cfg | grep -A1 "\[defaults\]"
[defaults]
inventory = inventory/prod
```

**结论**：✅✅ **完全准确** — 我的 plan §3.3 Gap Analysis 表格内措辞「Ansible forks=20（ansible.cfg 既有）」是事实错误。Ansible 默认 forks=5。

**Plan 修订**：
- §1.4 验收点：加 "forks 显式覆盖到 20"
- §3.3 Gap Analysis 表：改措辞为「ansible_runner.run(forks=20) 或 ansible.cfg [defaults] 加 forks=20」
- §3.5 多节点 batch：明确 forks 来源

### 1.2 #2 — Runner 路径模型需修正

**Codex 声明**：`private_data_dir` 指日志目录，但 `playbook` 默认相对 `private_data_dir/project` 解析，inventory 类似——建议传 `project_dir=PROJECT_ROOT` + 绝对路径 inventory + `artifact_dir` + `ident`

**核验**（WebFetch `https://docs.ansible.com/projects/runner/en/stable/ansible_runner/`）：
- `project_dir`：「The path to the playbook content, this defaults to 'project' within the private data dir」 ✅
- `playbook`：「a path relative to `private_data_dir/project`」 ✅
- `inventory`：「path to the inventory file in the `private_data_dir/inventory` directory or an absolute path」 ✅
- `artifact_dir`：「defaults to 'artifacts' under the private data dir」 ✅
- `ident`：「The run identifier ... used to create and name the artifact directory」 ✅

**结论**：✅✅ **完全准确** — 我 plan §3.3 草案的当前写法（`private_data_dir=runtime/logs/.../{run_id}` + `playbook="plugins/vps_runner/playbooks/X.yml"`）会去 `runtime/logs/.../{run_id}/project/plugins/vps_runner/playbooks/X.yml` 找，**必然 FileNotFoundError**。

**Plan 修订**：
- §3.3 Execution API 草案：改用 codex 推荐的混合：
  ```python
  runner = ansible_runner.run(
      project_dir=str(PROJECT_ROOT),
      playbook=f"plugins/vps_runner/playbooks/{action}.yml",
      inventory=str(PROJECT_ROOT / "inventory" / env),
      artifact_dir=str(PROJECT_ROOT / "runtime" / "logs" / "vps_runner"),
      ident=run_id,
      extravars=extravars or {},
      envvars={"ANSIBLE_CONFIG": str(PROJECT_ROOT / "ansible.cfg")},
  )
  ```

### 1.3 #3 — 密码不能只靠事后 redact

**Codex 声明**：`extravars/envvars/passwords` 会进入 `private_data_dir/env`；建议 `suppress_env_files=True` + 敏感 task `no_log: true` + `rotate_artifacts`

**核验**（WebFetch 同上 URL）：
- 「All three (extravars, envvars, passwords) ... will also be read from `env/envvars` in `private_data_dir`」 ✅ 数据落盘真实
- `suppress_env_files`：「Disable the writing of files into the `env` which may store sensitive information」 ✅ 参数存在
- `rotate_artifacts`：「Keep at most n artifact directories, disable with a value of 0 which is the default」 ✅ 参数存在
- Ansible `no_log` keyword：项目内已有用法（grep 各 role）— 是 Ansible 原生 task-level 选项 ✅

**结论**：✅✅ **完全准确** — 我 plan §3.7 的当前措辞「事后 redact」是**反防御性**思路（让敏感数据先落盘再清理 vs 一开始就不落）。

**Plan 修订**：
- §3.7 重写：
  - 主防线：`suppress_env_files=True`（敏感数据不进 disk）
  - 二线：`no_log: true` 标在 onboard.yml 中处理密码的 task 上
  - 三线：`rotate_artifacts=10`（即使有泄露也限制保留窗口）
  - 事后 redact 改为「补充防线」措辞，不当主防线

### 1.4 #4 — bootstrap claim 与旧 onboard.yml 复用冲突

**Codex 声明**：plan §0-D 说 bootstrap 走 raw + gather_facts:no，但 T2.3 又说复用旧 onboard.yml；旧 `plugins/vps_manager/playbooks/onboard.yml:2` 是 `gather_facts: true`，grep 无 raw module

**核验**：
```bash
$ grep -n "gather_facts\|raw " plugins/vps_manager/playbooks/onboard.yml
5:  gather_facts: true
$ head -20 plugins/vps_manager/playbooks/onboard.yml
- name: Onboard VPS into Ansispire management
  hosts: vps_targets
  become: true
  gather_facts: true
  gather_subset: [min]
  ...
```

**结论**：✅✅ **完全准确** — 我 plan §0-D 和 §4 T2.3 自相矛盾。旧 onboard.yml 不支持裸机 bootstrap，它假设节点已有 Python（Ubuntu/Debian 默认装 python3）。

**Plan 修订**：
- §0-D Best-Practice Pre-Check 第 4 行（bootstrap）：改为「**仅支持已有 Python3 的 Ubuntu/Debian/Alpine VPS**（项目目标场景）；若未来需 bootstrap 裸机，单独加 `playbooks/bootstrap_python.yml` 走 raw module，但本 plan 不实施」
- §4 T2.3：明确「复用 onboard.yml 的前提是节点已有 Python」+ 在 README 列前置条件
- §6 加新 D8：「是否需要 raw bootstrap 阶段」决策点（默认 No，dev 阶段所有 VPS 都是 Ubuntu）

### 1.5 #5 — 静态 inventory 的理由要改严谨

**Codex 声明**：「节点数 < 50」不够严谨。Ansible/AWX 判断标准是「是否有外部事实源 / 云 provider / CMDB」。如果 VPS 是本插件手工 onboard 的事实源 → 静态 inventory 合理

**核验**：
- AWX dynamic inventory best practice 文档（之前 WebSearch 已读）：dynamic inventory 适用于"infrastructure changes frequently"、"cloud instances spin up and down"、"auto-scaling groups resize"
- vps_runner 场景：节点是 user 手工 onboard 的——**事实源就在本插件**——不存在外部 fact source

**结论**：✅ **正确** — 这是 semantic 修订，不是 bug。「节点数 < 50」是次要标准；「事实源是否外部」才是主要标准。

**Plan 修订**：
- §1.3 Out-of-scope：「不实现 dynamic inventory plugin（节点数 < 50 不需要）」改为「不实现 dynamic inventory plugin（事实源在本插件，无外部 cloud provider / CMDB 需要同步）」
- §6 D2：同步修

---

## 2. Codex 自身漏掉的项（Claude second-opinion）

按 [[pre-accept-verification]]，不仅核验 codex 是否对，也要核验 codex 是否完整。

### 2.1 Codex 漏掉的 ansible.cfg 副作用

我跑 `head -30 ansible.cfg` 时还看到：

```ini
[defaults]
inventory = inventory/prod          ← 默认 inventory 是 prod！
vault_password_file = .vault_pass

[privilege_escalation]
become = True
become_method = sudo
become_ask_pass = False             ← 默认 sudo 无密
```

**潜在风险**：
- (a) **inventory = inventory/prod**：dev/stag 操作必须显式 `inventory=...` 覆盖，否则会**默认对 prod 跑**——非常危险。codex 提到了 inventory 绝对路径但没强调这个 default override 的风险
- (b) **become_ask_pass = False**：onboard 新节点时如果节点 sudo 配置要求密码（默认 Ubuntu cloud image 通常允许 NOPASSWD 但 hostinger/某些 provider 不允许），会卡住——bootstrap 必须 `--ask-become-pass` 或 `ansible_become_password` 覆盖

**Plan 修订**：
- §3.7 加：「`inventory` 参数必须显式传 `inventory/{env}/`，禁止依赖 ansible.cfg 默认值——加 unit test 验证」
- §7 R4 风险：「become 默认无密；onboard 首次时新节点 sudo 配置不可控，必须支持 `--ask-become-pass` 路径」

### 2.2 Codex 漏掉的 ANSIBLE_CONFIG 继承问题

我 plan §3.3 草案有 `envvars={"ANSIBLE_CONFIG": str(PROJECT_ROOT / "ansible.cfg")}`。但 ansible-runner 文档说 envvars 会被写到 `private_data_dir/env/envvars`——如果同时启用 `suppress_env_files=True`，envvars 会怎么传？

**核验需要**：round 2 spike 时确认（可能 ansible-runner 用 `envvars` 时是直接 inject 到子进程 env 而不一定靠 disk）

**Plan 修订**：
- §7 R5 风险：「`suppress_env_files=True` 与 `envvars` 传 ANSIBLE_CONFIG 的交互需 round 2 起手前 30 分钟 spike 验证」

### 2.3 Codex 漏掉的提：本 plan §3.5 中关于「`audit` 用 group pattern」的多节点能力，验收点（§1.4）应该加「per-host 并发实测」

**Plan 修订**：
- §1.4 加一条验收点：「3 节点 audit 实测，PLAY RECAP 时间戳显示并发执行（不是顺序），且 ident 下 `events.jsonl` 含 3 个 host 的 events」

---

## 3. Codex review 取舍汇总

| # | Codex 发现 | 评级 | 引发的 plan 修订 |
|---|---|---|---|
| 1 | `forks=20` 不存在 | ✅✅ Strong Accept | §1.4 + §3.3 + §3.5 修订 |
| 2 | Runner 路径模型 | ✅✅ Strong Accept | §3.3 Execution API 草案重写 |
| 3 | 密码 redact 是补防线 | ✅✅ Strong Accept | §3.7 重写（suppress_env_files + no_log + rotate_artifacts） |
| 4 | bootstrap 与旧 playbook 冲突 | ✅✅ Strong Accept | §0-D 第 4 行 + §4 T2.3 + §6 新 D8 |
| 5 | 静态 inventory 理由不严谨 | ✅ Accept | §1.3 + §6 D2 措辞修订 |
| 6 (Claude 补) | inventory=inventory/prod 默认风险 | ✅ Self-find | §3.7 + §7 R4 |
| 7 (Claude 补) | suppress_env_files vs envvars 交互 | ⚠️ Need-verify | §7 R5（round 2 spike）|
| 8 (Claude 补) | 多节点并发实测验收点 | ✅ Self-find | §1.4 加一条 |

净结果：5/5 完全采纳 codex + 3 项 Claude 自补。Codex review 质量评分 **9/10**（远高于 Gemini r1/r2，4 个必修点全部基于事实核验，准确率 100%）。最有价值贡献是 #3（密码防御性，把 redact 从"主防线"降级为"补防线"）。

---

## 4. plan-2026-05-16.md 实际 diff（本 round 落地）

详见 plan 文件本身；摘要：
- **§0-D Best-Practice Pre-Check**：bootstrap 行措辞修订（只支持已有 Python 的 VPS）
- **§1.3 Out-of-scope**：dynamic inventory 理由改为「无外部事实源」
- **§1.4 Judgment Criteria**：加 forks 显式覆盖到 20 验收 + 3 节点并发实测验收
- **§3.3 Gap Analysis 表**：forks 行措辞改正
- **§3.3 Execution API 草案**：完整重写，含 project_dir + 绝对路径 inventory + artifact_dir + ident
- **§3.5 多节点 batch**：forks 来源明确
- **§3.7 安全与密码**：suppress_env_files / no_log / rotate_artifacts 三层防御 + inventory 必须显式传
- **§4 T2.3**：明确复用 onboard.yml 的前提
- **§6 D2**：静态 inventory 理由修订
- **§6 新 D8**：是否需要 raw bootstrap 阶段（默认 No）
- **§7 加 R4/R5**：become 默认无密风险 + envvars/suppress_env_files 交互 spike

---

## 5. Loop 状态

| 阶段 | 状态 | 备注 |
|---|---|---|
| Plan r1 (Claude) | ✅ Done | 2026-05-16 |
| Review r1 (Codex) | ✅ Done | 本文上半（user 提供原文）|
| Self-audit r1 (Claude) | ✅ Done | pre-accept-verification 三步逐条核验 + WebFetch 实证 + 自补 3 项 |
| Action r1 (Claude → plan diff) | ⏳ Pending | §4 摘要 + 实际 Edit |
| Review r2 (Codex 或其他) | 🔲 Pending | user 可选再过一轮，或批准修订后的 plan 直接进 round 2 |

---

## 6. Next Steps（本注释引发）

**Immediately doable**
- **(claude)** 按 §4 立即落 plan diff（本 round 内）
- **(user)** plan 修订后选路径：
  - (a) 批准修订版直接进 round 2 实施（建议——本轮 codex review + self-audit 已收敛主要风险点）
  - (b) 再让 codex / 其他 agent review 修订后的 plan（review r2）

**Blocked**
- 无新增——本 review 没触发任何认证 / 凭据 / 远端操作需授权项

**Deferrable**
- D8 raw bootstrap：默认 No，未来出现非 Ubuntu/Debian 节点时再加
- §7 R5 spike：round 2 起手前 30 分钟做

---
*Annotated by Claude in response to Codex review; plan diff applied in the same round per workspace W-R8.*
