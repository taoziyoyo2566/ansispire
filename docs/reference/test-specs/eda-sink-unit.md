# 测试规格与验证说明书 (TSVS) — EDA Sink L1 Unit Test

## 1. 测试概览 (Overview)
- **测试 ID**: `TSVS-EDA-SINK-UNIT-001`
- **层级**: L1 — Python 单测，HTTPServer socket 与 wfile 全部通过 `unittest.mock` 注入
- **测试类型**: 功能单元测试
- **优先级**: 高
- **测试目的**: 验证 `controller/audit/sink.py` 的事件落盘与 HTTP handler 行为：
  - `_append` 把 dict 序列化为单行 JSON 并 append
  - `GET /healthz` 返回 200 + 字面量 "ok"
  - `GET /unknown-path` 返回 404
  - `POST /event` 合法 JSON → 解析并 _append 一条带 `payload` 的记录、回 204
  - `POST /event` 非法 JSON → fallback：把原始 body 字符串放进 `payload`、不 crash
- **不在范围**:
  - 真实 docker 端口绑定 / TCP 行为 (→ `TEST-EDA-004` e2e)
  - 落盘文件被 relay/reactor 消费的下游 (→ `TSVS-AUDIT-LOOP-001`)

## 2. 测试环境 (Environment)
- 操作系统: Linux 任意版本
- Python: 3.11+
- 网络: **无**（socket 不真实绑定）

## 3. 软件包清单 (Software Stack)
| 软件 | 版本 | 备注 |
|---|---|---|
| Python | 3.11+ | stdlib only |
| http.server.BaseHTTPRequestHandler | stdlib | 被 patch 掉 `handle` / `parse_request` 后单元化 |
| unittest.mock | stdlib | MagicMock for socket / server, mock_open for file ops |

## 4. 测试方法与步骤 (Methodology)

### 4.1 前置条件
- `controller/audit/sink.py` 暴露 `Handler`（HTTPRequestHandler 子类）+ `_append`

### 4.2 执行步骤
```bash
make test-eda-sink-unit
# 或：python3 controller/audit/test_sink.py
```

### 4.3 用例清单（5 cases）

| # | 用例 | 验证点 |
|---|---|---|
| TestSink.test_append | 写一次，`open().write` 被调一次，写入内容是单行 JSON | 序列化 + 落盘格式 |
| TestSink.test_handler_get_healthz | GET /healthz → `send_response(200)` + body `b"ok"` | 健康探针 |
| TestSink.test_handler_get_404 | GET /unknown → `send_response(404)` | 路由兜底 |
| TestSink.test_handler_post_event | POST /event + 合法 JSON → `send_response(204)` + `_append` 收到带 payload 的 dict | 写入路径 |
| TestSink.test_handler_post_invalid_json | POST /event + 非法 JSON → `_append` 收到的 record.payload 为原始字符串（不 crash） | 容错 fallback |

## 5. 预期结果 (Expected Results)
```
Ran 5 tests in <0.05s

OK
```
- 全部 5 个用例 PASS
- exit code 0
- 无 socket / 端口占用

## 6. 测试执行记录 (Actual Results)
- **首次执行**: 2026-05-13 — 经 `./scripts/loopback_test_runner.sh standard` 在 `eda/sink-unit.log` 中执行
- **状态**: PASS

## 7. 结论与建议 (Conclusion)
- 锁住了 sink 的两条路径：健康探针 + 事件 POST。新增路由（如 `/metrics`）时按平行用例追加。
- 不覆盖：磁盘满 / 写入 IOError / 大 body 截断——若引入这些边界处理，应追加用例。
- 与 L5 `TSVS-AUDIT-LOOP-001` 互补：本 spec 锁 handler 单步语义，loop-smoke 锁端到端写入。

---
*父级链路 spec 见 `audit-loopback-functional.md` (L5)*
