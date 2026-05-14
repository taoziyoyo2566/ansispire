# 测试规格与验证说明书索引 (TSVS Index)

本文件用于登记 Ansispire 项目所有 **TSVS**（测试规格与验证说明书），让贡献者 / 审计员 / 未来 AI agent 能在一处查到"哪个表面有规格、哪个还没有"。

**状态机**：
- **Active** — 当前在维护，断言意图与代码同步
- **Retired** — 已废弃 / 被替代（保留历史；不再用于覆盖判断）

新增 TSVS 必须在本表追加一行（见 [`testing-governance.md §7`](../../governance/testing-governance.md)）。

---

## 1. TSVS 注册表

| ID | 首次登记 | 表面 | 层级 | Carrier | 状态 | Spec 文件 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `TSVS-MOL-COMMON-001` | 2026-05-11 | `roles/common/` | L4 | `molecule test -s common` | Active | [molecule-common.md](molecule-common.md) |
| `TSVS-MOL-WEBSERVER-001` | 2026-05-11 | `roles/webserver/` | L4 | `molecule test -s webserver` | Active | [molecule-webserver.md](molecule-webserver.md) |
| `TSVS-MOL-DATABASE-001` | 2026-05-11 | `roles/database/` | L4 | `molecule test -s database` | Active | [molecule-database.md](molecule-database.md) |
| `TSVS-MOL-FULLSTACK-001` | 2026-05-11 | 多 role 共存（common + webserver + database） | L4 | `molecule test -s full-stack` | Active | [molecule-full-stack.md](molecule-full-stack.md) |
| `TEST-EDA-001` | 2026-05-09 | `controller/audit/reactor.py` (纯函数) | L1 | `make test-eda-unit` | Active | [eda-reactor-unit.md](eda-reactor-unit.md) |
| `TEST-EDA-002` | 2026-05-09 | `extensions/eda/rules.json` ↔ `bootstrap.yml` 契约 | L2 | `make test-eda-contract` | Active | [eda-rules-contract.md](eda-rules-contract.md) |
| `TEST-EDA-003` | 2026-05-09 | `controller/audit/reactor.py` + mock Semaphore HTTP | L3 | `make test-eda-component` | Active | [eda-reactor-component.md](eda-reactor-component.md) |
| `TEST-EDA-004` | 2026-05-10 | reactor → relay → sink 全链路（disposable e2e） | L5 | `make test-eda-e2e` | Active | [eda-reactor-e2e.md](eda-reactor-e2e.md) |
| `TSVS-EDA-RELAY-UNIT-001` | 2026-05-13 | `controller/audit/relay.py`（cursor/fetch/tick, urllib mocked） | L1 | `make test-eda-relay-unit` | Active | [eda-relay-unit.md](eda-relay-unit.md) |
| `TSVS-EDA-SINK-UNIT-001` | 2026-05-13 | `controller/audit/sink.py`（HTTP handler, socket mocked） | L1 | `make test-eda-sink-unit` | Active | [eda-sink-unit.md](eda-sink-unit.md) |
| `TSVS-FILTERS-UNIT-001` | 2026-05-13 | `filter_plugins/custom_filters.py`（7 个过滤器纯函数） | L1 | `make test-filters` | Active | [filters-unit.md](filters-unit.md) |
| `TSVS-AUDIT-LOOP-001` | 2026-04-27 | Semaphore API → reactor → relay → sink | L5 | `make controller-loop-smoke` | Active | [audit-loopback-functional.md](audit-loopback-functional.md) |
| `TSVS-RBAC-SMOKE-001` | 2026-04-27 | `controller/rbac/`（三角色权限边界） | L5 | `make controller-rbac-smoke` | Active | [rbac-functional-smoke.md](rbac-functional-smoke.md) |

---

## 2. 命名约定

- **新 TSVS** 一律使用 `TSVS-<SCOPE>-<SLUG>-NNN` 格式（与现有 `TSVS-AUDIT-LOOP-001` / `TSVS-RBAC-SMOKE-001` 对齐）。
- 历史的 `TEST-EDA-NNN` 系列保留原 ID 不重命名（迁移成本无收益）；新增 EDA 系列规格使用 `TSVS-EDA-<SLUG>-NNN`。
- `SCOPE` 建议：`MOL`（Molecule 场景）/ `EDA`（事件驱动）/ `AUDIT` / `RBAC` / `INFRA` / `CTRL`（controller）。

---

## 3. 表面覆盖映射

读这一节可以快速回答"我改了 X 表面，有哪些 TSVS 覆盖？"

| 表面 | 覆盖的 TSVS | 是否完整 |
| :--- | :--- | :--- |
| `roles/common/` | `TSVS-MOL-COMMON-001` | ⚠ UFW 规则内容未断言（[`test-plan.md §5 G9`](../../governance/test-plan.md)） |
| `roles/webserver/` | `TSVS-MOL-WEBSERVER-001` | Ubuntu 22 + Debian 12（2026-05-12 G3）；SSL/PHP-FPM 未覆盖 |
| `roles/database/` | `TSVS-MOL-DATABASE-001` | Ubuntu 22 + Debian 12（2026-05-12 G3，Debian 走 MySQL 上游 APT repo）；testuser 实测授权（2026-05-12 T-C3）|
| `roles/ansispire_hub/` | （无） | ✗ 仅 lint + syntax + e2e 间接覆盖（G2） |
| `roles/ansispire_audit/` | `TSVS-AUDIT-LOOP-001`（间接） + EDA L1–L5 | ✅ 良好 |
| `roles/infra_baseline/` | （无） | ✗ 最大盲区（G1） |
| `controller/audit/reactor.py` | `TEST-EDA-001`（L1）+ `TEST-EDA-003`（L3）+ `TEST-EDA-004`（L5） | ✅ 良好 |
| `controller/audit/relay.py` | `TSVS-EDA-RELAY-UNIT-001`（L1）+ `TEST-EDA-004`（L5）+ `TSVS-AUDIT-LOOP-001`（L5） | ✅ 良好（L1+L5；L3 component 视后续是否需要） |
| `controller/audit/sink.py` | `TSVS-EDA-SINK-UNIT-001`（L1）+ `TEST-EDA-004`（L5）+ `TSVS-AUDIT-LOOP-001`（L5） | ✅ 良好（同上） |
| `extensions/eda/rules.json` | `TEST-EDA-002` | ✅ |
| `controller/rbac/` | `TSVS-RBAC-SMOKE-001` | ✅ smoke 级别 |
| `filter_plugins/custom_filters.py` | `TSVS-FILTERS-UNIT-001` | ✅ 100% 行覆盖 |
| `playbooks/site.yml`、`inventory/{stag,prod}/` | （无独立 TSVS） | ⚠ lint + syntax + dry-run 覆盖（暂无 TSVS 必要） |
| 多 role 共存 | `TSVS-MOL-FULLSTACK-001` | ⚠ co-existence 子集；未覆盖跨服务交互 |

---

## 4. 维护流程

- **新 TSVS 落地**：
  1. 在 `docs/reference/test-specs/` 下创建 spec 文件，参考 [`TEMPLATE.md`](TEMPLATE.md)
  2. 在 §1 追加一行（含 ID、首次登记日期、表面、层级、Carrier、状态、链接）
  3. 在 §3 表面覆盖映射中补 / 更新对应行
  4. 同步 [`docs/governance/test-plan.md §2 表面清单`](../../governance/test-plan.md) 的 TSVS 文档列

- **退役 TSVS**：
  1. 不要删除文件；将本表 §1 中状态置为 `Retired`
  2. 在 spec 文件 §1 顶部添加 `> **Retired YYYY-MM-DD** — 原因: ...`
  3. 更新 §3 表面覆盖映射

- **状态迁移记录**：放在本文末尾"变更日志"小节（按时间倒序）

---

## 5. 变更日志

| 日期 | 变更 | 来源 |
| :--- | :--- | :--- |
| 2026-05-11 | 创建 INDEX，登记现有 6 份 + 新增 4 份 Molecule TSVS | feat-testing-strategy round 2（[plan](../../reviews/feat-testing-strategy/plan-2026-05-10.md)）|
| 2026-05-12 | webserver / database / full-stack TSVS 更新：G3 Debian 12 平台 + T-C1 my.cnf 硬断言 + T-C2 root pw 去重 + T-C3 testuser 实测授权 | feat-testing-tier-c round 2（[plan](../../reviews/feat-testing-tier-c/plan-2026-05-12.md)）|
| 2026-05-13 | 新增 3 份 L1 TSVS：`TSVS-EDA-RELAY-UNIT-001` / `TSVS-EDA-SINK-UNIT-001` / `TSVS-FILTERS-UNIT-001`（来自 loopback runner v2 round1 中规范化的 orphan tests）；§3 表面覆盖映射相应更新 | feat-loopback-runner round 2（[plan](../../reviews/feat-loopback-runner/plan-2026-05-13.md)）|

---

*配套测试方针见 [`docs/governance/testing-governance.md`](../../governance/testing-governance.md)，覆盖矩阵与缺口分析见 [`docs/governance/test-plan.md`](../../governance/test-plan.md)。*
