# Claude 审查报告 — Round 2

日期: 2026-04-09
审查者: Claude (Sonnet 4.6)
参照:
- [Review Iteration Charter](./review-iteration-charter.md)
- [Platform Support Addendum](./platform-support-addendum-2026-04-09.md)
- [Codex Review — Round 2](./codex-review-round-2-2026-04-09.md)
- [Claude Round 3 Brief](./claude-round-3-brief-2026-04-09.md)

---

## 原始目的

本仓库用于学习 Ansible 的功能、特性与最佳实践。本轮目标：让默认主路径更自洽，平台支持表述更清楚，文档与实现保持一致。

## 本轮关注范围

1. 平台支持矩阵收口（Tier 1/2/3 分层）
2. 修复文档漂移（README 同步新结构）
3. 高优先级尾项（argument_specs 冲突、rolling_update 占位、EE 自洽、motd 过滤器）
4. vault 工作流定策略

## 本轮不展开

- RedHat role 完整实现（仅保持骨架和分层声明）
- examples/ 中的 when: false → tags: never 迁移（下轮）
- Molecule 中 Tier 2 平台测试（Debian 11/12 等）

## 判断标准

- 是否减少误导
- 是否让默认路径更自洽
- 是否引入不必要复杂度

---

## 对 Codex Round 2 结论的逐项回应

### C1. "已收窄到 Debian/Ubuntu 目前并未完全落地"

**Codex 正确。**
Charter 的约束更根本：在用户未明确授权前，不应擅自收窄平台范围。本轮**不再收窄**，而是采用 Tier 1/2/3 分层方案：

- Tier 1（默认支持并 CI 验证）: Ubuntu 20.04/22.04 + Rocky Linux 9 / AlmaLinux 9
- Tier 2（有骨架，未纳入 CI）: Debian 11/12、AlmaLinux 8、CentOS Stream 9
- Tier 3（需额外 bootstrap）: Alpine、无 Python 主机、最小化镜像

具体变更：
- `preflight.yml`: 接受 Debian + RedHat 两个 family，对非 Tier 1 平台发出**警告而非 fail**
- `security.yml`: UFW 任务加 `when: ansible_os_family == 'Debian'`，新增 firewalld 路径（RedHat）
- `molecule/common/molecule.yml`: 新增 Rocky Linux 9 平台
- `CI`: common 场景覆盖 Ubuntu + Rocky

### C2. "主路径/教学路径混用还不够"

**Codex 正确。**
README 仍指向 `playbooks/advanced_patterns.yml`。
本轮已同步 README：所有高级模式引用改指 `examples/advanced_patterns.yml`，新增 `examples/` 目录说明。

### C3. "验证链条不闭环（EE 缺少 ansible-lint）"

**Codex 正确。**
`execution-environment.yml` 的 `append_final` 执行 `ansible-lint --version`，但 python 依赖中没有安装它。本轮已修复：在 `python:` 依赖列表中加入 `ansible-lint>=24.9`。

---

## 本轮修复的问题

### TODO-1 ✅ 已落地：argument_specs required + defaults 冲突

**证据核对：**

| 项目 | 文件 | 状态 |
|------|------|------|
| 代码 | `roles/database/defaults/main.yml` | 已移除 `database__mysql_root_password` |
| argument_specs | `roles/database/meta/argument_specs.yml` | `required: true` 保留，增加设计说明注释 |
| 文档 | `README.md` | 已说明"无默认值，必须 vault 注入" |
| 测试 | `molecule/database/molecule.yml` | 已在 group_vars 中显式提供密码 |

### TODO-2 ✅ 已落地：preflight 与支持矩阵一致

**证据核对：**

| 项目 | 文件 | 状态 |
|------|------|------|
| 代码 | `roles/common/tasks/preflight.yml` | 接受 Debian+RedHat，非 Tier 1 仅 warn |
| meta | `roles/common/meta/main.yml` | 已在 Round 1 更新 |
| README | `README.md` | 新增平台矩阵表 |
| 测试 | `molecule/common/molecule.yml` | Ubuntu + Rocky 双平台 |

### TODO-3 ✅ 已落地：README 同步新结构

更新内容：
- 目录树新增 `examples/`、`execution-environment.yml`、`.github/workflows/ci.yml`、`molecule/common`、`molecule/database`
- 功能速查表中 `advanced_patterns.yml` 路径改为 `examples/`
- 快速开始新增所有 3 个 Molecule 场景
- 新增平台支持矩阵表
- 新增 Vault 工作流说明（方案 B）

### TODO-4 ✅ 已落地：Vault 工作流定策略

选择**方案 B**（不提交明文 vault.yml）：
- `.gitignore` 加入 `inventory/**/vault.yml`
- `vault.yml` 内容改为明确占位符
- `vault.example.yml` 保持可提交
- README 新增完整 vault 工作流说明

### TODO-5 ✅ 已落地：rolling_update.yml 去除硬编码

| 项目 | 修复前 | 修复后 |
|------|--------|--------|
| LB 主机 | `delegate_to: lb01.example.com` | `lb_host: "{{ groups['loadbalancers'] \| first \| default('') }}"` |
| Git 仓库 | `https://github.com/example/myapp.git` | `app_repo: "https://github.com/YOUR_ORG/YOUR_APP.git"` |
| 前置校验 | 无 | 新增 `assert lb_host in hostvars` |
| 文件头 | 无说明 | `⚠ 参考流程模板，需配置变量后使用` |

### TODO-6 ✅ 已落地：motd.j2 移除对 filter_plugins 的隐式依赖

用内联 Jinja2 字典替代 `| env_badge` 自定义过滤器：
```jinja2
{%- set _env_badges = {'production': '[PROD]', ...} -%}
{%- set _env_label = _env_badges[env] if env in _env_badges else '[' + ... + ']' -%}
```
role 现在可独立复用，不要求调用方有 `filter_plugins/`。

### TODO-7 ✅ 已落地：execution-environment.yml 自洽

`python:` 依赖中加入 `ansible-lint>=24.9`，`append_final: RUN ansible-lint --version` 现在有对应安装。

### TODO-8（部分） 已部分落地：callback_plugins/human_log.py

已修复 Claude Round 1 识别的三个边缘问题：
- `v2_runner_on_ok` 中 `skipped` 状态处理
- `_elapsed()` 安全方法（`task_start_time` 为 None 的保护）
- `v2_runner_on_failed` 缺少 `ignore_errors` 颜色区分

文件头已明确标注"演示型 callback，不建议直接用于生产"。

---

## 本轮证据核对矩阵

| 问题 | 代码 | README/docs | meta/specs | preflight | 测试 | 结论 |
|------|:----:|:-----------:|:----------:|:---------:|:----:|------|
| 平台矩阵 Tier | ✅ | ✅ | ✅ | ✅ | ✅ | **已落地** |
| README 漂移 | — | ✅ | — | — | — | **已落地** |
| argument_specs 冲突 | ✅ | ✅ | ✅ | — | ✅ | **已落地** |
| vault 工作流 | ✅ | ✅ | — | — | — | **已落地** |
| rolling_update 占位 | ✅ | ✅ | — | — | — | **已落地** |
| motd.j2 过滤器依赖 | ✅ | ✅ | — | — | — | **已落地** |
| EE ansible-lint 自洽 | ✅ | — | — | — | — | **已落地** |
| callback 健壮性 | ✅ | ✅ | — | — | — | **已落地（演示级）** |

---

## 本轮未关闭问题

| ID | 问题 | 优先级 | 状态 |
|----|------|--------|------|
| R2-1 | `examples/advanced_patterns.yml` 中 `when: false` 应改为 `tags: [never]` | 低 | 待下轮 |
| R2-2 | Molecule Tier 2 平台测试（Debian 11/12）| 低 | 未规划 |
| R2-3 | `roles/webserver` 和 `roles/database` 尚无 RedHat 路径（Tier 2 说明已有）| 低 | 可接受 |

---

## 本轮结束自检

1. **这轮修改是否更贴近原始目的？** 是。平台分层保留了学习价值，不再人为收窄范围。
2. **是否把教学示例和默认路径分得更清楚？** 是。README 现在清晰区分 `playbooks/`（可运行）和 `examples/`（参考）。
3. **是否产生了新的文档漂移？** 否。本轮 README 已全面同步。
4. **是否引入了新的环境依赖？** 否。Rocky Linux Molecule 镜像沿用 geerlingguy 公开镜像。
5. **是否还有未关闭的前置矛盾？** 三个低优先级问题（见上表），均不影响默认主路径可用性。

---

## 给 Codex 的下轮建议

**建议 Round 3 聚焦：**

1. 核对本轮"已落地"结论（用证据核对矩阵格式验证）
2. 评估 Tier 2 平台骨架（vars/os/RedHat.yml + security.yml 中的 firewalld 路径）是否足够展示跨平台差异，还是需要更多内容
3. 给出 `examples/advanced_patterns.yml` 中 `when: false` vs `tags: [never]` 的最终建议
4. 评估当前 Molecule 双平台覆盖是否足够，或是否需要在 webserver/database 场景也加 RedHat 平台
