# 测试规格与验证说明书 (TSVS) — EDA Reactor Component Test (L3)

## 1. 测试概览 (Overview)
- **测试 ID**: `TEST-EDA-003`
- **层级**: L3 — 组件契约测，进程内 mock HTTP server，**无** docker，**无**真 Semaphore
- **测试类型**: 出站 HTTP 契约 / API 调用形态
- **优先级**: 高
- **测试目的**: 验证 reactor.py 调用 Semaphore REST API 时的请求契约稳定：method、path、`Authorization: Bearer <token>` header、JSON body 形态、project/template ID 解析顺序、template_id 缓存命中。
- **不在范围**: rules.json schema (→ L2)；reactor 纯函数逻辑 (→ L1)；Semaphore 真实接受 (→ Phase 3 L4)。

## 2. 测试环境 (Environment)
- Python: 3.10+
- Stdlib only (`http.server`, `threading`, `unittest`)

## 3. 软件包清单 (Software Stack)
| 软件 | 版本 | 来源 |
|---|---|---|
| Python | 3.10+ | system or venv |
| http.server | stdlib | mock Semaphore endpoint |
| threading | stdlib | non-blocking server thread |
| unittest | stdlib | |

## 4. 测试方法与步骤 (Methodology)

### 4.1 前置条件
- `controller/audit/reactor.py` 模块可被 import

### 4.2 执行步骤
```bash
python3 controller/audit/test_reactor_component.py
# 或经 Make wrapper:
make test-eda-component
```

### 4.3 测试架构
```
┌──────────────────┐                     ┌────────────────────┐
│ test runner      │  monkeypatch        │ reactor module     │
│ (this file)      │ ─SEMAPHORE_URL─────▶│ trigger_semaphore_ │
│                  │  ─SEMAPHORE_TOKEN──▶│   task()           │
│                  │                     │                    │
│  recorded calls  │◀────HTTP────────────│ urllib.request     │
│  ↑               │                     └────────────────────┘
│  └ ThreadingHTTPServer @ 127.0.0.1:<random>
│    serves /api/projects, /api/project/<id>/templates,
│            /api/project/<id>/tasks
└──────────────────┘
```

### 4.4 用例清单

| # | 用例 | 验证点 |
|---|---|---|
| K1 | trigger_semaphore_task 完整 happy path | 三次出站请求顺序: `GET /api/projects` → `GET /api/project/<pid>/templates` → `POST /api/project/<pid>/tasks`；每次 header 含 `Authorization: Bearer <token>`；POST body 是 `{"template_id": <int>}` |
| K2 | template_id 缓存复用 | 同 project + template 第二次调用时只发 `GET /api/projects` + `POST /api/project/<pid>/tasks`；不重发 `GET /templates` |
| K3 | template_name 找不到 | mock 返回的 templates 列表中没有匹配项 → reactor 不发 POST，记录错误日志后返回 |
| K4 | project_name 找不到 | mock 返回的 projects 列表中没有匹配项 → reactor 不发 GET templates / POST，记录错误日志后返回 |
| K5 | SEMAPHORE_TOKEN 空 | 走完 GET 解析后到 POST 之前 abort，POST 不发出 |

## 5. 预期结果 (Expected Results)
```
Ran 5 tests in <2s

OK
```
- 5 个用例 PASS
- mock server 在测试过程中开/关，端口由 OS 随机分配，无端口冲突风险
- exit code 0

## 6. 测试执行记录 (Actual Results)
- **执行时间**: 2026-05-09 round2
- **执行人**: Claude (`feat/eda-advanced-healing` Phase 2)
- **状态**: PASS

```
$ python3 controller/audit/test_reactor_component.py
[reactor] remediation triggered: template=42 (Auto Remediation: Disk Cleanup), status=201
[reactor] remediation failed: could not resolve template Auto Remediation: Disk Cleanup in project 7
[reactor] remediation failed: could not resolve project ansispire
[reactor] remediation failed: SEMAPHORE_API_TOKEN not set
----------------------------------------------------------------------
Ran 5 tests in 0.533s

OK
```

差异分析: 无；预期与实际一致。stderr 上的 `[reactor] remediation triggered/failed` 是被测试主动触发的预期日志（K1 K3 K4 K5 各一条），不是失败信号。

## 7. 结论与建议 (Conclusion)
- 出站 HTTP 契约已锁：method、路径、Bearer header、POST body shape 全部断言。Semaphore API 真升级时此层会先红，提前一个版本拦下漂移。
- K2 验证 `TEMPLATE_CACHE` 命中：第二次同 `template_name` 调用不重发 GET templates，性能与正确性皆有。
- 当前 reactor 没有 project_id 缓存（每次重新 GET projects），观察到但未要求；如果未来引入缓存可在此追加 K6（project 缓存命中）。
- 不依赖 docker，可在 CI 阶段无外部依赖运行（contrast L4 e2e in Phase 3）。

## 8. 演化预案
- Semaphore API 路径变更（如 v3.x 引入新 endpoint）：本层先红，提前一个版本暴露问题
- 引入新 action type（webhook / shell）：在此文件平行添加 K6+
