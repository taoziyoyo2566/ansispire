# docs/governance/testing-governance.md — 测试方针 (Testing Strategy)

> 本文回答："**我应该跑什么测试，什么时候，凭什么**"。
> 配套的"**什么被测了 / 什么没被测**"在 [`test-plan.md`](test-plan.md)。
>
> 治理范围：本文是项目的测试**红线**，与 `CLAUDE.md §3 Engineering Standards` 协同生效。

**Quick reference**：`make verify-quick`（commit 前，~3 s）→ `make verify`（push 前，~30–60 s）→ `make verify-full`（release 前 / role 改动，~10–20 min）。决策树详见 §3，闸口语义详见 §5。

---

## 1. 目标与读者

- **读者**：贡献者（写 PR）/ 维护者（跑 verify 与 CI）/ 审计员 / 未来 AI agent（接手项目）
- **目标**：贡献者读完 §3 决策树，30 秒内回答"我改了 X，应该跑什么"
- **不在范围**：
  - 单条测试用例的写法（见 `docs/reference/test-specs/*` TSVS 文档）
  - 性能基准（项目尚未引入）
  - 安全扫描（detect-secrets 由 CI 强制；OpenSCAP 等扩展属未来 workstream）

---

## 2. 测试金字塔

层级定义（自下而上）：

| 层级 | 范围 | 速度 | 现项目载体 |
|---|---|---|---|
| **L0 静态** | 文本规则、语法、密钥扫描 | < 5 s | `yamllint`、`ansible-lint`、`ansible-playbook --syntax-check`、`detect-secrets` |
| **L1 单元** | 纯函数、无 IO | < 1 s | `controller/audit/test_reactor.py`（14 cases） |
| **L2 契约** | 跨配置 / 跨文件一致性 | < 5 s | `controller/audit/test_rules_contract.py`（9 cases，校验 `rules.json` ↔ `bootstrap.yml` template name 对齐） |
| **L3 组件** | 单组件 + mock 外部依赖 | < 10 s | `controller/audit/test_reactor_component.py`（5 cases，reactor → mock Semaphore HTTP） |
| **L4 集成** | 单 / 多 role 部署到容器 | 2–5 min/scenario | Molecule（4 场景：`common` / `webserver` / `database` / `full-stack`） |
| **L5 端到端** | 真实 docker stack，多组件协同 | 1–2 min | `controller/audit/loop-smoke.sh`、`controller/rbac/smoke.sh`、`make test-eda-e2e` |

**关键观察**：L0–L3 是文本/逻辑层，**抓不到**部署期类 bug（防火墙规则、模板渲染产物、systemd 状态、跨配置文件路径）。这类 bug **只能由 L4 浮现** —— 这是 round 5 五个 bug 全部要靠 Molecule 才能发现的结构性原因。

---

## 3. 决策树：什么改动跑什么测试

| 改动了什么 | 必跑 (本地最低) | 应跑 (push 前) | 可跑 (release / 大变更) |
|---|---|---|---|
| `roles/common/**` | `make verify-quick` | `molecule test -s common` | `molecule test -s full-stack` |
| `roles/webserver/**` | `make verify-quick` | `molecule test -s webserver` | `molecule test -s full-stack` |
| `roles/database/**` | `make verify-quick` | `molecule test -s database` | `molecule test -s full-stack` |
| `roles/ansispire_hub/**` | `make verify` | `make controller-loop-smoke` | `make test-eda-e2e` |
| `roles/ansispire_audit/**` | `make verify` (含 test-eda) | `make controller-loop-smoke` | `make test-eda-e2e` |
| `roles/infra_baseline/**` | `make verify` | （无 L4 覆盖，见 `test-plan.md` §5 G1） | — |
| `controller/audit/*.py` | `make test-eda-unit` | `make test-eda` (L1+L2+L3) | `make test-eda-e2e` |
| `extensions/eda/rules.json` | `make test-eda-contract` | `make test-eda` | `make controller-loop-smoke` |
| `controller/rbac/**` | `make controller-rbac-smoke` | `make verify` | — |
| `extensions/eda/rulebooks/**` | `make test-eda-contract` | `make controller-loop-smoke` | `make test-eda-e2e` |
| `playbooks/site.yml` | `make verify` | `make verify-full` | — |
| `inventory/{stag,prod}/**` | `make syntax` | `make verify` | — |
| `Makefile` / `.github/workflows/**` | `make verify` | `make verify-full` (本地)；CI 自验 | — |
| `docs/**` (非 governance) | （无强制） | 视读者人工通读 | — |
| `CLAUDE.md` / `docs/governance/**` | （无强制） | 同步引用本文 §3+§4 | — |

**使用方法**：在改动文件前 grep 路径，命中行就跑对应测试。多文件改动取并集。

---

## 4. 操作模式（Local vs CI）

### 4.1 Local Make 目标

| 目标 | 包含 | 耗时 | 用途 |
|---|---|---|---|
| `make verify-quick` | syntax-check (stag + prod) | ~3 s | commit 前最低门槛、保存点检查 |
| `make verify` | lint + syntax + `test-eda` (L1+L2+L3) + dry-run | ~30–60 s | push / PR 前默认、一般改动闸口 |
| `make verify-full` | `verify` + `molecule-all` (4 场景串行) | ~10–20 min | release 前 / 涉及 role 改动 / 涉及 Make 改动 |
| `make test-eda-e2e` | 真实 docker e2e（约 60–90 s） | ~90 s | 涉及 reactor / 审计链路改动 |
| `make controller-rbac-smoke` | RBAC 三角色权限 smoke | < 30 s | 涉及 rbac 改动 |
| `make controller-loop-smoke` | Semaphore action → relay → sink 回环 | ≤ 20 s | 涉及 audit 链路改动 |

> **不要**自创组合命令。如果发现"我经常需要 `verify` + 单一 molecule 场景"，反映给 maintainer，可能需要新 Make 目标（Tier C 工作）。

### 4.2 CI（`.github/workflows/ci.yml`）

触发：push 至 `dev` / `master` / `hotfix/*`，PR 至 `dev` / `stg` / `master`。

依赖图：

```
yamllint ──┬─→ ansible-lint ──┬─→ dry-run
           └─→ syntax-check ──┴─→ molecule [matrix: common, webserver, database, full-stack 并行]
detect-secrets (独立)
```

**CI 与本地的责任划分**：
- **CI 跑全量**：所有 4 个 molecule 场景并行（matrix）
- **本地跑选择性**：贡献者按 §3 决策树挑场景，避免每次都 `verify-full`
- 本地 `molecule-all` 是**串行**（这是 round 5 痛点之一；Tier C 待并行化）

---

## 5. 质量闸口

| 闸口 | 触发 | 必须通过 | 备注 |
|---|---|---|---|
| **保存点** | 个人本地 commit | `verify-quick` | 不强制，但建议 |
| **Push 前** | `git push` | `verify` | 涉及 role/playbook 改动需追加 `verify-full` |
| **PR 合并前** | CI | yamllint + ansible-lint + syntax + dry-run + molecule(4) + detect-secrets | CI 自动门禁 |
| **Release 前** | 手动 | `verify-full` + 涉及功能的 e2e + 当轮新增 / 改动的 TSVS PASS | maintainer 决策 |

**红线**：CI 失败的 PR **不得合并**。失败原因是真实 bug 还是测试自身坏掉，必须先定性再处置（不得为了合并而临时放宽 lint）。

---

## 6. Molecule 操作模式

L4 测试在两种模式下行为不同，按场景选择：

| 模式 | 命令 | 行为 | 单次耗时 | 用途 |
|---|---|---|---|---|
| **干净验证** | `molecule test -s <X>` | create → converge → verify → destroy | 2–5 min | CI / release / 调试结束的最终确认 |
| **迭代调试** | `molecule converge -s <X>` | 复用现有容器，仅跑 converge | 10–20 s | 改 task 后快速看效果 |
| **手动 verify** | `molecule verify -s <X>` | 仅跑 verify.yml | < 10 s | 调试断言本身 |
| **登入容器** | `molecule login -s <X>` | shell 进入容器 | < 1 s | 现场排错 |

**为什么这两种要分开**：迭代时 destroy/create 占总耗时的 60–80%；converge-only 模式可缩短到 10–20s/iter，把反馈循环压到秒级。完成调试后必须跑一次 `molecule test` 确认在干净环境也成立 —— 否则可能依赖了上一次迭代留下的 side-effect（这就是 round 5 "高频环境重建"痛点的根因，但同时也是必要保护）。

**纪律**：迭代调试期间用 `molecule converge`，最终提交前 `molecule test`。两者**不可互相替代**。

---

## 7. TSVS 强制规约

任何 **功能性测试**（非纯静态校验）的新增 / 重大变更，都必须：

1. 在 `docs/reference/test-specs/` 下产出对应 TSVS 文档，参考 `TEMPLATE.md`
2. 注册至 [`docs/reference/test-specs/INDEX.md`](../reference/test-specs/INDEX.md)
3. 标注：层级（L1–L5）、所属 surface、断言清单、预期结果

**例外**（不需要 TSVS）：
- 纯 lint 规则（在 `.ansible-lint` / `.yamllint` 配置中表达即可）
- 纯 yamllint 规则
- 纯 syntax-check（无独立断言意图）

**触发新增 TSVS 的典型情况**：
- 新增 Molecule 场景
- 新增 controller 子模块的功能测试
- 新增 e2e 链路验证
- 现有 TSVS 的断言数量、预期结果或所属层级**显著变化**

---

## 8. 文档自身维护

| 触发 | 必须同步 |
|---|---|
| `make verify` / `verify-full` 链结构调整 | §4.1 表 + §3 决策树相关行 |
| CI workflow 调整 | §4.2 依赖图 |
| 新 surface（新 role / 新 controller 子模块） | §3 决策树补行 + `test-plan.md` §2 表面清单补行 |
| 测试金字塔层级新增（如 L6 性能） | §2 + `test-plan.md` §3 矩阵 |
| 闸口规则调整 | §5 |
| Molecule 操作模式变更（如新增 batch 模式） | §6 |
| TSVS 模板规约变更 | §7 + `docs/reference/test-specs/TEMPLATE.md` |

**自检节奏**：每一轮 round 收尾时，必须扫一遍本文，与实际 Make / CI 行为对账；发现漂移立即修复或开 Tier C 缺口。

---

*配套测试覆盖现状与缺口分析见 [`test-plan.md`](test-plan.md)。*
*单测试规格与执行记录见 [`docs/reference/test-specs/`](../reference/test-specs/)。*
