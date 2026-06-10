# 调查报告索引 (Investigation Index)

本文件用于记录所有技术调查的摘要，便于 Agent 快速检索并实现"懒加载"。**状态为 `Applied` 时，「应用位置」列指向已落地规则的文档节，无需深读原 IVG。**

| ID | 日期 | 子系统 | 调查类型 | 核心结论 (Abstract) | 状态 | 应用位置 | 关联文档 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| IVG-TEMPLATE | 2026-04-27 | N/A | Template | 调查报告标准模板 | Active | — | [Link](./TEMPLATE.md) |
| IVG-TASK-CLAUDE-SYNC | 2026-04-27 | AI-Governance | Sync | 同步 Gemini 规则至 Claude 最佳实践（降级为设计笔记） | Archived | — | [Link](../../reviews/feat-governance-integration/design-note-claude-sync.md) |
| IVG-TOOLENV-REGISTRY | 2026-04-27 / implemented 2026-06-10 | AI-Governance | 架构探索 | 命令执行注册表（TER）：将 AI 工具调用经验外化为可持久化查找表，消除跨会话试错；2026-06-10 以 per-host + timestamp 形态落地（`scripts/env_probe.sh` → `.agents/env/<host>.yml`） | Applied | [.agents/rules/environment-truth.md](../../../.agents/rules/environment-truth.md) | [Link](./IVG-TOOLENV-REGISTRY.md) |
| LESSONS-MIGRATED | 2026-05-10 | Multi | Consolidation | Former SUMMARY.md §4 operational truths consolidated into a single governance doc (Python 3.9+ baseline, env sensing, var precedence, molecule plugin isolation, image deps, RHEL tier, etc.) | Applied | [docs/governance/operational-truths.md](../../governance/operational-truths.md) | [refactor-docs-enterprise plan](../../reviews/refactor-docs-enterprise/plan-2026-05-10.md) |
| VENDOR-PATCHES-MIGRATED | 2026-05-10 | Vendor-roles | Consolidation | Former SUMMARY.md §5 vendor patch obligations (geerlingguy.docker FQCN/octal patches) moved to dedicated governance doc with re-apply protocol | Applied | [docs/governance/vendor-patches.md](../../governance/vendor-patches.md) | [refactor-docs-enterprise plan](../../reviews/refactor-docs-enterprise/plan-2026-05-10.md) |
| IVG-SEMAPHORE-CROSS-COMPARE | 2026-05-17 | Control-plane + Audit | 架构探索 + 交叉验证 | 独立审计 ansispire vs upstream semaphore v2.18，5 条 Codex 发现全部独立确认，另独立发现 8 条工程项 + 1 条 Vault Pro 修正；分 Tier 1/2/3 建议未实施 | Active | — | [Link](./IVG-SEMAPHORE-CROSS-COMPARE.md) |
| IVG-EDA-RULEBOOK-MIGRATION | 2026-05-18 | Audit / Reaction-plane | 架构探索 / 可行性 | 评估自研 reactor (235 行) vs upstream `ansible-rulebook` (Apache-2.0 v1.3.0)；功能等价但运行时 ×5-8 (JVM)、镜像 ×4-5、当前 2 条规则不构成迁移收益；推荐**暂不迁移**，记录 4 项触发条件清单 | Active | — | [Link](./IVG-EDA-RULEBOOK-MIGRATION.md) |
| IVG-EXECUTION-PLANE-RUNNER | 2026-05-18 | Control + Data-plane | 架构探索 / 可行性 | 评估引入 Semaphore OSS Runner 拆分 controller/executor；OSS 完全支持基础 Runner（tag-routing 是 Pro，不可吸收）；当前 1 job/min + 0 真实 fleet 节点不构成拆分收益；推荐**暂不引入**，记录 5 项触发条件 + 6-Gate 落地路径草案 | Active | — | [Link](./IVG-EXECUTION-PLANE-RUNNER.md) |
| IVG-SEMAPHORE-INVENTORY-API | 2026-06-03 / runtime addendum 2026-06-06 | Control-plane / VPS lifecycle | API 契约调查 / 架构探索 | 核清 `feat/target-architecture` 的 Semaphore Inventory / Task API 方向：当前 repo 仍是 `file` inventory；runtime probe 已确认 `static` whole-blob CRUD；task payload 使用 task-level `environment` JSON string 承载嵌套 `vps_task`，不依赖 raw `extra_vars` | Active | — | [Link](./IVG-SEMAPHORE-INVENTORY-API.md) |
| IVG-SEMAPHORE-DB-BACKEND | 2026-06-10 | Control-plane | 可行性研究 / 架构探索 | SQLite vs Postgres：代码 diff 不随时间变化；v2.17+ 官方 export/import 工具存在但 backup 不含 secrets（Key Store 需重录，fleet-key 下 1–2 把）；2.18.x 无 SQLite 运行态阻塞 bug；结论**维持 Q2：先 SQLite**，Postgres 归口 TASK-003，3 项切换触发条件 + 迁移 runbook 骨架已记录 | Applied | [design-2026-05-26.md §八](../../reviews/feat-target-architecture/design-2026-05-26.md) | [Link](./IVG-SEMAPHORE-DB-BACKEND.md) |

---

## Investigation Protocol（路径 / 命名 / 流程契约）

任何 RCA / 可行性研究 / 性能调查 / 架构探索都遵循以下契约（之前以分散形式存在于 `CLAUDE.md`，2026-05-11 起统一收纳到此处）：

1. **文件位置 / 命名**：`docs/reference/investigations/IVG-<SCOPE>-<SLUG>.md`（规则详见 [`.agents/rules/file-naming.md`](../../../.agents/rules/file-naming.md)）
   - `<SCOPE>` 为大写域标签（`SEMAPHORE` / `EDA` / `RUNNER` …）
   - `<SLUG>` 为大写简称（`INVENTORY-API` / `RULEBOOK-MIGRATION` …）
2. **必须使用模板**：每份 IVG 必须基于 [`TEMPLATE.md`](./TEMPLATE.md) 起草，覆盖 §1–§7 字段（概览 / 背景 / 假设与实验 / 证据 / 发现 / 结论 / 关联验证）
3. **必须登记**：新增 IVG 后在本表追加一行（不登记 = 不存在 → 未来 agent 找不到）
4. **Findings 落地后改 `Applied`**：当结论被吸收进 `CLAUDE.md` / `ARCHITECTURE.md` / `docs/governance/*` / 代码注释等，把状态改为 `Applied` 并在「应用位置」列填入指向规则落点的链接，让未来 agent 可以跳过深读
5. **长流程文档**：完整 L1.5 工作流见 [`docs/governance/ai-workflow.md §1`](../../governance/ai-workflow.md)
