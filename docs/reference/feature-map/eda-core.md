# Feature: EDA Reactor Core

## Status
✅ **TASK-001 closed 2026-05-10** (Round 4). Path A (Ansible role deploy) + Path B (docker-compose dev) both green; full e2e self-healing chain verified < 60 s cold start.

## Overview
A lightweight Event-Driven Ansible (EDA) reaction engine that transforms audit events into autonomous remediation actions. The reactor watches `events.jsonl`, matches against `rules.json`, and triggers Semaphore job templates over the REST API using a Bearer token.

## Operational entry points
- **第一次接触**：[`operator-guide.md`](../../user-guide/02-quickstart-eda.md) — long-form user guide, no prior project knowledge assumed
- **Maintainer 速查**：[`operations.md`](../../operations/eda-core.md) — terse command reference

## Key triggers
- New entries in `events.jsonl` matching conditions in `extensions/eda/rules.json` (with `enabled: true`)

## Actions supported
- **Semaphore API** (preferred): `POST /api/project/<id>/tasks`, dynamic resolution of `template_name → template_id`
- **Webhook**: outbound HTTP for alerting (no remediation execution)
- **Shell**: local script trigger (legacy / debug)

## Matching semantics
- **`_contains` suffix**: substring match on the event field (e.g. `description_contains: "Disk Full"`)
- **No suffix**: exact-equality match
- **`enabled: false`**: rule short-circuits in `match_rule` early-return; preserved in file for documentation
- **Cooldown**: per-rule timestamp prevents event-storm cascades (default 600 s)

## Configuration SSOT
- **Ports + image versions**: `config/manifest.yml` → rendered into `controller/semaphore/.env` by `make manifest-sync`; consumed by both Ansible vars_files and docker compose `${VAR}` interpolation
- **Hub topology**: `inventory/hosts.ini` `[hub_local]` / `[hub_remote]` / `[hub:children]`
- **Rules**: `extensions/eda/rules.json`
- **Rules schema**: `extensions/eda/rules.schema.json` (Draft-07; validated by `make test-rules-schema` — part of `make test-eda` chain)
- **Event contract**: `extensions/eda/events.schema.json` (Draft-07; reactor logs `event schema: <$id>@<version>` at startup)

## Test pyramid (TSVS-tracked)
| Layer | Spec | Cases | Wall time |
|---|---|---|---|
| L1 reactor unit | [`docs/reference/test-specs/eda-reactor-unit.md`](../test-specs/eda-reactor-unit.md) | 14 | < 0.01 s |
| L2 rules contract | [`docs/reference/test-specs/eda-rules-contract.md`](../test-specs/eda-rules-contract.md) | 9 | < 0.1 s |
| L3 reactor component | [`docs/reference/test-specs/eda-reactor-component.md`](../test-specs/eda-reactor-component.md) | 5 | < 1 s |
| L4 disposable e2e | [`docs/reference/test-specs/eda-reactor-e2e.md`](../test-specs/eda-reactor-e2e.md) | 1 | ~60 s |

L1+L2+L3 entry: `make test-eda` (in `make verify` chain). L4 entry: `make test-eda-e2e` (host-only, NOT in verify).

## Engineering mandates (2026 LTS)
- **Bearer Token Auth**: M2M MUST use scoped API tokens minted by `bootstrap.yml` to `controller/semaphore/.secrets` (Path B) or `<hub>:/var/lib/ansispire/state/.eda_token` (Path A). Hardcoded passwords are forbidden.
- **SQLite Persistence**: Control plane uses SQLite (BoltDB deprecated upstream).
- **IaC Provisioning**: All Semaphore resources (Projects, Templates, Keys) defined in `controller/semaphore/bootstrap.yml`. UI-zero-touch.
- **Image Pinning**: `manifest.yml` `*_pinned` fields pin production image tags; `default_tag: latest` is the fallback for fresh clones.
- **Rsync Hygiene (Path A)**: `roles/ansispire_hub/tasks/main.yml` enforces 21 exclude patterns (4 groups: local-artefacts / secrets / stateful / docs). No credentials or stateful files cross the rsync boundary.
- **State Separation (Path A)**: `.eda_token` lives in `/var/lib/ansispire/state/`, outside the rsync target directory, so `rsync --delete` cannot wipe it across deploys.

## Dependencies
- **Data Source**: `events.jsonl` (Audit Sink + Audit Relay)
- **Rulebook**: `extensions/eda/rules.json`
- **Schema**: `extensions/eda/events.schema.json`
- **Identity**: `SEMAPHORE_API_TOKEN` env var (loaded from `.secrets` or `state/.eda_token` depending on path)

## Round-by-round history (this branch)
- Round 1 (2026-05-09) — Path B 底盘修复：`bootstrap.yml` 回滚至 486-line 版本 + token mint + RBAC；端口 SSOT；image pin v2.18.2
- Round 2 (2026-05-09) — 测试金字塔 L1+L2+L3 落地
- Round 3 (2026-05-09) — `events.schema.json` + `enabled` 字段 + L4 e2e harness 实现
- Round 4 (2026-05-10) — Path A 全面硬化：manifest SSOT、inventory `[hub_local/remote]`、rsync excludes、state migration、OS-family 守门、`make hub-deploy NODE=` 包装。**TASK-001 闭环。**
- Round 5+6 follow-up (2026-05-10) — Molecule 深循环 + 安全硬化：UFW loopback allow / `ansible_managed` 包 `comment` filter / MySQL re-runnable / 删 `nginx_vhosts` legacy alias。**Test infra 范畴**，不属 reactor 自身改动。
- testing-strategy R1+R2 (2026-05-11) — testing-governance + test-plan + TSVS INDEX + 4 molecule TSVS。**治理文档落盘**，无 reactor 行为变化。
- testing-tier-c R1+R2 (2026-05-11/12) — T-C1 my.cnf hard assert / T-C2 root pw dedup / T-C3 testuser probe / Debian 12 service-name + MySQL APT GPG 修复。**Test infra 范畴**。
- audit-pr-readiness (2026-05-13) — 本会话 PR-readiness 审查 + testing-governance §9 测试卫生 + feature-map sync round。

详见 [`docs/reviews/feat-eda-advanced-healing/`](../../reviews/feat-eda-advanced-healing/) + [`docs/reviews/feat-testing-strategy/`](../../reviews/feat-testing-strategy/) + [`docs/reviews/feat-testing-tier-c/`](../../reviews/feat-testing-tier-c/) + [`docs/reviews/audit-pr-readiness/`](../../reviews/audit-pr-readiness/)。
