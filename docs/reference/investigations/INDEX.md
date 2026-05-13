# 调查报告索引 (Investigation Index)

本文件用于记录所有技术调查的摘要，便于 Agent 快速检索并实现"懒加载"。**状态为 `Applied` 时，「应用位置」列指向已落地规则的文档节，无需深读原 IVG。**

| ID | 日期 | 子系统 | 调查类型 | 核心结论 (Abstract) | 状态 | 应用位置 | 关联文档 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| IVG-TEMPLATE | 2026-04-27 | N/A | Template | 调查报告标准模板 | Active | — | [Link](./TEMPLATE.md) |
| IVG-TASK-CLAUDE-SYNC | 2026-04-27 | AI-Governance | Sync | 同步 Gemini 规则至 Claude 最佳实践（降级为设计笔记） | Archived | — | [Link](../../reviews/feat-governance-integration/design-note-claude-sync.md) |
| IVG-TOOLENV-REGISTRY | 2026-04-27 | AI-Governance | 架构探索 | 命令执行注册表（TER）：将 AI 工具调用经验外化为可持久化查找表，消除跨会话试错；含层级设计、条目结构草案、开放问题 | Active | — | [Link](./IVG-TOOLENV-REGISTRY.md) |
| LESSONS-MIGRATED | 2026-05-10 | Multi | Consolidation | Former SUMMARY.md §4 operational truths consolidated into a single governance doc (Python 3.9+ baseline, env sensing, var precedence, molecule plugin isolation, image deps, RHEL tier, etc.) | Applied | [docs/governance/operational-truths.md](../../governance/operational-truths.md) | [refactor-docs-enterprise plan](../../reviews/refactor-docs-enterprise/plan-2026-05-10.md) |
| VENDOR-PATCHES-MIGRATED | 2026-05-10 | Vendor-roles | Consolidation | Former SUMMARY.md §5 vendor patch obligations (geerlingguy.docker FQCN/octal patches) moved to dedicated governance doc with re-apply protocol | Applied | [docs/governance/vendor-patches.md](../../governance/vendor-patches.md) | [refactor-docs-enterprise plan](../../reviews/refactor-docs-enterprise/plan-2026-05-10.md) |

---

## Investigation Protocol（路径 / 命名 / 流程契约）

任何 RCA / 可行性研究 / 性能调查 / 架构探索都遵循以下契约（之前以分散形式存在于 `CLAUDE.md`，2026-05-11 起统一收纳到此处）：

1. **文件位置 / 命名**：`docs/reference/investigations/IVG-<TASK_ID>-<SLUG>.md`
   - `<TASK_ID>` 为关联任务编号或主题标识（`TASK-001` / `TOOLENV-REGISTRY` …）
   - `<SLUG>` 为 kebab-case 简称，可省略
2. **必须使用模板**：每份 IVG 必须基于 [`TEMPLATE.md`](./TEMPLATE.md) 起草，覆盖 §1–§7 字段（概览 / 背景 / 假设与实验 / 证据 / 发现 / 结论 / 关联验证）
3. **必须登记**：新增 IVG 后在本表追加一行（不登记 = 不存在 → 未来 agent 找不到）
4. **Findings 落地后改 `Applied`**：当结论被吸收进 `CLAUDE.md` / `ARCHITECTURE.md` / `docs/governance/*` / 代码注释等，把状态改为 `Applied` 并在「应用位置」列填入指向规则落点的链接，让未来 agent 可以跳过深读
5. **长流程文档**：完整 L1.5 工作流见 [`docs/governance/ai-workflow.md §1`](../../governance/ai-workflow.md)


