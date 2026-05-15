# 测试规格与验证说明书 (TSVS) — Filter Plugins L1 Unit Test

## 1. 测试概览 (Overview)
- **测试 ID**: `TSVS-FILTERS-UNIT-001`
- **层级**: L1 — 纯函数单测，无 Ansible 运行时
- **测试类型**: 功能单元测试
- **优先级**: 中
- **测试目的**: 锁定 `filter_plugins/custom_filters.py` 暴露给模板的 7 个过滤器在边界值上的行为契约：
  - `to_nginx_size` — 字节数 → nginx size 字面量（"1g" / "10m" / "1k" / 原值）
  - `cidr_to_nginx_allow` — CIDR 列表 → `allow <cidr>;` 行
  - `mask_secret` — 字符串脱敏（默认 4 字符前缀；短串全 mask）
  - `env_badge` — env 名 → badge 字面量（plain / emoji / raw 三种 style）
  - `parse_version` — 半版本号字符串 → 数字+后缀混合列表
  - `to_systemd_bool` — Python/字符串 truthy → "yes" / "no"
  - `ljust` / `rjust` — 左右补齐到指定宽度
  - `FilterModule.filters()` — Ansible 入口暴露的过滤器集合包含 `to_nginx_size`
- **不在范围**:
  - 在 Ansible playbook 内调用过滤器的渲染产物（由 `make syntax` + dry-run 间接覆盖）
  - 过滤器调用次数 / 性能

## 2. 测试环境 (Environment)
- 操作系统: Linux 任意版本
- Python: 3.11+
- Ansible: **不需要**（filter_plugins 被作为普通模块导入）

## 3. 软件包清单 (Software Stack)
| 软件 | 版本 | 备注 |
|---|---|---|
| Python | 3.11+ | stdlib only |
| unittest | stdlib | |

## 4. 测试方法与步骤 (Methodology)

### 4.1 前置条件
- `filter_plugins/custom_filters.py` 在 `sys.path` 可解析（测试文件用 `sys.path.append(...filter_plugins)` 注入）
- 文件暴露 module-level 函数 + `FilterModule.filters()` 字典

### 4.2 执行步骤
```bash
make test-filters
# 或：python3 controller/audit/test_filters.py
```

### 4.3 用例清单（8 cases）

| # | 用例 | 验证点 |
|---|---|---|
| TestFilters.test_to_nginx_size | 多档字节数 → "1g"/"2g"/"1m"/"10m"/"1k"/"10k"/"500"（< 1k 原值） | 单位换档边界 |
| TestFilters.test_cidr_to_nginx_allow | CIDR 列表 / IP 列表 → `allow <X>;` 行 | nginx 配置字面量 |
| TestFilters.test_mask_secret | 默认前缀 4 字符 + 4 星；自定义前缀；短串全 mask | 脱敏策略 |
| TestFilters.test_env_badge | production/staging/dev/test/prod 别名 + emoji + raw style | env 别名归一化 |
| TestFilters.test_parse_version | "v1.2.3" / "1.2.3-alpha" / "2.0" → 数字 + 后缀混合列表 | 半版本号解析 |
| TestFilters.test_to_systemd_bool | True/False、"true"/"1"/"on"/"0" → "yes"/"no" | systemd unit bool |
| TestFilters.test_ljust_rjust | 短于宽度时补空格到指定宽度 | 文本对齐 |
| TestFilters.test_filter_module | `FilterModule().filters()` 包含 `to_nginx_size` 键 | Ansible 入口契约 |

## 5. 预期结果 (Expected Results)
```
Ran 8 tests in <0.01s

OK
```
- 全部 8 个用例 PASS
- exit code 0
- 覆盖率：`filter_plugins/custom_filters.py` 100%

## 6. 测试执行记录 (Actual Results)
- **首次执行**: 2026-05-13 — 经 `./scripts/loopback_test_runner.sh standard` 在 `eda/filters-unit.log` 中执行
- **状态**: PASS
- **覆盖率**: `filter_plugins/custom_filters.py` → 100%（50/50 stmts）

## 7. 结论与建议 (Conclusion)
- 锁住了 7 个过滤器在常见边界值上的行为；模板渲染产物变更时此层先告警。
- 新增过滤器：补一组用例 + 在 `FilterModule.filters()` 测试中加 key，并在此 spec 表里追加一行。
- 与 molecule L4 互补：本 spec 锁过滤器返回值；molecule 锁渲染后的实际文件内容是否被服务正确读取。

---
*相关：所有 role 模板调用这些过滤器（grep `to_nginx_size` / `mask_secret` / `env_badge`）*
