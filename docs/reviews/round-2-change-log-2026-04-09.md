# Round 2 变更日志

日期: 2026-04-09
执行者: Claude (Sonnet 4.6)

---

## 变更列表

### 修改文件

| 文件 | 变更摘要 |
|------|---------|
| `roles/common/tasks/preflight.yml` | 从 Debian-only 改为 Tier 1/2 分层：接受 Debian+RedHat，非 Tier 1 warn 不 fail |
| `roles/common/tasks/security.yml` | UFW 加 `when: Debian` 守卫，新增 firewalld 路径（RedHat），dpkg-query 改为 package_facts |
| `roles/common/vars/os/Debian.yml` | 新增 `_common__firewall_pkg`、`_common__firewall_service` |
| `roles/common/vars/os/RedHat.yml` | 新增 `_common__firewall_pkg`、`_common__firewall_service` |
| `roles/common/templates/motd.j2` | 移除 `\| env_badge` 自定义过滤器依赖，改为内联 Jinja2 字典 |
| `roles/database/defaults/main.yml` | 移除 `database__mysql_root_password` 默认值 |
| `roles/database/meta/argument_specs.yml` | 补充设计说明注释（为何 required: true 且无默认值）|
| `playbooks/rolling_update.yml` | lb_host 变量化，app_repo 改为占位符，新增前置 assert，标注为参考模板 |
| `execution-environment.yml` | python 依赖中加入 `ansible-lint>=24.9` |
| `.gitignore` | 加入 `inventory/**/vault.yml` 排除规则 |
| `molecule/common/molecule.yml` | 新增 Rocky Linux 9 平台（Tier 1 RedHat）|
| `.github/workflows/ci.yml` | common 场景现覆盖 Ubuntu + Rocky 双平台 |
| `callback_plugins/human_log.py` | 修复 skipped 事件处理、_elapsed() 保护、ignore_errors 颜色；标注为演示型 |
| `README.md` | 全面同步：平台矩阵、新目录结构、vault 工作流、examples/ 路径、Molecule 场景 |

### 新增文件

| 文件 | 说明 |
|------|------|
| `docs/reviews/claude-review-round-2-2026-04-09.md` | 本轮 Claude 审查文档 |
| `docs/reviews/round-2-change-log-2026-04-09.md` | 本文件 |

---

## 关闭的问题

来自 Codex Round 2 待办清单：

| ID | 问题 | 结论 |
|----|------|------|
| TODO-1 | argument_specs required+default 冲突 | ✅ 已落地 |
| TODO-2 | preflight 保留 RedHat 声明与收窄矛盾 | ✅ 已落地（改为分层，不收窄）|
| TODO-3 | README 未同步新结构 | ✅ 已落地 |
| TODO-4 | Vault 工作流未定型 | ✅ 已落地（选方案 B）|
| TODO-5 | rolling_update.yml 硬编码 | ✅ 已落地 |
| N4 | motd.j2 filter_plugins 依赖 | ✅ 已落地 |
| N7 | EE ansible-lint 自洽 | ✅ 已落地 |
| N8 | callback 边缘情况 | ✅ 已落地（演示级）|

---

## 未关闭问题（移交下轮）

| ID | 问题 | 优先级 |
|----|------|--------|
| R2-1 | examples/ 中 `when: false` 改 `tags: [never]` | 低 |
| R2-2 | Molecule Tier 2 平台（Debian 11/12）| 低 |
| R2-3 | webserver/database role 无 RedHat 路径 | 低（Tier 2 可接受）|
