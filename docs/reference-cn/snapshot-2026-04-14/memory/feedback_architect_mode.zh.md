---
name: Architect Mode Feedback Rules
description: Six feedback rules distilled from the Round 5→6 conversation about working as an architect not engineer
type: feedback
originSessionId: 6897cc59-eb38-4fd3-90b0-d3a9ccfc5b43
---
从 Round 5→6 会话中提炼的六条工作规则（R1-R6，见 CLAUDE.md 第 7 节）：

1. **方案先行**：方案文档未获用户批准前不得实施
2. **层级区分**：架构层问题不得按工程层做法处理
3. **路线图先批**：3+ 任务的计划须先让用户过目
4. **意图澄清优先**：开始前必须澄清系统类型、边界、NFR
5. **经验沉淀循环**：每轮自检是否有新规则需加入 CLAUDE.md
6. **成本前置**：大型工作评估工作量，大型拆多轮

**Why**: 本次会话中用户通过多次纠正揭示了"工程师思维占主导、架构师思维缺位"的系统性偏差——具体包括把管理控制系统当模板做、14 任务未经路线图层面审核、文档在实施后追加、规则在被提醒后才加入 CLAUDE.md。

**How to apply**:
- 每次新会话开始时，先读 CLAUDE.md 第 1 节预执行检查清单
- 识别到架构层工作，立即切换到"澄清→设计→评审→才执行"流程
- 不允许"意识到问题但不沉淀"——每个纠正都必须变成规则或自检项

更新 MEMORY.md 索引：此文件与 project_real_scope.md 联用，共同矫正工程师默认模式。
