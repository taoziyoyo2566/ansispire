# 技术调查报告 — Ansible 多服务器管理最佳实践对照

## 1. 调查概览
- **调查 ID**: `IVG-MULTI-SERVER-ANSIBLE-PRACTICE`
- **关联**: feat-vps-batch-parallel plan-2026-05-16、IVG-VPS-BATCH-PARALLEL、reality-ops 上游、ansispire vps_manager 现状
- **调查类型**: 可行性研究 + 同行复核（second-opinion on self-proposed plan）
- **目标**:
  1. 探索性调查 Ansible 官方 + 社区在「多服务器管理」上的最佳实践，**不预设结论**。
  2. 对照 vps_manager 当前实现与 feat-vps-batch-parallel plan，识别反范式之处。
  3. 决定 plan-2026-05-16 是否仍然成立、或需要重新设计。
- **触发**: user 2026-05-16 — "先调查 ansible 在管理多服务器方面的最佳实践，... 我对你给的方案有点质疑。不要预先设定结果，要探索性的去调查"。

## 2. 背景
- 我刚起草 `feat-vps-batch-parallel/plan-2026-05-16.md`，提议 Action Batching + 自写 Callback Reporter，解决 vps_manager per-task 串行问题。
- user 质疑这套设计，要求先做最佳实践调查。
- 我自己也意识到——之前的 plan 是「在 vps_manager 既有架构之上加层」，未质疑根基。

## 3. 调查方法
1. 重读 reality-ops 上游 `deploy.yml` + `inventory.ini` + `ansible.cfg`——验证「真实生产多节点方案怎么写」。
2. WebSearch 4 个维度：
   - Ansible 多节点编排（forks / strategy / serial / throttle）
   - 静态 vs 动态 inventory 对 VPS lifecycle 的适用性
   - ansible-runner Python API（替代 subprocess）
   - AWX/Tower 的多节点 batch 调度
3. 对照 vps_manager.py 实际代码（process_paths / execute_task / build_ansible_inventory）。

## 4. 证据

### 4.1 reality-ops 上游真实范式（生产已跑 13 个节点）

```ini
# inventory.ini —— 静态，按层级分组
[reality_nodes]
dzire ansible_python_interpreter=/usr/bin/python3
netcup ...
ams ...
dcc ...
[free]
dp
legend
dzire
[basic]
lej
netcup
...
```

```ini
# ansible.cfg —— Ansible 原生并发 + 长连接
[defaults]
forks = 20
host_key_checking = True
[ssh_connection]
pipelining = True
ssh_args = -o ControlMaster=auto -o ControlPersist=10m -o StrictHostKeyChecking=accept-new
```

```yaml
# deploy.yml —— 一次 play 对所有 reality_nodes 跑
- hosts: reality_nodes
  pre_tasks:
    - 加载全部用户配置（delegate_to: localhost）
    - 每节点本位计算自己承载哪些用户（set_fact + acl_matrix 交集）
  roles:
    - reality_single (when reality_mode == 'single')
    - reality_multi  (when reality_mode == 'multi')
    - monitor
  post_tasks:
    - delegate_to: localhost 推 Gist（仅 first host）
```

**核心特征**：
- ❌ 没有 inbox / 任务队列
- ❌ 没有 per-task subprocess
- ❌ 没有自写 callback reporter
- ✅ 一次 `ansible-playbook deploy.yml` 调用，Ansible 自己 fan-out 到 13 个节点
- ✅ 每节点的差异化逻辑在 playbook 内部（per-host set_fact）
- ✅ delegate_to: localhost 处理控制端协调任务

### 4.2 Ansible 官方推荐：ansible-runner

- 官方文档：「If you want to use Python API only for executing playbooks or modules, Ansible recommends considering ansible-runner first.」
- `ansible_runner.runner.Runner.events` ——**结构化** host event 流（dict）
- `Runner.host_events(hostname)` ——按 host 取事件列表
- `Runner.stats` ——最终统计（成功/失败/不可达 per host）
- `async_run()` ——异步执行（返回 thread + Runner）
- 自动管理 artifacts（events + stdout 都落盘）
- AWX 内部就用 ansible-runner

**对比 vps_manager.py:714-809 现状**：
- 用 `subprocess.Popen` + 自己 select.select 轮询 stdout
- 通过 returncode 判断成败
- callback_plugins/human_log.py 美化输出
- **没有 per-host 结构化结果**——失败时只能从 stdout 猜哪个 host 挂了

### 4.3 AWX Job Slicing（生产级多节点方案）

- 大 inventory → 切分成 chunk（slice）
- 每个 slice 起独立 `ansible-playbook` 进程
- 多个 slice 跨 cluster 节点**并行**
- **每个 slice 内部仍用 Ansible 原生 forks**

**关键对比**：AWX 是**切分**（把大 inventory 分小段），我的 plan 是**聚合**（把多 task 合并）——方向相反。AWX 的前提是「一次 playbook 就该对 N 个 host 跑」，所以问题是「N 太大要切」；我的前提是「一次 playbook 跑 1 个 host」，所以问题是「task 多了要合」——后者本身就不应该存在。

### 4.4 Ansible 多节点性能与并发控制

- `forks` —— 同时连接的 host 数（默认 5，社区推荐 20-50）
- `serial` —— rolling 批次（每批 N host 跑完整 play 再下一批）
- `throttle` —— per-task worker 上限（防 rate-limit）
- `strategy: free` —— host 之间不互等（默认 linear）
- `async` + `poll: 0` —— 任务异步触发，后续查询结果

这套四件套覆盖了所有「N 节点同时操作」的真实需求，**全部内置**。

### 4.5 VPS Bootstrap（首次接入）的标准模式

- `raw` module + `gather_facts: no` + `--ask-pass` —— 处理未装 Python 的裸节点
- 一次 bootstrap.yml 对 hosts: all 跑，**仍是多节点并发**
- 节点加进静态 inventory（手动 / dynamic inventory script） → 后续走标准 SSH key

vps_manager `onboard` 当前实现的等价部分是 OK 的（用 bootstrap.host + bootstrap.user + password_env），但**强制单节点**——一次只能 onboard 一台，破坏 Ansible 多节点 bootstrap 的天然能力。

### 4.6 vps_manager 当前模式 vs Ansible 范式 — 三层错位

| 层 | vps_manager 现状 | Ansible 范式 | 错位严重度 |
|---|---|---|---|
| **调度模型** | runtime/inbox/vps/{pending,processing,...} 队列 + per-task 串行 process | inventory + `ansible-playbook` 一次对一组 host 跑 | 🔴 反范式（Ansible forks 闲置）|
| **执行 API** | `subprocess.Popen` + select.select 轮询 stdout + callback_plugins/human_log | `ansible_runner.run()` + `Runner.events` 结构化事件 | 🔴 官方有更好 API，自己写了次品 |
| **State 模型** | `runtime/state/vps_inventory.yml`（自定义 schema） | `inventory/<env>/hosts.yml` + `host_vars/<alias>.yml` | 🟡 SSOT 二义性，与标准 inventory 并存但语义不互通 |
| **结果收集** | subprocess returncode + 整批 ok/fail | per-host event stream + per-host stats | 🔴 失败时无法定位是哪个 host |
| **Inventory 构造** | 每个 task 临时生成单 host inventory | 静态多 host inventory 复用 | 🟡 每次都重建 → 浪费 + 不一致风险 |

## 5. 发现与分析

### 5.1 我的 plan-2026-05-16 的根本问题

之前提的 Action Batching：
1. **基于错误根基继续叠层**：不质疑 inbox 模式 / subprocess 模式 / 自写 callback，反而在三层反范式之上加 batching。
2. **重复造轮子**：Callback Reporter 是 ansible-runner `Runner.events` 的等价物，但更原始。
3. **保留 subprocess 模式**：放弃了 ansible-runner 已有的 host_events / stats / async_run。
4. **不解决 SSOT 二义性**：vps_inventory.yml 仍与标准 inventory 平行。
5. **方向反 AWX**：AWX 是切分大 inventory，我是聚合零散 task —— 后者根本不应该存在（zero task 应该一次提交，不是 N 个 single-host task）。

### 5.2 vps_manager inbox 模式的实际价值

inbox 模式的**真实有用部分**：
- ✅ 持久化操作历史（archive/done/failed）→ 审计 / 回溯
- ✅ task schema 校验（pre-flight）→ 错误前置
- ✅ pending → processing → done 状态机 → 幂等性 + 重试边界

inbox 模式的**实际无用部分**：
- ❌ 「队列削峰」—— vps 操作不是高频事件，没有削峰需求
- ❌ 「per-task 独立进程」—— Ansible forks 已经处理并发
- ❌ 「per-task inventory 动态生成」—— 标准 inventory 早就够了

### 5.3 真实痛点重新定位

user 说「manager vps 分支只考虑了单节点」——重新理解：
- **不是「想要 batching 功能」**
- **是「想要 vps_manager 用上 Ansible 多节点能力」**

这两个解法**完全不同**：
- 我之前的 batching = 在 inbox 模式之上加合并层（错位修复）
- 正确方向 = 让 vps_manager 直接走「standard inventory + ansible-runner + Ansible forks」（根基修复）

## 6. 结论与建议

### 6.1 总判决

- **plan-2026-05-16 暂停**，不要按它实施。它解决的是错位症状，不是根本病因。
- **真正问题**：vps_manager 用 inbox + subprocess + 自写 callback 实现了「Ansible 包装的下位替代品」，让 Ansible 的多节点能力闲置。
- **真正方向**：让 vps_manager 用 ansible-runner + 标准 inventory，把它从「队列调度器」改造成「Ansible 多节点能力的轻量 CLI 入口」。

### 6.2 三个可行路径（取代之前的 A/B/C）

**X. 最小修：保留 inbox + 给 ansible-playbook 调用加 `--forks N` 实现 batching**（接近原 plan-2026-05-16 但去掉自写 callback）
- 改动：仅修改 `execute_task` 当 batch 时启用 `--forks`；用 `--extra-vars` 把 task 数据注入；解析 PLAY RECAP 替代自写 callback
- 优点：改动最小（~1 天工作）
- 缺点：仍用 subprocess、仍是 inbox 内合并、还是反范式；放弃了 ansible-runner 的好处
- 适用：user 想最快出 batching 能力、其他重构延后

**Y. 中修：ansible-runner 替代 subprocess + 同 action 聚合**（推荐）
- 改动：
  1. `execute_task` 改用 `ansible_runner.run()` 替代 `subprocess.Popen`
  2. inbox 内同 action 多 task 聚合为单次 `run()`，inventory 含 N host
  3. 通过 `Runner.events` / `Runner.host_events(alias)` 得 per-host 结构化结果
  4. callback_plugins/vps_batch_reporter.py **不写**（ansible-runner events 已等价）
  5. callback_plugins/human_log.py 保留（输出体验）
- 优点：对齐 Ansible 范式、用上官方 API、forks 自然生效、per-host 故障可定位
- 缺点：需要给 vps_manager 加 ansible-runner 依赖（requirements.txt）；execute_task 重写
- 风险：ansible-runner 在 venv 内行为需要测试（特别是 EE / molecule 场景的兼容性）
- 工作量：2-3 天

**Z. 大修：重新定位 vps_manager 为「Ansible 多节点 CLI 入口」**
- 改动：
  1. Y 的全部内容
  2. + 把 `runtime/state/vps_inventory.yml` 退化为 `inventory/<env>/hosts.yml` 的镜像生成器（或直接砍掉，用标准 inventory）
  3. + inbox 退化为「CLI command history」（pending → done，仅作审计，不参与执行流）
  4. + 增加「standard ansible-playbook 入口」：`vps-manager run <playbook> --limit <group>` 直接对 inventory group 跑
- 优点：彻底回归 Ansible 范式、SSOT 单一、未来扩展空间最大
- 缺点：改动范围大、需要 migration 已有 vps_inventory.yml 数据、要重新设计 CLI surface
- 风险：高（需要重新走完整的 architecture-level plan + user 验证 + 真实生产数据迁移）
- 工作量：1-2 周（含 plan + 实施 + 测试 + 文档）

### 6.3 推荐

**推荐 Y（中修）**，理由：
- 真正解决我之前 plan 的根本问题（subprocess + 自写 callback）
- 不需要 big bang，inbox 模式可以保留作为审计层
- 改动范围聚焦 `execute_task` 和 `build_ansible_inventory`，可测可回滚
- 为未来走 Z 留接口（ansible-runner 一旦接入，Z 的剩余部分就是渐进重构）

**不推荐 X**，理由：自写 callback 已经被 IVG 4.2 证明是重复造轮子；继续走 X 会让代码债更深。

**Z 可作为长期目标**，但不应在本轮做——会和 reality-migration 优先级冲突，且 user 在 dev 阶段，过度重构换不来当下价值。

### 6.4 对 reality-migration 的影响

- 如果选 Y：reality-migration 阶段 3 deploy.yml 走标准 Ansible 范式（`hosts: reality_nodes` + per-host set_fact），**不**复用 vps_manager 的 ansible-runner 封装——因为 reality_deploy 是「日常运维 playbook」，不是「lifecycle task」，性质不同。
- 如果选 X：同上，但 reality-migration 阶段 3 仍要单独写一份「不走 vps_manager」的约定。
- 如果选 Z：reality-migration 阶段 3 可以直接 `vps-manager run reality_deploy.yml --limit reality_nodes`——但要等 Z 完成。

### 6.5 经验教训

- **接受任务前先质疑根基**：我接到「实现 batching」需求时直接进入设计 Phase，没问「为什么 vps_manager 是 per-task 串行？这本身合理吗？」结果方案是错位修复。
- **跨语言/跨工具的反范式实现，常被作为「补丁」继续叠层**：vps_manager 用 subprocess 包 ansible-playbook 是补丁，我提议的 batching 是补丁之上的补丁。每加一层补丁都让回归 Ansible 范式更难。
- **user 的「质疑」比 review 更有价值**：Gemini r1/r2 都没指出 vps_manager 用 subprocess 是反范式（因为 Gemini 是在我已写好的 plan 上做 review，框定在了错误问题域内）。user 一句「我对方案有质疑」反向打开了根基质疑空间。
- **「探索性调查」不预设结论**：原 plan-2026-05-16 §3 的设计决策（D1-D6）都是「假定 batching 方向正确，决策细节」。真正的探索应该回到「batching 方向是否正确」。

## 7. 关联验证
- **TSVS 引用**: 暂无（本次为方法论调查）
- **验证结果**: N/A——结论是「现有 plan 暂停，按 §6.2 重新选路径」
- **复用证据**:
  - reality-ops `ansible.cfg` + `inventory.ini` + `deploy.yml` 真实代码
  - vps_manager.py:264-289 (process_paths)、:714-809 (execute_task)、:820-858 (build_ansible_inventory) 真实代码
  - Ansible 官方文档：strategies / forks / dynamic inventory / ansible-runner Python API
  - AWX Job Slicing 文档

---
*Generated by Ansispire Investigation Engine — 反思自己的 plan-2026-05-16 后的根基级复核。*
