# 技术调查报告 — Tool Execution Registry (TER) 架构设计

## 1. 调查概览 (Overview)
- **调查 ID**: `IVG-TOOLENV-REGISTRY`
- **关联任务**: 无（用户主动发起的架构探索）
- **调查类型**: 架构探索 (Architecture Exploration)
- **目标**: 设计一套"命令执行注册表"机制，使 AI Agent 在需要执行工具命令时能够查询本机环境的已知可行方法，消除反复试错的浪费。

---

## 2. 背景与问题描述 (Background)

### 2.1 初始观察
在处理 yamllint CI 问题时，AI 经历了如下试错序列：

```
1. yamllint .             → command not found
2. pip install yamllint   → PEP 668 externally-managed-environment 错误
3. pipx run yamllint      → command not found
4. python3 -m venv /tmp/yamllint-venv && .../yamllint .  → 成功
```

共尝试 4 次才找到正确方法，且每次新对话都会重复同样的试错。

### 2.2 根本原因
AI 的工具调用知识来自训练数据（通用经验），无法感知特定主机的环境约束（本机 Python 被 PEP 668 锁定、系统无 pipx 等）。这种知识是**隐式的、对话内的、不可持久化的**。

### 2.3 影响范围
- 所有需要在本机执行外部命令的场景（lint、测试、格式化工具等）
- 每次新对话都会"失忆"，重新试错
- 试错期间浪费用户等待时间，并产生不必要的错误日志

---

## 3. 设计问题 (Design Questions)

本次探索需要回答以下问题：

1. **存储层级**：注册表文件放在哪一层（全局 / 工作区 / 项目）？
2. **触发时机**：AI 何时去查询注册表？如何避免查询本身增加显著开销？
3. **数据结构**：单个条目应包含哪些字段才能覆盖典型情形？
4. **自更新协议**：AI 通过试错发现新方法后，如何保证写回注册表？
5. **与现有 CLAUDE.md 规则的关系**：是增补还是重构？

---

## 4. 架构分析 (Architecture Analysis)

### 4.1 核心模式：按需查找（Lazy Lookup Registry）

```
AI 要执行命令 X
  ↓
查询 TOOLENV.md 中是否有条目 X
  ├── 有 → 直接按条目执行，跳过试错
  └── 无 → 走常规推断；成功后写回条目
```

**设计原则**：
- **关注点分离**：行为规则（"查注册表"）和执行知识（"怎么跑 yamllint"）分开存储
- **懒加载**：注册表文件只在需要时 Read，不预加载进上下文
- **自增长**：每次成功发现新方法即更新，注册表随使用趋于完备

### 4.2 层级归属

| 层级 | 文件路径 | 内容 |
|---|---|---|
| 用户/主机级 | `~/.claude/TOOLENV.md` | 本机环境通用约束（Python、Docker、系统包等） |
| 工作区级 | `~/workspace/TOOLENV.md` | 跨项目常用工具（yamllint、ansible-lint、molecule 等） |
| 项目级 | `<project>/TOOLENV.md` | 项目特有工具或覆写条目 |

查找优先级：项目 > 工作区 > 用户，与 CLAUDE.md 层级一致。

### 4.3 条目数据结构（草案）

```markdown
## <command-name>

- **环境**：<执行环境描述，如 venv、docker、system 等>
- **前置条件**：<需要事先满足的条件>
- **前置命令**：`<建立环境的命令，如 venv 初始化>`
- **调用模板**：`<实际执行命令的模板，含占位符>`
- **已知失败路径**：<列出不可用的方式及原因>
- **最后验证**：<日期，避免过期信息被沿用>
```

**示例（yamllint）**：

```markdown
## yamllint

- **环境**：Python venv（系统 pip 被 PEP 668 锁定，无 pipx）
- **前置命令**：`python3 -m venv /tmp/yamllint-venv && /tmp/yamllint-venv/bin/pip install yamllint -q`
- **调用模板**：`/tmp/yamllint-venv/bin/yamllint [args]`
- **已知失败路径**：`yamllint`（未安装）、`pip install yamllint`（PEP 668）、`pipx run yamllint`（无 pipx）
- **最后验证**：2026-04-27
```

### 4.4 触发规则（写入 CLAUDE.md 的行为规则）

```
执行任何外部工具命令前：
  1. Read TOOLENV.md（就近层级优先）
  2. 查找对应条目
  3a. 有条目 → 按条目执行
  3b. 无条目 → 试错推断；成功后当轮写回条目（含已知失败路径）
```

### 4.5 与现有规则的关系

| 现有规则 | 关系 |
|---|---|
| W-R12 agent 信息流转通过持久化 artifact | **一致**：注册表是"工具经验"的持久化 artifact |
| §2 Layered Context Governance（懒加载） | **扩展**：现有懒加载针对文档，TER 将其扩展至工具知识 |
| §1-A Pre-Execution Checklist | **增补**：在 checklist 中加"查 TOOLENV"步骤 |

---

## 5. 主要权衡 (Tradeoffs)

### 方案 A：独立注册表文件（推荐）
- **优**：懒加载，不污染日常上下文；命令知识增长快，单独文件易维护；跨会话持久
- **劣**：每次需要额外一次 Read 操作

### 方案 B：嵌入 CLAUDE.md
- **优**：单文件，无额外查找步骤
- **劣**：CLAUDE.md 随工具增加而膨胀，每次全量加载成本高；命令知识和行为规则耦合

**结论**：选方案 A。TOOLENV.md 独立文件，CLAUDE.md 中只写"查注册表"的触发规则。

### 注意事项
- 条目需有"最后验证"时间戳，防止环境变化后沿用过期路径
- `/tmp/` 路径的 venv 在重启后消失，前置命令必须包含幂等的创建步骤
- 自更新协议需在 CLAUDE.md 中明确规定"当轮必须写回"，否则会退化成可选行为

---

## 6. 开放问题 (Open Questions)

| # | 问题 | 优先级 |
|---|---|---|
| OQ-1 | `~/workspace/TOOLENV.md` 还是 `~/.claude/TOOLENV.md` 作为主注册表？后者跨所有项目但不在 git 里 | 高 |
| OQ-2 | 条目过期策略：多长时间或什么事件触发重验证？ | 中 |
| OQ-3 | 自更新协议的具体触发词：changelog 机制还是 CLAUDE.md 行内规则？ | 中 |
| OQ-4 | 是否需要"失败条目"（记录已知不可用的路径）防止 AI 重复尝试明确失败的方式？ | 低 |

---

## 7. 下一步行动 (Next Steps)

若决定落地此架构，需完成：

1. **解决 OQ-1**：确定注册表层级归属
2. **起草 TOOLENV.md 格式规范**（条目模板定稿）
3. **写入 yamllint 首个真实条目**（已有完整数据）
4. **修改 CLAUDE.md**（工作区级或用户级）加入触发规则和自更新协议
5. **验证**：新对话中执行 yamllint，确认第一次即命中条目、无试错

---

## 8. 参考与关联 (References)

- 触发本调查的对话：2026-04-27 yamllint CI 修复过程
- 设计原则来源：W-R12（`~/workspace/CLAUDE.md §8`）、§2 Layered Context Governance
- 类似模式：Service Locator Pattern、Operations Runbook、Ansible role defaults

---

*Generated: 2026-04-27 | Status: Active | 应用位置: —*
