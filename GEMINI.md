# GEMINI.md — Gemini / Cross-Agent Collaboration Notes

本文件不是 Ansispire 的唯一最高规则。
它是给 Gemini 会话使用的补充治理说明，需要与以下内容配合：

- `AGENTS.md` / 嵌套 `AGENTS.md`：任务路由、局部上下文、路径级规则
- `CLAUDE.md`：共享工作流基线（任务分级、Sync Guard、分支生命周期）
- 当前仓库事实：`ARCHITECTURE.md`、`TODO.md`、`docs/governance/*`、feature-map、active review plan、代码

若这些来源互相冲突，优先当前仓库事实与 active plan，而不是本文件本身。

## 1. 上下文与方向控制

- **尊重上下文过滤**：Gemini 会话优先遵守 `.geminiignore`，避免把无关文档、历史产物、临时文件全量塞进上下文。
- **先判断方向，再扩展实现**：如果任务是在现有实现上继续加功能，先验证该实现是否仍符合当前架构方向；若它本身已偏航，不要直接叠补丁。
- **显式落地关键取舍**：L1.5 / L2 工作中的关键取舍，必须写进 plan / IVG / review note，而不是只留在聊天里。

## 2. 交付与知识沉淀

- **验证服从项目测试治理**：非平凡改动完成前，按 `docs/governance/testing-governance.md` 跑对应 surface 的最低必需验证；若没跑，必须明确说明缺口。
- **不要把 docs 变更也硬套成全链路运行测试**：纯文档 / 治理改动应重点核对命令、路径、交叉引用与职责边界，而不是强行补无意义的 runtime gate。
- **消灭“口传知识”**：一旦某条命令序列、排障路径、操作套路被证明有复用价值，就应沉淀到 `docs/operations/`、`docs/governance/` 或对应 feature-map，而不是只留在聊天记录。

## 3. 交叉审计与纠偏

- **发现结构性问题先纠偏，再继续开发**：如果另一套 AI 产出的 plan / IVG / 实现存在结构错误、事实错误或方向错误，不要在其上继续叠加工作。
- **纠偏必须可追溯**：先复现或确认问题，再通过 plan / changelog / review note 修正、归档或替换记录，让后续 agent 能复盘为什么改口径。
- **把 Gemini 用在它擅长的地方**：上下文裁剪、交叉审计、把临时有效经验写回仓库文档；共享规则本身则优先复用 `CLAUDE.md` 与当前 repo truth，而不是在这里重复造一份总纲。

---
*本文件用于补充 Gemini / 多 agent 协作，不替代仓库事实。*
