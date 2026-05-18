# Feature: Audit Plane

## Status
✅ 稳定。R5/R6 测试硬化（2026-05-10）已落地：UFW loopback 显式 allow（消除 self-probe 误失败）+ 模板 `ansible_managed` 通过 `comment` filter 包裹（防止注入到 nginx/mysql conf body 时被解析为未知指令）。

## Overview
The Audit Plane ensures a tamper-proof, reliable trace of all management actions performed in the Ansispire system. It decouples event capture from core management logic.

## 组件 (per hub host)
- **`sink.py`** — Python 轻量 HTTP 接收器，append-only 写入 JSONL（host 端口 3330）。容器从 `Dockerfile.sink` 本地构建，logrotate 烘焙入镜像（不再 runtime `apk add`）
- **`relay.py`** — Python，cursor 分页拉 Semaphore tasks → POST 到 sink；含 60 s heartbeat；compose 健康检查通过 `pidof python3`
- **`reactor.py` (v2.4)** — 见 [`eda-core.md`](./eda-core.md)。容器从 `Dockerfile.reactor` 本地构建（baked-in jq + procps）；cursor 状态持久化到 `audit-reactor-state:/var/lib/audit-reactor/cursor`；compose 健康检查通过 `pgrep -f reactor.py`

容器命名：`ansispire-audit-{sink,relay,reactor}`（dev stack）/ `ansispire-audit-*-e2e`（disposable e2e 隔离命名）。镜像 tag：`ansispire/audit-{sink,reactor}:${AUDIT_IMAGE_TAG}`（本地 build；relay 仍直接用 `python:3.12-alpine` 因为 relay.py 是稳定脚本无需烘焙）。

## Key Triggers
- Any action in the Semaphore API (login, project update, key creation)
- Relay heartbeat (sent every 60 s)

## Dependencies
- **Upstream**: Semaphore REST API (`/api/events`)
- **Downstream**: Audit Sink (`HTTP POST`)

## Data Flow
`Semaphore` → `relay.py`（polling + cursor pagination） → `sink.py`（HTTP receiver） → `events.jsonl`（artifact） → `reactor.py`（rule match → Semaphore API）

## Critical Guarantees
- Zero data loss during relay restarts (via cursor + backfill pagination)
- Zero data loss during reactor restarts (cursor persisted to `audit-reactor-state` volume; cold start resumes from last flushed offset rather than tail-EOF — see `eda-core.md` `CURSOR_FILE` env)
- Decoupled persistence (Sink is independent of Controller / Reactor)
- Append-only on disk (`events.jsonl` 不允许就地改写)
- Bounded reload pressure: reactor `load_rules` is mtime-gated (`RULES_MIN_RELOAD_INTERVAL`, default 30 s) — busy editor saves cannot DoS the matcher

## TSVS
- [`docs/reference/test-specs/audit-plane.md`](../test-specs/audit-plane.md) — 旧规格（如有）
- 复用 [`eda-reactor-e2e.md`](../test-specs/eda-reactor-e2e.md) L4 测试覆盖 sink + relay + reactor 全链路
