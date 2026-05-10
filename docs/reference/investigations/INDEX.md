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
*注：新增调查后必须在此索引追加记录。findings 落地后将状态改为 `Applied` 并填写「应用位置」，Agent 见此状态即可跳过深读原文件。*
