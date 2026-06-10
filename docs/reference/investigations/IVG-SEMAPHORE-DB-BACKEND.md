# 技术调查报告 (Technical Investigation Report) - Semaphore DB 后端选型：SQLite vs PostgreSQL

## 1. 调查概览 (Overview)
- **调查 ID**: `IVG-SEMAPHORE-DB-BACKEND`
- **关联任务**: Target Architecture Q2（`design-2026-05-26.md §八`）/ TASK-003 Controller HA
- **调查类型**: 可行性研究 / 架构探索
- **目标**: 回答「Semaphore 控制面数据库现在就切 PostgreSQL，还是先用 SQLite、后期再切」——明确两条路径的真实成本差与切换触发条件。

## 2. 背景与问题描述 (Background)
- **初始观察**: `plan-semaphore-first-wiring-2026-06-09.md`（change-file 草案）主张直接切 Postgres，理由是「当前无存量数据，是最干净的切换时机」；但 Q2 已于 2026-06-06 关闭为「暂用 SQLite，Postgres 归口 TASK-003」。两个结论冲突，用户无法判断孰优。
- **影响范围**: `controller/semaphore/docker-compose.yml`（+ preflight / e2e compose）、`config/manifest.yml`、`.env` 链路、运维面（备份 / 凭据 / 启动顺序）。
- **触发条件**: 方案 1 整合（新 plan 并入 phase-a）前需要最终确认 DB 后端，避免把有争议的决策带进关键路径。

## 3. 调查过程 (Investigation Process)

### 3.1 假设 (Hypotheses)
1. 假设 A: 「现在切更干净」成立的前提是**以后切有显著额外成本**（数据迁移困难 / 无官方工具）。
2. 假设 B: SQLite 在 Semaphore 当前版本（v2.18.2）作为运行后端存在已知严重缺陷（锁竞争 / 损坏），会被迫提前切换。
3. 假设 C: 本部署规模（单节点控制面、小规模 fleet、低并发任务）下，SQLite 与 Postgres 无可感知的能力差异。

### 3.2 实验与验证 (Experiments)
- **步骤 1**: 查上游官方文档（dialect 支持、生产建议）与 v2.17 release notes（迁移工具）。
- **观察结果**: 见 §4 证据。假设 A **不成立**——v2.17 起官方内置 `semaphore project export/import` CLI，跨后端迁移有官方路径；唯一不可导出项是 Key Store 密钥。
- **步骤 2**: 检索 GitHub issues 中 SQLite 后端的锁 / 损坏类问题（含 2.18.x）。
- **观察结果**: 未发现 SQLite 作为运行后端的阻塞性 bug；已知问题集中在 *BoltDB→SQLite 迁移工具*（#3828 等），本项目从未使用 BoltDB，不受影响。假设 B **不成立**。
- **步骤 3**: 对照本 repo 实际形态（单容器、`bootstrap.yml` IaC 可重放、audit 证据外置于 relay/sink、fleet-key 模型）评估能力差异。
- **观察结果**: 假设 C **成立**——SQLite 单写者模型在单节点低并发场景下不构成约束；Postgres 的优势（多连接、HA 共享存储）只在 TASK-003 多节点时才被消费。

## 4. 证据与日志 (Evidence & Logs)

**上游事实（官方文档 / release notes）**：
- Semaphore 支持 4 种 dialect：**SQLite（默认）**、PostgreSQL、MySQL、BoltDB（已弃用并移除）。SQLite 是上游的第一公民本地后端，不是边缘选项。
- 社区与上游指引共识：**生产环境推荐 PostgreSQL；测试与小规模部署 SQLite 足够**，并明确支持「先 SQLite 后迁移」路径。
- v2.17（当前 pin v2.18.2 已包含）内置项目级迁移工具：

```bash
semaphore project export --project-name "Demo project" --file /path/to/backup.json
semaphore project import --file /path/to/backup.json
# Docker 场景可用 SEMAPHORE_IMPORT_PROJECT_FILE 环境变量自动导入
```

- **关键限制**：官方确认 backup **不包含 secrets——导出后所有 key 为空**。Key Store 私钥（write-only、AES 加密存库）必须在新实例手工重新录入。
- 2.18.x 已知问题清单中与 SQLite 相关的均为 BoltDB 迁移工具缺陷（如 #3828 `SEMAPHORE_MIGRATE_FROM_BOLTDB` 不生效），无运行态锁 / 损坏报告。

**仓内事实**：
- `config/manifest.yml`: `semaphore_pinned: v2.18.2`（≥2.17，迁移工具可用）。
- `controller/semaphore/docker-compose.yml:31`: `SEMAPHORE_DB_DIALECT: sqlite`，数据在 `semaphore-data` named volume。
- 控制面资源（project / repo / inventory / template / token）全部由 `controller/semaphore/bootstrap.yml` 幂等重放（UI-zero-touch IaC）——DB 内容的可再生性是架构设计目标。
- audit 证据链由 relay 拉取到外部 sink 持久化，**不依赖** Semaphore DB 的 task history。
- static inventory blob 可经 `GET/PUT /inventory/{id}` API 搬运（IVG-SEMAPHORE-INVENTORY-API §8 已实测）。

## 5. 发现与分析 (Findings)

- **核心结论**: 「现在切更干净」的前提不成立。代码面 diff（约 8 个文件：manifest / manifest_sync / .env.example / 主 compose / preflight compose / e2e compose / 两处文档）现在做和以后做完全相同；以后切的*额外*成本仅为一次有界的 re-seed。
- **两条路径成本对比**:

| 维度 | 现在切 Postgres | 先 SQLite，TASK-003 时切 |
|---|---|---|
| 代码 diff | ~8 文件 | 同样 ~8 文件（不变） |
| 数据迁移 | 无 | bootstrap.yml 重放（零成本）+ inventory blob API 搬运（分钟级）+ **Key Store 重录**（fleet-key 模型下 1–2 把）+ Worker template-id 重新 `--var` 部署 ≈ 1–2 小时 operator 手工 |
| 关键路径影响 | 绑进 R1/R2，扩大 review 面、推迟首次真实 onboard | 无 |
| 运维面 | 立即承担：凭据管理、pg_dump 备份、容器启动顺序、健康检查 | 推迟到有值得备份的数据时 |
| 测试 harness | preflight / e2e compose 每次多启动一个 service | 维持现状 |
| 决策一致性 | 需正式推翻已关闭的 Q2 并同步 design / TODO / TASK-003 | 与 Q2 决策一致 |
| 能力收益 | 本阶段无消费者（单节点、低并发） | HA 时点收益与成本同时出现 |

- **风险评估**: 留在 SQLite 的唯一长期注意事项是**不要积累不可再生数据**。当前架构下唯一此类数据是 Key Store 私钥——fleet-key 模型（phase-a R1 Option A）天然把它压到 1–2 把。task history 增长属可丢弃数据（audit 证据外置），必要时可清理。

## 6. 结论与建议 (Conclusion)
- **行动方案**: **维持 Q2 原决策——先 SQLite**。Postgres 切换归口 TASK-003，不进入当前关键路径。
- **切换触发条件**（满足任一即启动 Postgres 迁移）:
  1. TASK-003 多节点 Semaphore / HA 落地（SQLite 文件无法跨节点共享，硬性条件）；
  2. task history / 并发任务量出现可测量的 SQLite 性能瓶颈；
  3. 出现第二个需要直接读写控制面 DB 的组件。
- **届时迁移 runbook 骨架**: 起 postgres service → 翻 `SEMAPHORE_DB_DIALECT` + 连接 env → 空库首启自动建 schema → `bootstrap.yml` 重放（或 `project export/import`）→ Key Store 重录 → inventory blob API 搬运 → Worker 重新部署 template-id vars → 验证 smoke。
- **经验教训**: 「现在没数据所以现在切最便宜」类论断必须先核实**以后切的真实成本**——当迁移有官方工具、且架构本身以 IaC 可重放为设计目标时，「最干净的时机」并不稀缺。

## 7. 关联验证 (Linked Verification)
- **TSVS 引用**: N/A（纯调查，无代码变更）
- **验证结果**: N/A
- **参考来源**:
  - Semaphore v2.17 release notes（export/import CLI）: https://semaphoreui.com/releases/semaphore-v2_17
  - Semaphore 配置文档（dialect / postgres 连接键）: https://semaphoreui.com/docs/administration-guide/configuration/
  - GitHub discussion（backup 不含 secrets）: https://github.com/semaphoreui/semaphore/discussions/847
  - GitHub issue #3828（BoltDB 迁移工具缺陷，确认与运行态 SQLite 无关）: https://github.com/semaphoreui/semaphore/issues/3828
  - 仓内: `config/manifest.yml` · `controller/semaphore/docker-compose.yml` · `controller/semaphore/bootstrap.yml` · `IVG-SEMAPHORE-INVENTORY-API.md §8` · `design-2026-05-26.md §八`
