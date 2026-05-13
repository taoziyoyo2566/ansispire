# Feature: Audit Plane

## Status
✅ 稳定。R5/R6 测试硬化（2026-05-10）已落地：UFW loopback 显式 allow（消除 self-probe 误失败）+ 模板 `ansible_managed` 通过 `comment` filter 包裹（防止注入到 nginx/mysql conf body 时被解析为未知指令）。

## Overview
The Audit Plane ensures a tamper-proof, reliable trace of all management actions performed in the Ansispire system. It decouples event capture from core management logic.

## 组件 (per hub host)
- **`sink.py`** — Python 轻量 HTTP 接收器，append-only 写入 JSONL（host 端口 3330）
- **`relay.py`** — Python，cursor 分页拉 Semaphore tasks → POST 到 sink；含 60 s heartbeat
- **`reactor.py` (v2.3)** — 见 [`eda-core.md`](./eda-core.md)

容器命名：`ansispire-audit-{sink,relay,reactor}`（dev stack）/ `ansispire-audit-*-e2e`（disposable e2e 隔离命名）。

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
- Decoupled persistence (Sink is independent of Controller / Reactor)
- Append-only on disk (`events.jsonl` 不允许就地改写)

## TSVS
- [`docs/reference/test-specs/audit-plane.md`](../test-specs/audit-plane.md) — 旧规格（如有）
- 复用 [`eda-reactor-e2e.md`](../test-specs/eda-reactor-e2e.md) L4 测试覆盖 sink + relay + reactor 全链路
