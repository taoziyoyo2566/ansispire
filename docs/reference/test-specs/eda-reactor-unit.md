# 测试规格与验证说明书 (TSVS) — EDA Reactor L1 Unit Test

## 1. 测试概览 (Overview)
- **测试 ID**: `TEST-EDA-001`
- **层级**: L1 — 纯 Python 单测，无 HTTP，无 docker
- **测试类型**: 功能单元测试
- **优先级**: 高
- **测试目的**: 验证 reactor.py 内部纯函数行为：`match_rule` 的精确/包含/混合/缺字段匹配、cooldown 窗口控制、`process_event` 的分发路径与异常吞吐。
- **不在范围**: 出站 HTTP 请求契约 (→ TEST-EDA-003 L3)；rules.json 与 bootstrap.yml 一致性 (→ TEST-EDA-002 L2)；端到端编排 (→ Phase 3 L4)。

## 2. 测试环境 (Environment)
- 操作系统: Linux 任意版本
- Python: 3.10+ (stdlib only — 无第三方依赖)

## 3. 软件包清单 (Software Stack)
| 软件 | 版本 | 备注 |
|---|---|---|
| Python | 3.10+ | stdlib only |
| unittest | stdlib | |
| unittest.mock | stdlib | patch time.time / trigger_semaphore_task |

## 4. 测试方法与步骤 (Methodology)

### 4.1 前置条件
- `controller/audit/reactor.py` 为 v2.3 (Bearer token + dynamic resolution + cooldown)

### 4.2 执行步骤
```bash
python3 controller/audit/test_reactor.py
# 或经 Make wrapper:
make test-eda-unit
```

### 4.3 用例清单（14 cases）

| # | 用例 | 验证点 |
|---|---|---|
| TestMatchRule.test_exact_match | 全部条件精确相等 → 命中 | exact 匹配 |
| TestMatchRule.test_exact_mismatch | 一个字段值不同 → 不命中 | exact 否决 |
| TestMatchRule.test_contains_match | description_contains 子串存在 → 命中 | _contains 子串 |
| TestMatchRule.test_contains_mismatch | description_contains 子串不存在 → 不命中 | _contains 否决 |
| TestMatchRule.test_contains_missing_field | _contains 引用的字段在事件里没有 → 不命中 | str(None) 处理 |
| TestMatchRule.test_mixed_exact_and_contains | exact + _contains 共存，全满足才命中；任一不满足都不命中 | 多条件 AND |
| TestMatchRule.test_no_event_envelope | 事件没有 payload.event 子键 → 不命中 | 守护 |
| TestMatchRule.test_cooldown_blocks_within_window | 5s < 10s cooldown → 不命中 | 冷却阻挡 |
| TestMatchRule.test_cooldown_releases_after_window | 11s > 10s cooldown → 命中 | 冷却释放 |
| TestMatchRule.test_disabled_rule_never_matches | `enabled: false` 短路；缺省 enabled 视为 true | enabled flag |
| TestProcessEvent.test_dispatch_on_match | 命中规则 → trigger_semaphore_task 被调用一次 | dispatch 路径 |
| TestProcessEvent.test_no_dispatch_on_mismatch | 不命中 → 不调用 | 非 dispatch |
| TestProcessEvent.test_invalid_json_does_not_raise | 残缺 JSON 行 → 静默吞吐，不 crash | 容错 |
| TestProcessEvent.test_empty_line_skipped | 空白行 → 直接 return | 容错 |

## 5. 预期结果 (Expected Results)
```
Ran 14 tests in <0.01s

OK
```
- 全部 14 个用例 PASS
- exit code 0
- 仅 stderr 有 reactor 自身的 log 行（`MATCH FOUND` / `JSON parse error` 等是被测试触发的预期日志，不是失败）

## 6. 测试执行记录 (Actual Results)
- **执行时间**: 2026-05-09 round1 → round3
- **执行人**: Claude (`feat/eda-advanced-healing` Phase 2 + Phase 3 增量)
- **状态**: PASS

```
$ python3 controller/audit/test_reactor.py
... [reactor] skipping Cool: in cooldown (5.0s < 10s)
... [reactor] received event: go
... [reactor] MATCH FOUND: R
... [reactor] JSON parse error: ...
... [reactor] received event: stop
----------------------------------------------------------------------
Ran 14 tests in 0.002s

OK
```

差异分析: 无；预期与实际一致。

## 7. 结论与建议 (Conclusion)
- L1 覆盖完整，对未来引入新 condition operator (例如 `_regex`、`_in`) 时只需追加平行用例。
- 重构 reactor.py 内部纯函数 (`match_rule`/`process_event`) 时此层先行。
- 不与 Semaphore 通信、不读 docker，CI 友好。

---
*超出本规格的契约/外部行为见 `eda-rules-contract.md` (L2) 与 `eda-reactor-component.md` (L3)*
