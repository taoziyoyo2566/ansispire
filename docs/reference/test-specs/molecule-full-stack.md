# 测试规格与验证说明书 (TSVS) - Molecule full-stack 场景

## 1. 测试概览 (Overview)
- **测试 ID**: `TSVS-MOL-FULLSTACK-001`
- **测试类型**: L4 集成测试 (Cross-role Integration / Molecule)
- **优先级**: 高 (P0)
- **测试目的**: 验证 `common + webserver + database` 三个 role 在**同一台主机**上按序部署后，三方产物共存无冲突；并以一条独立的"co-existence assertion"显式校验 nginx 与 mysql 同时处于 `running` 状态。本场景是当前仅有的"多 role 集成"覆盖路径。
- **覆盖表面**: 三个 role 的合成；交叉断言 → [`test-plan.md §4.11`](../../governance/test-plan.md)

## 2. 测试环境 (Environment)
- **驱动**: docker
- **被测平台**:
  - `fullstack-ubuntu22`: `geerlingguy/docker-ubuntu2204-ansible:latest`（Ubuntu 22.04 LTS，systemd）
- **容器参数**: `privileged: true`、`cgroupns_mode: host`、`/sys/fs/cgroup` rw、`command: /lib/systemd/systemd`
- **host_vars**: `db_role: primary`
- **测试 vhost**: `name: fullstack-test.local`、`root: /var/www/fullstack`
- **测试数据库**: `appdb`（utf8mb4），用户 `appuser`（priv `appdb.*:ALL`）
- **root 密码**: `IntegrationTestRoot123!`
- **开放端口**: `firewall_allowed_tcp_ports: [22, 80, 443, 3306]`

## 3. 软件包清单 (Software Stack)
| 软件名称 | 版本号 | 备注 |
| :--- | :--- | :--- |
| ansible-core | 2.20.5 | |
| molecule | >= 24.0.0 | |
| molecule-plugins[docker] | >= 23.5.0 | |
| Python | 3.11 | CI baseline |
| nginx | Ubuntu 22.04 APT 默认 | 由 webserver role 安装 |
| MySQL Server | Ubuntu 22.04 APT 默认（8.0.x 系） | 由 database role 安装 |

## 4. 测试方法与步骤 (Methodology)

### 4.1 前置条件 (Prerequisites)
1. `make setup` 完成。
2. Galaxy 依赖（含 `community.mysql`）已安装。
3. Docker daemon 运行中。
4. group_vars 中三个 role 的输入变量均已注入（由 molecule.yml 显式声明，避免依赖外部 inventory）。

### 4.2 执行步骤 (Steps)
1. **干净验证**：`molecule test -s full-stack`
2. **迭代调试**：`molecule converge -s full-stack && molecule verify -s full-stack`（molecule.yml 顶部注释推荐用法）
3. **登入容器**：`molecule login -s full-stack`

### 4.3 部署顺序与共存假设
- 三 role 按 `playbooks/site.yml` 的顺序在**单一主机**应用：common → webserver → database（或并列由 playbook 编排，具体顺序见 `playbooks/`）。
- 假设：nginx 监听 80，mysql 监听 3306，两者端口不冲突；防火墙仅作为应用层，不实际阻断容器内回环。
- idempotence：第二次 converge **必须 0 changed**（三 role 全部幂等）。

## 5. 预期结果 (Expected Results)

`verify.yml` 当前断言矩阵（按角色分组）：

**common 子集（注：不含 MOTD / UFW 断言）**：
- [x] `ansible_date_time.tz in ['UTC', 'Etc/UTC']`
- [x] `'curl' in ansible_facts.packages`
- [x] `getent passwd appuser` 成功
- [x] `/opt/apps` 存在且为目录

**webserver**：
- [x] `'nginx' in ansible_facts.packages`
- [x] `'nginx.service' in services and services['nginx.service'].state == 'running'`
- [x] `nginx -t` 退出码 0
- [x] `/etc/nginx/sites-available/fullstack-test.local.conf` 存在
- [x] `http://localhost:80` 响应 `[200, 301, 302, 404]`

**database**：
- [x] `'mysql-server' in ansible_facts.packages or 'mysql-server-8.0' in ansible_facts.packages`
- [x] `'mysql.service' in services and services['mysql.service'].state == 'running'`
- [x] `127.0.0.1:3306` 在 5 s 内 `state: started`
- [x] `appdb` 通过 root 密码可见
- [x] `/etc/mysql/mysql.conf.d/mysqld.cnf` 含 `Ansible managed` —— **硬断言**（2026-05-12 **T-C1** 起：移除原 `failed_when: false`，与 `molecule-database.md §5` 第 5 条对齐）

**共存断言（场景特有）**：
- [x] **nginx AND mysql 同时 running**（双 OR 形式兼容 `service` 与 `service.service` 命名变体）

idempotence 阶段：第二次 converge **必须 0 changed**。

### 5.1 未断言的项（已知盲区）
- 跨服务请求（如 nginx → mysql via PHP-FPM）；本场景显式 `php_fpm: false`、`ssl: false`
- 多 vhost / 多数据库
- 防火墙规则在容器内实际生效（容器内 UFW 行为不完全等同物理主机）

### 5.2 与单 role 场景的覆盖关系
- 单 role 场景（common / webserver / database）覆盖各自完整 happy path；本场景**只覆盖三者共存的子集**，避免重复断言爆炸。
- 若单 role 场景已 PASS 但本场景 FAIL，最常见原因是端口冲突 / 用户名冲突 / 防火墙顺序问题。

## 6. 测试执行记录 (Actual Results)
- **执行时间**: 由 CI 持续维护；本 round 2 未触发独立 ad-hoc 运行
- **执行人**: GitHub Actions `molecule` job（matrix scenario = `full-stack`）
- **状态**: 由 CI 状态决定
- **实际表现**:
    > 首次完整执行结果待落地后追溯（plan §6 round 2 仅登记现有断言，不引入新断言）。
- **异常分析**: 无

## 7. 结论与建议 (Conclusion)
- **测试结论**: 当前结构以"common 子集 + webserver 全集 + database 全集 + 共存断言 + idempotence"覆盖三 role 集成；唯一明显口径弱化在 my.cnf 软断言。
- **建议**：
  - ~~**硬化 my.cnf 断言**：移除 `failed_when: false`，使其成为硬断言（与 `molecule-database.md` §5 第 5 条对齐）。~~ ✅ **CLOSED 2026-05-12**（Tier C round 2，T-C1）。
  - **多 distro 扩展**（G3 范围外）：本场景与单 role 场景 G3 不同步。当前仅 Ubuntu 22；如要加 Debian 12 需同时引入 MySQL 上游 APT repo prepare 步骤（见 `molecule-database.md §2`），不在本轮范围。
  - **跨服务交互**：若未来引入 PHP-FPM，本场景应升级为"nginx → PHP → MySQL"三层链路验证。

---
*Carrier: `molecule test -s full-stack` (≈ 2–5 min) | CI `molecule` matrix*
*Registered in: [`docs/reference/test-specs/INDEX.md`](INDEX.md)*
