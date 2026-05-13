# 测试规格与验证说明书 (TSVS) - Molecule common 场景

## 1. 测试概览 (Overview)
- **测试 ID**: `TSVS-MOL-COMMON-001`
- **测试类型**: L4 集成测试 (Integration / Molecule)
- **优先级**: 高 (P0)
- **测试目的**: 验证 `roles/common` 在两个 Debian-系发行版（Ubuntu 22.04、Debian 12）上部署后，时区、基础包、UFW（含 round-5 修复的 lo 规则间接前置）、MOTD、应用目录、应用用户六项部署期产物正确成立；并通过 Molecule idempotence 阶段验证二次执行无变更。
- **覆盖表面**: [`roles/common/`](../../../roles/common/) → [`test-plan.md §4.1`](../../governance/test-plan.md)

## 2. 测试环境 (Environment)
- **驱动**: docker（`molecule-plugins[docker]`）
- **被测平台**:
  - `ubuntu22-node`: `geerlingguy/docker-ubuntu2204-ansible:latest`（Ubuntu 22.04 LTS，systemd）
  - `debian12-node`: `geerlingguy/docker-debian12-ansible:latest`（Debian 12 Bookworm，systemd）
- **容器参数**: `privileged: true`、`cgroupns_mode: host`、挂载 `/sys/fs/cgroup`、`command: /lib/systemd/systemd`（为确保 systemd 在容器内可用）
- **inventory 分组**: 两节点均归入 `tier1_debian`
- **执行宿主**: 任何能跑 docker 的 Linux/macOS 工作站；CI 使用 `ubuntu-latest`

## 3. 软件包清单 (Software Stack)
| 软件名称 | 版本号 | 备注 |
| :--- | :--- | :--- |
| ansible-core | 2.20.5 | 来自 `requirements.txt` |
| molecule | >= 24.0.0 | 同上 |
| molecule-plugins[docker] | >= 23.5.0 | 同上 |
| Python | 3.11 | CI baseline |
| Docker | host runtime | 任意支持 cgroup v2 的版本 |

## 4. 测试方法与步骤 (Methodology)

### 4.1 前置条件 (Prerequisites)
1. `make setup` 或等效 `pip install -r requirements.txt` 已完成。
2. `ansible-galaxy collection install -r requirements.yml` 已就绪。
3. Docker daemon 运行中、当前用户可访问 docker socket。
4. 工作目录为项目根；环境变量 `ANSIBLE_FILTER_PLUGINS=../../filter_plugins`（由 molecule.yml 注入）。

### 4.2 执行步骤 (Steps)
1. **干净验证**：`molecule test -s common`
   - `dependency` → `cleanup` → `destroy` → `syntax` → `create`（双容器）→ `prepare`（`prepare.yml`）→ `converge`（应用 `roles/common`）→ `idempotence`（再次 converge，应零变更）→ `verify`（`verify.yml`）→ `cleanup` → `destroy`
2. **迭代调试**：`molecule converge -s common`，保留容器；调试结束以 `molecule test -s common` 做干净复跑
3. **登入容器现场排错**：`molecule login -s common -h ubuntu22-node` 或 `... -h debian12-node`

## 5. 预期结果 (Expected Results)

`verify.yml` 在 **每个平台** 上独立执行；以下 6 条全部 PASS 视为通过：

- [x] 时区 `ansible_date_time.tz == 'UTC'`
- [x] `'curl' in ansible_facts.packages`
- [x] **Debian 系条件断言**：`ansible_facts['os_family'] == 'Debian' and common_ufw_enabled | default(true)` 成立时，`'ufw' in ansible_facts.packages`
- [x] `/etc/motd` 文件存在
- [x] `/etc/motd` 内容包含字符串 `Ansible`（通过 `grep "Ansible" /etc/motd`，无 `failed_when: false`，硬断言）
- [x] `{{ app_base_dir | default('/opt/apps') }}` 既存在又是目录
- [x] `{{ app_user | default('appuser') }}` 存在于 `passwd`（`ansible.builtin.getent`）

并且 idempotence 阶段：第二次 converge **必须 0 changed**（这是 Molecule 内置阶段，非 `verify.yml` 任务，但等同于一条"幂等性"断言）。

### 5.1 未断言的项（已知盲区，登记给未来 TSVS）
- UFW **规则内容**（round-5 修复的 `ufw allow in on lo`、`firewall_allowed_tcp_ports` 是否真的逐条 enabled）—— 对应 [`test-plan.md §5 G9`](../../governance/test-plan.md)
- SSH 加固结果（`PermitRootLogin`、`PasswordAuthentication` 是否实际被改写）
- `common__deploy_users` 创建的用户细节权限
- `common__sysctl_settings` 是否在 `/etc/sysctl.d/` 落盘

## 6. 测试执行记录 (Actual Results)
- **执行时间**: 由 CI 持续维护；本 round 2 未触发独立 ad-hoc 运行
- **执行人**: GitHub Actions `molecule` job（matrix scenario = `common`）
- **状态**: 由 CI 状态决定 —— 见 `.github/workflows/ci.yml` 的 `molecule` job 历史
- **实际表现**:
    > 首次完整执行结果待落地后追溯（plan §6 round 2 仅登记现有断言，不引入新断言）。
- **异常分析**: 无（round-5 修复后未观察到回归）

## 7. 结论与建议 (Conclusion)
- **测试结论**: 当前结构以"部署期产物 6 条 + idempotence"覆盖 common role 的 happy path；round-5 已通过本场景捕获并修复 `ufw allow in on lo` 缺失。
- **建议**：
  - **G9 收口**：未来引入 UFW 规则内容断言（解析 `ufw status numbered` 输出或读 `/etc/ufw/before.rules`）。
  - **跨发行版扩展**：已覆盖 Ubuntu 22 + Debian 12；若回归到 Debian 11 / Ubuntu 20，须新增平台（详见 [`test-plan.md §5 G3`](../../governance/test-plan.md)）。

---
*Carrier: `molecule test -s common` (≈ 2–5 min) | `make verify-full` 串行链 | CI `molecule` matrix*
*Registered in: [`docs/reference/test-specs/INDEX.md`](INDEX.md)*
