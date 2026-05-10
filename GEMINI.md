# GEMINI.md — 项目治理与执行总纲

本文件是 Ansispire 项目的最高执行契约。

## 0. AI 行为协议 (The Peer Rule)
- **主动挑战**：AI 严禁盲目执行指令。任何修改必须先进行影响分析（Impact Analysis）。
- **交付门禁 (Delivery Gate)**：任何修改在向用户交付前，必须经过 100% 全链路验证。
- **一致性保护**：任务关闭前必须确认：1. ARCHITECTURE.md 已更新；2. README.md 已更新；3. 验证经验已整理入对应的 operations.md（最终参考手册）。

## 1. 验证与知识沉淀 (Testing & Codification)
- **强制规程**：执行验证阶段时，必须强制遵循 `docs/TESTING_GOVERNANCE.md`。
- **消灭“口传知识”**：严禁将复杂的命令序列留在聊天记录中。所有被证实有效的操作路径必须沉淀为功能指南，作为系统的最终参考手册。

## 2. 工程标准 (Engineering Standards)
- **幂等性原则**：严禁使用 `recreate: always` 等暴力手段。必须通过任务状态感知（changed/handler）驱动资源变更。
- **解耦原则**：控制面与执行面物理分离。M2M 集成必须使用 Bearer Token。
- **配置即代码 (IaC)**：所有资源（Project, Template）必须通过剧本拨备，禁止手动 UI 操作。

## 3. 冲突阻断与审计 (Audit Protocol)
- **半径 3 米审计**：发现问题时，必须检查代码库其他位置是否存在类似缺陷。
- **强制 Gate**：提交前必须提供 `make syntax` 和 `ansible-lint` 通过日志。

---
*遵循本准则以确保 Ansispire 项目的工业级稳定性。*
