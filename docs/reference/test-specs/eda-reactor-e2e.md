# 测试规格与验证说明书 (TSVS) — EDA Reactor End-to-End (L4)

## 1. 测试概览 (Overview)
- **测试 ID**: `TEST-EDA-004`
- **层级**: L4 — 端到端，**真** docker，真 Semaphore，真 ansible-runner
- **测试类型**: 全链路验证 / smoke
- **优先级**: 高（但不强制 CI）
- **测试目的**: 在隔离的 disposable docker compose 项目里完整验证「故障注入 → reactor → Semaphore 模板 → ansible 执行 → 任务成功」闭环。一次 cold-start 下来 < 90 秒。
- **不在范围**: 性能基线、规模化（多事件并发）、故障注入路径上的 fault-injection（两者属 Phase 5+）。

## 2. 测试环境 (Environment)
- 操作系统: Linux + Docker engine 25+
- 资源: 1.5 GB RAM 富余、1 CPU 富余
- 端口（host 侧 +20 偏移于 dev semaphore，跳出整个 dev 端口范围避免冲突）:
  - Semaphore web: **3320** (e2e) ↔ 3300 (dev)
  - Audit sink: **3330** (e2e) ↔ 3310 (dev)
  - 注：最初设计 +10 偏移 (3310/3320)，但 dev audit-sink 已占 3310 → 改为 +20。
- Docker compose project name: **ansispire-e2e** (与 dev 的 `semaphore` / `audit` projects 完全隔离)
- 容器网络: `controller-net-e2e` (与 dev `controller-net` 隔离)
- Volumes: 全部 disposable，`down -v` 时删

## 3. 软件包清单 (Software Stack)
| 软件 | 版本 | 备注 |
|---|---|---|
| Docker | 25+ | compose v2 |
| semaphoreui/semaphore | v2.18.2 | 与 dev 共享镜像（已在本地） |
| python:3.12-alpine | latest | sink/relay/reactor base |
| Ansible | 2.20.5 | 通过 Semaphore 运行 disk_cleanup.yml |
| curl | system | 状态轮询 |
| jq | system or via container | JSON 解析 |

## 4. 测试方法与步骤 (Methodology)

### 4.1 前置条件
- Phase 1/2 全部 landed (bootstrap.yml token-mint + ports SSOT + Make targets)
- L1+L2+L3 三层全绿 (`make test-eda`)
- Dev 控制平面可同时在跑（端口隔离），不需要先停

### 4.2 执行步骤
```bash
make test-eda-e2e
```

或手动分步：
```bash
cd controller/audit/e2e
docker compose -p ansispire-e2e --env-file .env up -d
./run.sh   # bootstrap + inject + poll + teardown
```

### 4.3 步骤序列（脚本自动）

| 阶段 | 动作 | 期望 |
|---|---|---|
| 1. up | `docker compose -p ansispire-e2e ... up -d` | 4 容器创建：semaphore-e2e / audit-sink-e2e / audit-relay-e2e / audit-reactor-e2e |
| 2. wait healthy | 轮询 semaphore-e2e healthcheck | < 60 s 内 healthy |
| 3. bootstrap | `ansible-playbook controller/semaphore/bootstrap.yml -e semaphore_password=... -e semaphore_url=http://localhost:3320 -e secrets_path=...` | ok≥30, failed=0; 写入 `e2e/.secrets` |
| 4. restart audit | 让 reactor 拿 token | reactor 日志含 `event schema: ...` + `loaded 1 rules`（Disk Failover 是 disabled, count = 1） |
| 5. inject | 写一行 Disk Full event 到 audit-sink-e2e 的 jsonl | reactor 日志 `MATCH FOUND: Remediation: Disk Full` |
| 6. poll Semaphore tasks | curl `/api/project/1/tasks?limit=1` 直到 `status == "success"` | 单条 task 出现，最终 status=success |
| 7. teardown | `docker compose -p ansispire-e2e ... down -v` | 容器、卷、网络全部清理；`docker ps` 不见 e2e 容器；dev 栈不受影响 |

### 4.4 失败模式与诊断

| 现象 | 可能原因 | 诊断命令 |
|---|---|---|
| step 2 timeout | semaphore-e2e 镜像未拉 / 端口占用 | `docker logs ansispire-semaphore-e2e` |
| step 3 ok=0 failed=1 password | `.env` 未生成 / SEMAPHORE_ADMIN_PASSWORD 不匹配 | `cat controller/audit/e2e/.env` |
| step 5 reactor 不 MATCH | rules.json 与 sink 写入的 event 字段不一致；schema 未 mount | `docker exec ansispire-audit-reactor-e2e env \| grep EVENTS_SCHEMA` |
| step 6 task 永远 waiting | Semaphore runner 无法 git-clone /workspace | `docker logs ansispire-semaphore-e2e` 看 ansible-runner |

## 5. 预期结果 (Expected Results)
- exit code 0
- wall time < 90 秒 (cold start, 3 GB free disk)
- 终端输出最末一行类似 `E2E PASS — task X status=success in Ys`
- `docker ps` 不见 `ansispire-*-e2e` 容器（teardown 完成）
- dev 栈（`ansispire-semaphore` / `ansispire-audit-*`）不受影响

## 6. 测试执行记录 (Actual Results)
- **执行时间**: 2026-05-10 01:55–01:57 (cold start, dev stack 同时运行)
- **执行人**: Claude (`feat/eda-advanced-healing` Phase 3 P3.6)
- **状态**: **PASS**

```
$ make test-eda-e2e
==> [pre] controller/audit/e2e/.env missing — copying from .env.example
==> [1/7] up: project=ansispire-e2e, semaphore=http://localhost:3320, sink=http://127.0.0.1:3330/event
 Network controller-net-e2e Created
 Volume ansispire-e2e_audit-e2e-data Created
 ... (4 containers created)
==> [2/7] wait semaphore healthy (≤90s)
    healthy after 22s
==> [3/7] bootstrap (mint token, register remediation templates)
PLAY RECAP: ok=39  changed=1  failed=0
    token persisted to controller/audit/e2e/.secrets
==> [4/7] recreate audit-relay + audit-reactor (pick up token)
==> [5/7] inject Disk Full event into the sink
    injected
==> [6/7] poll Semaphore tasks until status=success (≤60s)
==> E2E PASS — task 1 status=success in 23s (total 57s)
==> [teardown] docker compose down -v
```

差异分析 vs §5 期望:

| 项 | 期望 | 实测 | 备注 |
|---|---|---|---|
| 端口 | 3310/3320 | 3320/3330 | dev audit-sink 占 3310，spec 已修订为 +20 偏移 |
| 总耗时 | < 90 s | 57 s | ✓ |
| Semaphore healthy | < 60 s | 22 s | ✓ |
| Bootstrap | ok≥30 failed=0 | ok=39 failed=0 | ✓ |
| Inject → success | poll loop ends success | task id=1 status=success in 23s | ✓ |
| Teardown | 容器/卷/网络全清 | 全清；dev 4 容器仍在跑 | ✓ |

## 7. 结论与建议 (Conclusion)
- 闭环 (jsonl 注入 → reactor MATCH → Semaphore POST → ansible-runner 执行 → status=success) 在 disposable docker compose 项目里完整成立。
- 隔离性证实：teardown 后 `docker ps`/`docker volume ls`/`docker network ls` 均无 e2e 残留；dev 控制平面 (`ansispire-semaphore` / `ansispire-audit-*`) 全程不受影响。
- run.sh 的 `trap cleanup EXIT` 在 success/failure/被中断时都会执行 `down -v`；保留实例调试用 `E2E_KEEP=1 ./run.sh`。
- e2e 不进 `make verify`：跑完整栈需要 ~60 s + ~500 MB RAM，CI 上不划算；`make verify` 仍只走 L1+L2+L3 (28 cases, < 1 s) + lint/syntax/dry-run。
- 下一次 e2e 失败现场最可能的根因（按优先级）：(a) host 端口占用 → 改 `.env`；(b) Semaphore 镜像未本地缓存且无网 → 提前 `docker pull`；(c) bootstrap variable 漂移（如未来再有 `sem_pass` vs `semaphore_password` 那种）→ L1+L2 会先挡住。

## 8. 演化预案
- 若后续引入更多 remediation rules，每条增加一个独立的 inject step（保持每个 e2e 用例对一条 rule）
- 若 Phase 5 加 Prometheus 指标，e2e 多一步：metrics endpoint 应该看到 `eda_rule_matches_total{rule="..."}` ≥ 1
- 若想加入 CI，先把整套部分（不含 ansible-runner 跑真 playbook 的部分）切出 mock 版本作为 L4-mock，真 e2e 仍只在 host smoke 上跑
- DB Failover rule 当前 `enabled: false`；其 e2e 用例在 placeholder playbook 落地后再补 (TASK-001 follow-up)
