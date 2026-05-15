# Ansispire Project TODO

> 工作流：根据 `~/workspace/CLAUDE.md` §2 Plan-First，所有非平凡变更 plan-doc 优先。每完成一轮在 `docs/reviews/<kind>-<topic>/roundN-YYYY-MM-DD.changelog.md` 落证据。
>
> 状态语义：`[ ]` 未启动 / `[~]` 进行中 / `[✓]` 完成 / `[blocked]` 等外部依赖。

---

## 🟢 已完成 (Completed)

| ID | 任务 | 闭环时间 | 闭环报告 |
|---|---|---|---|
| TASK-001 | Advanced Self-Healing Scenarios (v2.3 API-driven reactor & IaC) | 2026-05-10 | [`docs/reviews/feat-eda-advanced-healing/round4-2026-05-10.changelog.md`](docs/reviews/feat-eda-advanced-healing/round4-2026-05-10.changelog.md) |
| TASK-004 | Robust Bootstrap 2.1 (venv isolation & path consistency) | — | — |
| TASK-006 | 升级至 Ansible-Core 2.20.5 (2026 LTS) | — | — |
| — | establish AI-native governance (GEMINI.md / CLAUDE.md hierarchy) | — | — |
| — | mass quality refactoring (lint clean) | — | — |
| — | zero-data-loss audit relay with pagination | — | — |
| — | lightweight EDA reaction engine core (Round 1–4) | 2026-05-10 | TASK-001 |
| — | basic Nginx auto-remediation logic (`feat/eda-remediation-nginx`) | — | — |

---

## 🟡 进行中 / 下一轮可立刻启动 (Active / Next-up)

### TASK-007 — Multi-OS Target Fleet  🆕
- **目标**：把 Alpine / Rocky / Ubuntu / Debian 4 台 VPS 接入 `[targets_*]` 组，实现 `infra_baseline` 的 RHEL / Alpine 分支，让管理 hub 能统一保持全 fleet 的安全基线。
- **入口**：`inventory/hosts.ini` 的 `[targets_debian]` / `[targets_rhel]` / `[targets_alpine]` 占位组（Round 4 已就位）。
- **拆解**：
    1. `[ ]` 在 inventory 加 4 台真实 VPS（host alias + python interpreter pin）
    2. `[ ]` `roles/infra_baseline/tasks/redhat.yml` 实现（dnf 装 docker / 用户）；删 RHEL fail 占位
    3. `[ ]` `roles/infra_baseline/tasks/alpine.yml` 实现（apk + openrc）；删 Alpine fail 占位
    4. `[ ]` 写 `playbooks/deploy_target.yml`（applies infra_baseline only，不装 hub）
    5. `[ ]` Makefile 加 `target-deploy TARGET_NODE=<group>` 包装
    6. `[ ]` 在 ans-hk01 hub 上从 Semaphore 调度对全 targets 的安全任务（demo: ansible all -m ping）
    7. `[ ]` 写 round1-changelog 闭环
- **依赖**：用户提供 4 台 VPS 的 SSH config alias
- **owner**：Claude（实现） + 用户（开 VPS）
- **优先级**：P1（用户已宣布的下一阶段）
- **建议分支**：`feat/multi-os-target-fleet`

### TASK-008 — DB Failover Playbook 真实化
- **目标**：把 `playbooks/remediation/db_failover.yml` 占位剧本替换为真实 failover 实现；翻 `extensions/eda/rules.json` 中 `Remediation: DB Connection Failure` 的 `enabled: true`；加 L4 e2e 用例。
- **拆解**：
    1. `[ ]` 设计 failover 模型（主备切换 / 提升 standby / DNS 切换 哪种？— 需用户决策）
    2. `[ ]` 实现 `playbooks/remediation/db_failover.yml`
    3. `[ ]` 翻 rules.json `enabled: false` → `true`，删 `_disabled_reason`
    4. `[ ]` 在 `controller/audit/e2e/run.sh` 加第二个注入步骤 + 第二个 task 轮询
    5. `[ ]` 更新 `docs/reference/test-specs/eda-reactor-e2e.md` §6（双用例）
- **依赖**：用户决策 failover 模型 + 是否有可演练的 db 拓扑
- **owner**：Claude（实现） + 用户（决策 + db 环境）
- **优先级**：P2
- **建议分支**：`feat/eda-db-failover`

---

## 🔵 待规划 (Backlog)

### TASK-005 — Production Deployment Blueprint  *(scope shrinking after Round 4)*
- **当前状态**：Round 4 已实现 Path A 真部署（`make hub-deploy HUB_NODE=...`） + 完整 operator-guide。原 TASK-005 大部分已被 TASK-001 闭环吸收。
- **剩余 scope**：
    1. `[ ]` `make verify` 的 vault 密码集成（让 `ansible-lint` 能解开 `inventory/local/vault.yml`）— 当前 lint 因密码缺失 fail
    2. `[ ]` 部署后健康监控（hub 上一个 cron / systemd timer 定期查 audit-relay/sink/reactor 还活着）
    3. `[ ]` 定期 EDA token 轮换 playbook
- **优先级**：P2（漏洞修复型）

### TASK-002 — Monitoring Integration (Prometheus)
- **目标**：reactor / relay / sink 暴露 metrics endpoint；hub 上跑 prom-stack；EDA 自愈链路有 `eda_rule_matches_total` 等指标。
- **依赖**：TASK-001 闭环（已完成）；端口 9390/9090 已在 `config/manifest.yml` 预留
- **优先级**：P3
- **建议分支**：`feat/observability-prometheus`

### TASK-003 — Controller High Availability
- **目标**：多节点 Semaphore；DB 从 SQLite 升级到 Postgres / MySQL；HA 选主 / 共享存储
- **优先级**：P3（生产规模化时再做）

---

## 📌 当前分支可发 PR (Branch Readiness)

**Branch**: `feat/eda-advanced-healing` → `master`

**包含**（截至 2026-05-13）：
- TASK-001 Round 1–4：Path B 底盘修复 / 测试金字塔 L1+L2+L3 / events.schema.json + L4 e2e harness / Path A 全面硬化（rsync excludes + state migration + manifest SSOT + inventory taxonomy + OS-family 守门 + Makefile HUB_NODE）
- TASK-001 Round 5–6（`f478b45`）：Molecule 深循环 + 安全硬化（UFW loopback / `ansible_managed` filter / MySQL re-runnable / 删 `nginx_vhosts` legacy alias / 删 `verify_report.py` 占位脚本）
- 文档企业化 P1–P6（`f7a204f`…`204f75e`）：README 重写 + SUMMARY→ARCHITECTURE + `docs/` 4 子目录分受众 + LICENSE/SECURITY/CHANGELOG/`docs/README.md` + 38 旧 review 归档
- testing-strategy R1+R2（`6a2e896` `d5f3087`）：testing-governance + test-plan + TSVS INDEX + 4 molecule TSVS
- operator-guide R1+R2+R3+R3 hotfix（`f5c0725` `258e320` `39dd28e`）：user-guide 完成 pass + 治理迁移
- testing-tier-c R1+R2（`2f3fbff` `3113428` `893b6a7`）：T-C1 my.cnf hard assert / T-C2 root pw dedup / T-C3 testuser probe / G3 Debian 12 + MySQL APT GPG 修复
- claude.md W-R14 cleanup R1+R2（`40e9ff3` `71bf1bf`）：剔除场景化规则，瘦身到 methodology-only
- ci(workflow) `e60d5c3`：drop stale Ubuntu 20 from matrix

**测试状态**（2026-05-13 实测）：
- ✅ `make test-eda` 28 cases (L1+L2+L3) PASS < 1 s — 重跑确认
- ✅ `make verify-quick` (stag + prod syntax) PASS — 重跑确认
- ✅ `molecule test -s database` (ubuntu22 + debian12) ALL 8 阶段 Successful — 验 `893b6a7` + `3113428`
- ✅ `molecule test -s webserver` (ubuntu22 + debian12) ALL 8 阶段 Successful
- ✅ `molecule test -s full-stack` (fullstack-ubuntu22) ALL 8 阶段 Successful，verify 含 nginx syntax / nginx :80 / mysql :3306 / appdb / my.cnf managed
- ✅ `make test-eda-e2e` (L4) PASS — 重跑确认（task1 status=success in 22 s, total 57 s）
- ✅ `make hub-deploy-check NODE=remote` PASS — 上次实测 2026-05-10，本轮未重跑（无相关 commit 改动）
- ✅ `make verify` (lint + syntax + test-eda + dry-run) PASS — 重跑确认（vault 阻塞已被 `ec93094` 修复，TODO 标注过期）

**已知 NOT done（不阻塞 closure）**：
- DB Failover rule 仍 `enabled: false`（追到 TASK-008）
- 真跑 `make hub-deploy HUB_NODE=remote` 上 ans-hk01（待用户授权）
- `molecule test -s common` 本轮未跑（database / webserver / full-stack 已覆盖最近两次实质 commit + 集成路径）

---

## 🗂 索引

- **架构主图**：[`ARCHITECTURE.md`](ARCHITECTURE.md)
- **EDA 自愈用户向 guide**：[`docs/user-guide/02-quickstart-eda.md`](docs/user-guide/02-quickstart-eda.md)
- **Hub 部署速查**：[`docs/operations/hub-deployment.md`](docs/operations/hub-deployment.md)
- **测试规格 (TSVS)**：[`docs/reference/test-specs/`](docs/reference/test-specs/)
- **变更证据链**：[`docs/reviews/feat-eda-advanced-healing/`](docs/reviews/feat-eda-advanced-healing/)
- **CLAUDE.md 三层**：`~/.claude/CLAUDE.md` / `~/workspace/CLAUDE.md` / `./CLAUDE.md`

---
*Last updated: 2026-05-13 (Branch Readiness 重核 + molecule database/webserver 实测落证据).*
