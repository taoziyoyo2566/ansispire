# 测试规格与验证说明书 (TSVS) - Molecule database 场景

## 1. 测试概览 (Overview)
- **测试 ID**: `TSVS-MOL-DATABASE-001`
- **测试类型**: L4 集成测试 (Integration / Molecule)
- **优先级**: 高 (P0)
- **测试目的**: 验证 `roles/database` 在 Ubuntu 22.04 上部署后，MySQL 服务存活、端口监听、目标数据库创建成功、my.cnf 由 Ansible 管理；并通过 Molecule idempotence 阶段验证二次执行无变更。本场景承担 round-5 修复（`check_implicit_admin: true` 实现 root 密码可重复设置）的回归防线。
- **覆盖表面**: [`roles/database/`](../../../roles/database/) → [`test-plan.md §4.3`](../../governance/test-plan.md)

## 2. 测试环境 (Environment)
- **驱动**: docker
- **被测平台**:
  - `ubuntu22-database`: `geerlingguy/docker-ubuntu2204-ansible:latest`（Ubuntu 22.04 LTS，systemd）
- **容器参数**: `privileged: true`、`cgroupns_mode: host`、`/sys/fs/cgroup` rw、`command: /lib/systemd/systemd`
- **host_vars**: `db_role: primary`（用于角色内分支）
- **测试数据库**: `testdb`（utf8mb4）
- **测试用户**: `testuser`（host `localhost`，对 `testdb.*` ALL）
- **root 密码**：`TestRootPass123!`（molecule.yml `group_vars.all.database__mysql_root_password` —— 同 key 在 YAML 中被声明两次，第二次的值生效，与 verify.yml 使用值一致）
- **端口**: 容器内 3306；MySQL bind 至 `127.0.0.1`

## 3. 软件包清单 (Software Stack)
| 软件名称 | 版本号 | 备注 |
| :--- | :--- | :--- |
| ansible-core | 2.20.5 | |
| molecule | >= 24.0.0 | |
| molecule-plugins[docker] | >= 23.5.0 | |
| Python | 3.11 | CI baseline |
| MySQL Server | 来自 Ubuntu 22.04 APT 默认版本（通常 8.0.x） | 通过 `roles/database` 安装 |

## 4. 测试方法与步骤 (Methodology)

### 4.1 前置条件 (Prerequisites)
1. `make setup` / `pip install -r requirements.txt` 完成。
2. Galaxy 依赖已安装。
3. Docker daemon 运行中。
4. `community.mysql` collection 已通过 `ansible-galaxy collection install -r requirements.yml` 落地（`roles/database` 内 `mysql_user`、`mysql_db` 模块依赖）。

### 4.2 执行步骤 (Steps)
1. **干净验证**：`molecule test -s database`
   - 完整生命周期同上：`dependency → cleanup → destroy → syntax → create → prepare → converge → idempotence → verify → cleanup → destroy`
2. **迭代调试**：`molecule converge -s database`
3. **登入容器**：`molecule login -s database`，便于 `mysql -uroot -p"$DB_ROOT" --socket=...` 直接排查
4. **手动 verify**：`molecule verify -s database`

### 4.3 round-5 idempotence 修复回归路径
第二次 converge 必须能在 root 密码已设置的情况下重新跑通——这正是 round-5 引入 `check_implicit_admin: true` 解决的问题（首次跑时密码为空 → 第二次跑时密码已存在）。Molecule 内置的 idempotence 阶段就是这条修复的自动化回归防线。

## 5. 预期结果 (Expected Results)

`verify.yml` 5 项断言全部 PASS：

- [x] `'mysql' in services or 'mysqld' in services`（兼容 service 名差异；硬断言）
- [x] `127.0.0.1:3306` 在 10 s 内 `state: started`（`ansible.builtin.wait_for`）
- [x] `mysql -u root -p'<TestRootPass123!>' --socket=/var/run/mysqld/mysqld.sock -e "SHOW DATABASES LIKE 'testdb';"` 输出包含 `testdb`
- [x] 文件 `/etc/mysql/mysql.conf.d/mysqld.cnf` 存在
- [x] `grep -q "Ansible" /etc/mysql/mysql.conf.d/mysqld.cnf` 退出码 0（硬断言，无 `failed_when: false`）

idempotence 阶段：第二次 converge **必须 0 changed**（=root 密码、用户、数据库、my.cnf 模板渲染全部幂等）。

### 5.1 未断言的项（已知盲区，登记给未来 TSVS）
- `testuser` 实际可登录 + 拥有 `testdb.* ALL` 权限（用户/权限只验证 Ansible 任务返回 ok，未实际 `mysql -u testuser ...` 验证授权）
- 备份脚本（`database__backup_enabled: false` 显式关闭，无法在本场景验证）
- replication 状态（场景仅 `primary`，无 secondary）
- `innodb_buffer_pool_size`、`max_connections` 等运行时参数是否被 MySQL 真正加载

## 6. 测试执行记录 (Actual Results)
- **执行时间**: 由 CI 持续维护；本 round 2 未触发独立 ad-hoc 运行
- **执行人**: GitHub Actions `molecule` job（matrix scenario = `database`）
- **状态**: 由 CI 状态决定
- **实际表现**:
    > 首次完整执行结果待落地后追溯（plan §6 round 2 仅登记现有断言，不引入新断言）。
- **异常分析**: 无（round-5 idempotence 修复后未观察到回归）

## 7. 结论与建议 (Conclusion)
- **测试结论**: 当前结构以"服务存活 + 端口监听 + 目标库创建 + my.cnf 被 Ansible 管理 + idempotence" 5 条覆盖 database role 的 happy path；可回归 round-5 二次执行权限错误 bug。
- **建议**：
  - **多 distro 扩展**（G3）：当前仅 Ubuntu 22.04。
  - **用户权限实测**：补 `mysql -u testuser` 实际授权验证，提升断言力度。
  - **备份子场景**：可作为独立 TSVS 引入（开启 `database__backup_enabled: true`）。
  - **YAML 重复 key**：`database__mysql_root_password` 在场景 group_vars 中重复声明（最终值生效，但有歧义），建议下次维护时移除冗余。

---
*Carrier: `molecule test -s database` (≈ 2–5 min) | CI `molecule` matrix*
*Registered in: [`docs/reference/test-specs/INDEX.md`](INDEX.md)*
