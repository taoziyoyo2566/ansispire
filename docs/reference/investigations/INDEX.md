# 调查报告索引 (Investigation Index)

本文件用于记录所有技术调查的摘要，便于 Agent 快速检索并实现"懒加载"。**状态为 `Applied` 时，「应用位置」列指向已落地规则的文档节，无需深读原 IVG。**

| ID | 日期 | 子系统 | 调查类型 | 核心结论 (Abstract) | 状态 | 应用位置 | 关联文档 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| IVG-TEMPLATE | 2026-04-27 | N/A | Template | 调查报告标准模板 | Active | — | [Link](./TEMPLATE.md) |
| IVG-TASK-CLAUDE-SYNC | 2026-04-27 | AI-Governance | Sync | 同步 Gemini 规则至 Claude 最佳实践（降级为设计笔记） | Archived | — | [Link](../../reviews/feat-governance-integration/design-note-claude-sync.md) |
| IVG-TOOLENV-REGISTRY | 2026-04-27 | AI-Governance | 架构探索 | 命令执行注册表（TER）：将 AI 工具调用经验外化为可持久化查找表，消除跨会话试错；含层级设计、条目结构草案、开放问题 | Active | — | [Link](./IVG-TOOLENV-REGISTRY.md) |
| LESSONS-MIGRATED | 2026-05-10 | Multi | Consolidation | Former SUMMARY.md §4 operational truths consolidated into a single governance doc (Python 3.9+ baseline, env sensing, var precedence, molecule plugin isolation, image deps, RHEL tier, etc.) | Applied | [docs/governance/operational-truths.md](../../governance/operational-truths.md) | [refactor-docs-enterprise plan](../../reviews/refactor-docs-enterprise/plan-2026-05-10.md) |
| VENDOR-PATCHES-MIGRATED | 2026-05-10 | Vendor-roles | Consolidation | Former SUMMARY.md §5 vendor patch obligations (geerlingguy.docker FQCN/octal patches) moved to dedicated governance doc with re-apply protocol | Applied | [docs/governance/vendor-patches.md](../../governance/vendor-patches.md) | [refactor-docs-enterprise plan](../../reviews/refactor-docs-enterprise/plan-2026-05-10.md) |
| IVG-REALITY-OPS-VERIFICATION | 2026-05-15 | Reality-Ops 迁移 | 可行性研究 / 同行复核 | 复核 Gemini 关于 taoziyoyo2566/reality-ops@feat/tag-acl-routing 的迁移方案：5/13 条断言错误或严重不足，4 份 Gemini 产物已丢弃；上游 29 份公开明文 X25519 私钥是先于迁移必须处理的安全清算项；给出修订后的 6 阶段迁移路径 | Active | — | [Link](./IVG-REALITY-OPS-VERIFICATION.md)（plan: [feat-reality-migration](../../reviews/feat-reality-migration/plan-2026-05-15.md)） |
| IVG-DEEP-AUDIT | 2026-05-15 | Reality 迁移 + 项目框架 | 架构审计 / 自审 | 用 pre-accept-verification 规范重审 plan-2026-05-15 + Ansispire 框架：发现 4 处 plan bug（encrypt_string 缺 --encrypt-vault-id、acl_matrix 目标路径、CI 缺 reality 测试、缺 runtime/logs 目录约定）+ 5 项继承风险（Audit Plane 集成缺失、EE 缺 cryptography、Vault 位置 SSOT 不明、feature-map sync 规则不含 plugins/、测试 sys.path hack） | Active | — | [Link](./IVG-DEEP-AUDIT-2026-05-15.md) |
| IVG-VPS-BATCH-PARALLEL | 2026-05-16 | vps-manager | 架构探索 | 针对 `vps_manager` 插件设计基于 Ansible 原生并发（forks）的批量处理方案，通过 Action Batching、动态 Inventory 及自定义 Callback 实现多实例并行部署与精确状态回放。**已被 IVG-MULTI-SERVER-ANSIBLE-PRACTICE 反转**——方案基于错位症状而非根本病因，建议作废 | Superseded | — | [Link](./IVG-VPS-BATCH-PARALLEL.md) |
| IVG-MULTI-SERVER-ANSIBLE-PRACTICE | 2026-05-16 | vps-manager + Ansible | 可行性研究 / 同行复核 | 调查 Ansible 多服务器最佳实践后反转 plan-2026-05-16：vps_manager 有 3 层反范式（per-task subprocess、stdout 解析、vps_inventory.yml 二义性），Action Batching 是错位补丁。正确方向是 ansible-runner 替代 subprocess + 同 action 聚合（路径 Y，推荐）；备选 X 最小修 / Z 大重构。reality-ops 上游 + AWX 实证 Ansible 范式应为「静态 inventory + forks=20 + 一次 playbook 跑整组 host」 | Active | — | [Link](./IVG-MULTI-SERVER-ANSIBLE-PRACTICE.md) |
| IVG-REFLECT-BESTPRACTICE-GAP | 2026-05-16 | Governance / Process | 元层反思 / governance audit | 反思为什么 vps_manager 反范式实现 + plan-2026-05-16 错位补丁没被现有 governance 拦住。发现 2 个具体盲区：(A) 14 条 W-R 全在「执行严谨性」层，无一条管「方向正确性」；(B) pre-accept-verification scope 只覆盖「外部 review」不覆盖「在已有实现上加功能」。修订落地：workspace W-R18 新增「framework best-practice pre-check」+ ansispire CLAUDE.md §0 加 Best-Practice Pre-Check + memory pre-accept-verification 扩展 scope | Applied | [workspace W-R18](../../../../CLAUDE.md) + [ansispire CLAUDE.md §0](../../../CLAUDE.md) | [Link](./IVG-REFLECT-BESTPRACTICE-GAP.md) |
| IVG-SEMAPHORE-CROSS-COMPARE | 2026-05-17 | Control-plane + Audit | 架构探索 + 交叉验证 | 独立审计 ansispire vs upstream semaphore v2.18，5 条 Codex 发现全部独立确认，另独立发现 8 条工程项 + 1 条 Vault Pro 修正；分 Tier 1/2/3 建议未实施 | Active | — | [Link](./IVG-SEMAPHORE-CROSS-COMPARE.md) |
| IVG-EDA-RULEBOOK-MIGRATION | 2026-05-18 | Audit / Reaction-plane | 架构探索 / 可行性 | 评估自研 reactor (235 行) vs upstream `ansible-rulebook` (Apache-2.0 v1.3.0)；功能等价但运行时 ×5-8 (JVM)、镜像 ×4-5、当前 2 条规则不构成迁移收益；推荐**暂不迁移**，记录 4 项触发条件清单 | Active | — | [Link](./IVG-EDA-RULEBOOK-MIGRATION.md) |
| IVG-EXECUTION-PLANE-RUNNER | 2026-05-18 | Control + Data-plane | 架构探索 / 可行性 | 评估引入 Semaphore OSS Runner 拆分 controller/executor；OSS 完全支持基础 Runner（tag-routing 是 Pro，不可吸收）；当前 1 job/min + 0 真实 fleet 节点不构成拆分收益；推荐**暂不引入**，记录 5 项触发条件 + 6-Gate 落地路径草案 | Active | — | [Link](./IVG-EXECUTION-PLANE-RUNNER.md) |

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


