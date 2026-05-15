# 测试规格与验证说明书 (TSVS) — EDA Relay L1 Unit Test

## 1. 测试概览 (Overview)
- **测试 ID**: `TSVS-EDA-RELAY-UNIT-001`
- **层级**: L1 — Python 单测，所有 IO（urllib / 文件）通过 `unittest.mock` 注入
- **测试类型**: 功能单元测试
- **优先级**: 高
- **测试目的**: 验证 `controller/audit/relay.py` 的 cursor 持久化、HTTP 分页拉取与 tick 增量推进逻辑，确认在以下场景下行为正确：
  - 已存在 cursor 文件 → 读出最后时间戳
  - cursor 文件缺失 → 回退到 EPOCH
  - 保存 cursor → 写盘 + atomic rename 路径正确
  - urllib.urlopen 返回事件列表 → 解析为 dict[]
  - tick 拉到比 cursor 新的事件 → 转发 + 推进 cursor
  - tick 拉到 ≤ cursor 的事件 → 既不转发也不推进
- **不在范围**:
  - 真实 Semaphore /api/events 契约 (→ `TSVS-AUDIT-LOOP-001` L5)
  - reactor → relay → sink 端到端 (→ `TEST-EDA-004` e2e)

## 2. 测试环境 (Environment)
- 操作系统: Linux 任意版本
- Python: 3.11+ (项目地板要求)
- 网络: **无**（urllib 被 mock，纯本地执行）

## 3. 软件包清单 (Software Stack)
| 软件 | 版本 | 备注 |
|---|---|---|
| Python | 3.11+ | stdlib only |
| unittest, unittest.mock | stdlib | mock_open + MagicMock for urlopen |

## 4. 测试方法与步骤 (Methodology)

### 4.1 前置条件
- `controller/audit/relay.py` 暴露 `load_cursor` / `save_cursor` / `fetch_page` / `tick` / `forward` / `EPOCH` / `SEM_TOKEN`

### 4.2 执行步骤
```bash
make test-eda-relay-unit
# 或：python3 controller/audit/test_relay.py
```

### 4.3 用例清单（6 cases）

| # | 用例 | 验证点 |
|---|---|---|
| TestRelay.test_load_cursor_exists | cursor JSON 文件存在 → 返回 `last_ts` | 读路径 |
| TestRelay.test_load_cursor_missing | open 抛 FileNotFoundError → 返回 `EPOCH` | 容错 |
| TestRelay.test_save_cursor | 写文件路径包含目标时间戳 | atomic write 路径 |
| TestRelay.test_fetch_page | urlopen 返回 JSON 列表 → 解析为 dict[] | HTTP 解析 |
| TestRelay.test_tick_new_events | 拉到 ≥1 个比 cursor 新的事件 → forward 每个 + cursor 推进到最新 | 增量推进 |
| TestRelay.test_tick_no_new_events | 拉到的事件均 ≤ cursor → 不 forward、cursor 不变 | 幂等 |

## 5. 预期结果 (Expected Results)
```
Ran 6 tests in <0.05s

OK
```
- 全部 6 个用例 PASS
- exit code 0
- 无外部网络流量（urllib 被 patch）

## 6. 测试执行记录 (Actual Results)
- **首次执行**: 2026-05-13 — 经 `./scripts/loopback_test_runner.sh standard` 在 `eda/relay-unit.log` 中执行
- **状态**: PASS

## 7. 结论与建议 (Conclusion)
- L1 锁住了 relay 的 cursor 推进语义；reactor 改协议（事件 envelope 形状变更）时此层会先响应。
- 不覆盖：分页 next-token、403/429 重试、连续 fetch 死循环防护——若 relay.py 引入这些行为，应追加用例或新建 L3 component spec。
- 与 L5 `TSVS-AUDIT-LOOP-001` 互补：本 spec 锁内部逻辑，loop-smoke 锁真实链路。

---
*父级链路 spec 见 `audit-loopback-functional.md` (L5)*
