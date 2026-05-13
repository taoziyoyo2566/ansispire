# Feature: Test Infrastructure

## Status
✅ 稳定。Testing governance R1+R2（2026-05-11）+ Tier C R2（2026-05-12）+ Test Hygiene §9（2026-05-13）已全部落地。

> **本文是测试基础设施的功能地图；治理细节（决策树 / 闸口 / TSVS 规约 / 测试卫生）见 [`docs/governance/testing-governance.md`](../../governance/testing-governance.md)，覆盖现状与缺口分析见 [`docs/governance/test-plan.md`](../../governance/test-plan.md)。**

---

## 1. 测试金字塔（载体）

| 层 | 范围 | 载体 | 当前 case 数 | 入口 |
| :--- | :--- | :--- | :--- | :--- |
| L0 静态 | 文本 / 语法 / 密钥扫描 | yamllint, ansible-lint, syntax-check, detect-secrets | — | `make verify-quick` / `make verify` |
| L1 单元 | 纯函数 / 无 IO | `controller/audit/test_reactor.py` | 14 | `make test-eda-unit` |
| L2 契约 | 跨配置一致性 | `controller/audit/test_rules_contract.py` | 9 | `make test-eda-contract` |
| L3 组件 | 单组件 + mock | `controller/audit/test_reactor_component.py` | 5 | `make test-eda-component` |
| L4 集成 | 单/多 role 部署到容器 | Molecule 4 场景：`common` / `webserver` / `database` / `full-stack` | 平台：Ubuntu 22.04 + Debian 12 | `molecule test -s <X>` 或 `make molecule-all` |
| L5 端到端 | 真 docker stack 多组件协同 | `controller/audit/e2e/run.sh` + smoke 系列 | — | `make test-eda-e2e` / `make controller-{loop,rbac}-smoke` |

**关键观察**：L0–L3 抓不到部署期 bug（防火墙规则、模板渲染产物、systemd 状态）。这类 bug **只能由 L4 浮现** —— Round 5 五个 bug 全部 Molecule 才发现。

---

## 2. TSVS（Test Specification & Verification Spec）

- **总注册表**：[`docs/reference/test-specs/INDEX.md`](../test-specs/INDEX.md) — 10 个 TSVS（4 Molecule + 6 EDA/audit/RBAC），Active/Retired 状态机
- **模板**：[`docs/reference/test-specs/TEMPLATE.md`](../test-specs/TEMPLATE.md)
- **规约**：testing-governance.md §7 —— 任何功能性测试的新增/重大变更必须产出对应 TSVS 并登记
- **当前 4 个 Molecule TSVS**：`molecule-common.md` / `molecule-webserver.md`（含 `.service` 后缀兼容）/ `molecule-database.md`（T-C1/T-C2/T-C3）/ `molecule-full-stack.md`

---

## 3. 测试卫生（Hygiene，§9）

每次测试模拟"新机 clone 即跑"语义：测试结果只能依赖 git 树 + 已声明依赖（`requirements.txt` / `requirements.yml`），不得依赖前次跑遗留的容器/卷/网络/临时文件。

**关键清理点**：
- L5 失败 → 必须 `rm -rf ~/.ansible/tmp/molecule.<scenario>` + 残留容器（否则下次 destroy.yml 解析报 rc=4）
- L4 leave-running stack 不再用 → `docker compose -f .../compose.e2e.yml -p ansispire-e2e ... down -v`
- 切分支后跑 L5 → 同 "干净复测"（重新拉镜像）

**永远不动 dev stack**：靠命名隔离（`*-e2e` 后缀 vs 无后缀）。详见 testing-governance.md §9.3。

---

## 4. CI（GitHub Actions）

`.github/workflows/ci.yml` 三 job：
- `yamllint`（全树）
- `ansible-lint --profile production`（注入临时 vault password）
- `syntax-check`（playbook syntax-check 跨 stag + prod）

触发：push 至 `dev|master|hotfix/*`；PR 至 `dev|stg|master`。`stg` 故意 PR-only。

---

## 5. 多平台矩阵

Tier 1（Molecule 真实覆盖）：
- Ubuntu 22.04（`geerlingguy/docker-ubuntu2204-ansible:latest`）
- Debian 12（`geerlingguy/docker-debian12-ansible:latest`）

Tier 2（占位，待 TASK-007）：
- Rocky Linux 9 / Alma 9
- Alpine

---

## 6. 已知缺口（test-plan.md §5 G1–G9）

仍开放：G1（infra_baseline 无 L4）/ G2（hub role 无 molecule）/ G6（nginx remediation 无 L4）/ G7（DB failover 无 L4）/ G8 / G9（详见 `test-plan.md`）。

最近闭合：G3（Debian 12 service-name 兼容，2026-05-12，commit `893b6a7`）/ G4 + G5（4 个 molecule TSVS 落地，2026-05-11，commit `d5f3087`）。

---

## 7. 历史（迁移自旧 SUMMARY 段）

- **环境感知逻辑**：`roles/common` 用 `/proc/net/if_inet6` 探测 IPv6 再配 UFW；SSH 任务用 `stat sshd_config` 避免在最小化容器里 fail
- **依赖自愈**：缺失的系统服务（如 `cron`）显式安装以满足 role handlers
- **配置最佳实践**：`ansible.cfg` 用 `result_format = yaml`；Ansible 2.20.5 把 `ansible_managed` 从 INI 配置移到 `group_vars/all/vars.yml`；molecule 不继承项目级 `PYTHONPATH`，必须在 `molecule.yml` 显式映射 plugin
- **Don't Repeat 教训**：见 [`docs/governance/operational-truths.md`](../../governance/operational-truths.md)
