# 技术调查报告 — 最佳实践核验缺口反思（Process / Governance Gap）

## 1. 调查概览
- **调查 ID**: `IVG-REFLECT-BESTPRACTICE-GAP`
- **关联**: IVG-MULTI-SERVER-ANSIBLE-PRACTICE、feat-vps-batch-parallel plan-2026-05-16（已暂停）、vps_manager 历史 commit `083fb7f`
- **调查类型**: 元层反思 / governance audit
- **触发**: user 2026-05-16 — 「我之前反复强调过以最佳实践为基础来实现，但是还是出现了这种情况，这是个很大的问题，急需马上处理」
- **目标**: 不止找出 vps_manager 反 Ansible 范式实现是怎么发生的，更要找出**为什么现有 governance 没拦住**，并补上规则。

## 2. 背景
- 2026-05-15 vps_manager 单 commit `083fb7f` 引入，~6000 行代码 + 7 个 playbook。
- 2026-05-16 user 让我做 batching，我直接进入「如何加 batching」的设计，**没质疑根基**。
- user 第二次要求「探索性调查、不要预设结果」才触发 IVG-MULTI-SERVER-ANSIBLE-PRACTICE，发现 3 层反范式。
- 这不是单点失误，而是**两次都没用上「框架最佳实践核验」**——必须当作系统问题。

## 3. 调查方法
1. 查 vps_manager 引入历史（git log + plan 文档存在性）。
2. 扫描 3 层 CLAUDE.md + memory 找「最佳实践核验」相关规则的覆盖范围与盲区。
3. 复盘 2026-05-16 我自己的响应链路，定位哪一步该触发核验但没触发。

## 4. 证据

### 4.1 vps_manager 引入路径（重大遗漏）

```
$ git log --oneline -- plugins/vps_manager/ | tail -5
083fb7f feat(vps): add VPS manager lifecycle plugin       ← 单 commit 引入

$ ls docs/reviews/ | grep vps
feat-vps-batch-parallel                                   ← 是 batching plan（已反转）

$ find docs/reference/investigations -name "*VPS*" -o -name "*vps*" | grep -v MULTI | grep -v BATCH
（空）                                                     ← 引入前无 IVG
```

**事实清单**：
1. vps_manager 引入**没有 plan 文档**（`docs/reviews/feat-vps-manager/`）
2. 引入**没有 IVG**（feasibility / best-practice check）
3. 单 commit 6000+ 行代码 + 完整 CLI + 7 个 playbook 直接 land 在 `feat/infra-hub-deployment` 分支
4. commit message 提了 "Verification: make verify" —— 是 lint + 测试套件通过，**不是**最佳实践审查
5. 同 commit 改了 `ARCHITECTURE.md` + `feature-map/INDEX.md` + `test-plan.md` —— **事后**登记，不是先有 RFC 再实施

**违反规则**：
- workspace W-R1（plan-first）：该改动是 L2 架构级（新子系统，引入"任务队列调度模型"），必须有 plan doc
- workspace W-R3（roadmap-approved-first）：3+ task 的 work，必须有 user sign-off
- ansispire CLAUDE.md §0 Proactive Challenge：「AI MUST NOT blindly implement changes. Perform an Impact Analysis first.」—— 没有 Impact Analysis

### 4.2 现有 governance 规则的覆盖范围扫描

| 规则 | 覆盖什么 | 不覆盖什么 |
|---|---|---|
| ansispire CLAUDE.md §0 Proactive Challenge | "不要盲目实施，先做 Impact Analysis" | **没具体到「核验所用工具/框架的最佳实践」** |
| ansispire CLAUDE.md §3 Evidence-based Verification | 「每个修改都要有 terminal log（lint/test/syntax）背书」 | terminal log 只能验证「代码能跑」，**不能验证「设计符合工具范式」** |
| workspace W-R1 plan-first | 新功能要有 plan doc | plan doc 内容是否包含「最佳实践对照」是模糊的 |
| workspace W-R4 (Intent Clarification) | "boundaries / NFR / authorization" 必须在第一段问 | **没有**「该方案是否符合所用工具范式」这一项 |
| workspace W-R14 (CLAUDE.md 内容粒度) | "no matter what I'm doing, I should X" 测试 | 测试本身是好的，但**没有具体的「核验最佳实践」规则**通过这个测试 |
| memory `feedback_pre_accept_verification` | **接受外部 review / Gemini findings** 时核验 | **不覆盖**：自己设计新功能时核验所选范式；在已有实现之上加功能时先核验已有实现 |
| memory `feedback_dev_stage_pragmatism` | 砍过度设计 / 阶段匹配 | 引用了 user 「以最佳实践为基础」原话，但应用方向是"砍"而不是"主动核验" |

**核心 gap**：所有现有规则都是**响应式**（accept-then-verify / 实施时跑 lint），缺少**前置式核验**——
- 写 plan 之前没有强制问：「该方案是否符合所用工具的最佳实践？」
- 已有代码之上加功能时没有强制问：「已有代码本身是否符合最佳实践？如果不符，是否应该修底座而非加补丁？」

### 4.3 我 2026-05-16 失误链路复盘

| 步骤 | 我做了什么 | 应该做什么 | 触发哪条规则 |
|---|---|---|---|
| 1. user 说 "manager vps 分支只考虑了单节点" | 接受问题域 = 「如何让 vps_manager 支持多节点」 | 应该先问 "vps_manager 当前为什么是单节点？这本身是设计选择还是反范式？" | W-R4 + §0 Proactive Challenge |
| 2. 找到 IVG-VPS-BATCH-PARALLEL（之前的批量方案） | 接受其前提 = 「Action Batching 是正确方向」 | 应该先核验其前提：上游 reality-ops 怎么处理多节点？Ansible 范式是什么？ | `feedback_pre_accept_verification` —— **但这条规则的当前 scope 只覆盖外部 review，不覆盖自家 IVG** |
| 3. 起 plan-2026-05-16，写 6 个 Decisions | 在「Batching 方向正确」前提下写决策细节 | 应该先写 IVG 验证 Batching 方向是否正确 | 缺规则！ |
| 4. plan 写出后给 user | 推荐路径 B = "先做 batching 再回头" | 应该给的是 "我需要先 IVG 验证方向" | 缺规则！ |
| 5. user 质询 "不要预设结论" | 触发 IVG-MULTI-SERVER-ANSIBLE-PRACTICE | （正确）但本来不需要 user 触发才做 | 缺规则！ |

**链路上的所有错误都指向同一个 gap**：缺少「写 plan 之前先做最佳实践核验」的强制规则。

### 4.4 vps_manager 当初为什么会被实现成反范式？

虽然这是另一个 session 干的（不是当前 session），但合理推测：
- 任务被框定成 "需要一个 CLI 来管理 VPS 生命周期"
- 没人问 "这个 CLI 应该是 Ansible 范式的（直接 playbook + inventory）还是包装范式的（subprocess + 自定义 state）？"
- 选择了"包装范式"是因为它**看起来更可控**（输入 task 文件、输出明确状态）
- 但这本质是用 Python 重新实现了 Ansible 已有的能力（forks / inventory / events）

这恰恰是 **anti-pattern**：用包装层屏蔽下层工具的原生能力。

## 5. 发现

### 5.1 核心 finding：governance 有 2 个具体盲区

**盲区 A — 缺「框架最佳实践前置核验」规则**

现有规则都假设 "你选的方向是对的，只是要把细节做对"。但当方向本身错误时：
- W-R1 (plan-first) 会让你**很优雅地**写出一份方向错误的 plan
- §3 Evidence-based Verification 会让你**很严谨地**测试一份反范式的实现
- W-R5 (cost up-front) 会让你**很负责任地**估算反范式实施的成本

**这些规则都不会阻止"方向错"。** 必须有一条规则强制问"方向对吗？"

**盲区 B — `feedback_pre_accept_verification` scope 太窄**

当前规则覆盖：「接受外部 agent / Gemini / review 的发现时核验」。
不覆盖：
- 自己写 plan 时引用「上一轮自己的 IVG」—— IVG 也可能基于错误前提
- 自己起设计时引用「项目内某个已有实现」—— 已有实现可能反范式
- 用户说「先做 X」时 —— user 的话也可能是基于不完整信息的需求陈述

### 5.2 反思：为什么 user 反复强调最佳实践仍未生效？

- `feedback_dev_stage_pragmatism` 引用了 user 原话「关键是方案是否符合涉及到的技术面的最佳实践」
- 但这条 memory 的 "How to apply" 主要讲「砍过度设计 / 接口要干净」，没具体到「主动核验是否符合最佳实践」
- 结果是 user 的核心强调被**收纳进 memory 但应用方向偏了**

这是另一个层面的 governance gap：**记下了 user 的强调，但没把它转化成可执行的检查步骤**。

## 6. 结论与建议

### 6.1 总判决

- vps_manager 反范式实现 + 我提议错位 batching plan，都是同一个 governance gap 的产物：**缺少「最佳实践前置核验」规则**
- 现有 14 条 W-R 全都在 "执行严谨性" 层，**没有任何一条**在 "方向正确性" 层
- 单纯重新设计 vps_manager 不够——如果不补 governance，下次设计仍会出错

### 6.2 governance 修订建议（必须本 round 落地）

**修订 1：workspace CLAUDE.md 新增 W-R18「框架最佳实践前置核验」**

```markdown
- **W-R18 (2026-05-16)** —— 框架/工具最佳实践前置核验。任何「新功能 plan」或「在已有实现上加功能」的工作开始前，必须先做一次「方向是否正确」核验：
  - (a) 该方案使用的工具/框架（Ansible / Docker / Python stdlib / ...），有没有原生功能/官方推荐方式覆盖同一需求？默认应当 grep 项目内已有用法 + WebSearch 官方文档 + 看上游/参考项目实际做法。
  - (b) 如果是「在已有实现上加功能」：先核验已有实现本身是否符合所用工具的最佳实践。如果已有实现已经反范式，加层只会让债务更深——优先修底座而非加补丁。
  - (c) 这一步产出**必须落到 plan §0 的 Pre-execution Checklist 里**（具体到「核验了哪些来源、结论是什么」），不能默认跳过。
  - **Why**: user 2026-05-16 — 「我之前反复强调过以最佳实践为基础来实现，但是还是出现了这种情况」。具体事件：vps_manager 单 commit 引入时无 IVG → 反 Ansible 范式实现（per-task subprocess + 自写 callback + 自定义 inventory state）；2026-05-16 我接到 batching 需求时直接设计补丁，未质疑根基；user 二次质询触发 IVG-MULTI-SERVER-ANSIBLE-PRACTICE 才发现整套方向错位。
  - **How to apply**: 写 plan 前先写 IVG（或在 plan §0 内嵌简短核验段）；plan 里如有「复用既有 X」「在 Y 之上加 Z」措辞，必须有一行核验 X / Y 本身是否符合最佳实践；这条规则在 [[pre-accept-verification]] 之上：那条针对接受外部输入时，这条针对**自己起设计时**。
```

**修订 2：扩展 `feedback_pre_accept_verification` 的 scope**

加一条新的触发场景：
- 「在已有实现之上加功能时」—— 必须先核验已有实现本身是否符合最佳实践，否则可能在反范式之上加层

**修订 3：ansispire CLAUDE.md §0 协议加一条 best-practice check**

```markdown
- **Best-Practice Pre-Check**: Before any [L2] or [L1.5] task, AI MUST explicitly answer "does this approach match the native pattern of the tool/framework involved?" with evidence (grep / WebSearch / upstream reference). Skipping this step is forbidden — record the check in plan §0 or in an IVG.
```

### 6.3 经验教训

- **「方向核验」不是「细节核验」的子集**——前者是 "should I"，后者是 "how to"。两者要分开规则。
- **「user 的反复强调」必须转化成「具体的检查步骤」**，否则只是被收纳但不被执行。
- **plan-first 是必要但不充分**——plan 本身也可以方向错。补一层 "IVG-before-plan when L2+" 才完整。
- **"在已有实现上加功能"是高风险触发点**——已有实现可能就是反范式，加层会让回归更难。这一类工作必须先核验底座。

### 6.4 vps_manager 重新设计的前置条件

- **不要立刻起新 plan**。先把 §6.2 三项 governance 修订落地。
- 落地后再起 `feat-vps-manager-rewrite` 分支（与 dev 同级），按 IVG-MULTI-SERVER-ANSIBLE-PRACTICE §6.2 路径 Y 重设。
- 重设 plan 必须以 IVG-MULTI-SERVER-ANSIBLE-PRACTICE + 本 IVG 为前置依据，plan §0 包含完整的 best-practice check 段。

## 7. 关联验证
- **TSVS 引用**: N/A（governance 反思）
- **验证结果**: 落地修订 1/2/3 后，下次类似场景应触发前置核验；具体可在 next L2 task 上观察是否生效

---
*Generated by Ansispire Investigation Engine — reflection on why governance failed to catch vps_manager's anti-pattern implementation.*
