# 测试规格与验证说明书 (TSVS) — EDA Rules Contract Test (L2)

## 1. 测试概览 (Overview)
- **测试 ID**: `TEST-EDA-002`
- **层级**: L2 — 数据契约测，无 HTTP、无 docker
- **测试类型**: 数据契约 / 静态一致性
- **优先级**: 高
- **测试目的**: 在 PR/CI 阶段拦截 `extensions/eda/rules.json` 与 `controller/semaphore/bootstrap.yml` 之间的契约漂移。本层是上一轮 Gemini 重构能"通过"但实际坏掉的根因防御网。
- **核心断言**: 每个 rule 引用的 `template_name` **必须** 在 bootstrap 注册的 remediation templates 列表中存在；否则规则触发时 reactor 会拿到 "could not resolve template" 错误。
- **不在范围**: reactor 行为 (→ L1)；出站 HTTP (→ L3)；端到端 (→ L4)。

## 2. 测试环境 (Environment)
- Python: 3.10+
- 第三方: PyYAML (来自项目 .venv，由 ansible 间接安装)

## 3. 软件包清单 (Software Stack)
| 软件 | 版本 | 来源 |
|---|---|---|
| Python | 3.10+ | venv |
| PyYAML | ≥6.0 | .venv (ansible 依赖链) |
| unittest | stdlib | |
| json | stdlib | |

## 4. 测试方法与步骤 (Methodology)

### 4.1 前置条件
- `extensions/eda/rules.json` 与 `controller/semaphore/bootstrap.yml` 均存在
- bootstrap.yml 中 `Register remediation templates` task 的 loop 列表是契约登记点

### 4.2 执行步骤
```bash
.venv/bin/python3 controller/audit/test_rules_contract.py
# 或经 Make wrapper:
make test-eda-contract
```

### 4.3 用例清单

| # | 用例 | 验证点 |
|---|---|---|
| C1 | rules.json 是合法 JSON | 解析不抛异常；顶层是 dict 含 `rules` 列表 |
| C2 | 每条 rule 含 name / condition / actions | 结构完整 |
| C3 | rule 名字全局唯一 | 防止重名导致 cooldown / 日志混淆 |
| C4 | 每个 semaphore_api action 含 template_name 与 project_name | 动态解析所需 |
| C5 | bootstrap.yml 是合法 YAML | 解析不抛异常 |
| C6 | bootstrap.yml 中能定位 `Register remediation templates` task | 契约登记点存在 |
| C7 | rules.json 引用的所有 template_name 都在 bootstrap 的 loop 列表里 | 核心契约 |
| C8 | bootstrap.yml 中所有 remediation template name 唯一 | 防止 idempotent 注册歧义 |
| C9 | rules.json 的 condition 字段（去 _contains 后缀）∈ events.schema.json 的 payload.event.properties | rules ↔ schema 对齐，防止匹配未声明字段 |

## 5. 预期结果 (Expected Results)
```
Ran 9 tests in <0.5s

OK
```
- 全部 9 个用例 PASS
- 当前 rules.json 引用 `Auto Remediation: Disk Cleanup` 与 `Auto Remediation: DB Failover`，bootstrap loop 注册同名两条 → C7 通过
- exit code 0

## 6. 测试执行记录 (Actual Results)
- **执行时间**: 2026-05-09 round2 → round3 (C9 added)
- **执行人**: Claude (`feat/eda-advanced-healing` Phase 2 + Phase 3 增量)
- **状态**: PASS

```
$ .venv/bin/python3 controller/audit/test_rules_contract.py
.........
----------------------------------------------------------------------
Ran 9 tests in 0.067s

OK
```

差异分析: 无；预期与实际一致。

## 7. 结论与建议 (Conclusion)
- C7 (核心契约) 通过：rules.json 引用的 `Auto Remediation: Disk Cleanup` 与 `Auto Remediation: DB Failover` 均在 bootstrap.yml 的 loop 列表中注册。
- 此层若未来被破坏（rules.json 改名、bootstrap.yml 删/改 template loop），会在 PR 阶段直接 fail，配合 `make verify` 的 gating 见 P2.5。
- 上一轮 Gemini 158 行 bootstrap 重写中两个 template 的 name 也巧合一致（属运气而非纪律）；此层把"运气"提升为可验证的"约束"。

## 8. 演化预案
- ~~Phase 3 加 `extensions/eda/events.schema.json` 后，本规格追加 C9~~ — **已落地（round 3）**。
- 引入 webhook action / shell action 后，contract 校验扩展到这些 action 类型的必填项。
- 当 rules.json 引入新 operator (例如 `_regex`)，C9 的 strip 逻辑要扩展（目前只剥离 `_contains` 后缀）。
