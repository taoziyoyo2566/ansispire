# Claude Round 4 Brief

日期: 2026-04-09
参照:
- [Review Iteration Charter](./review-iteration-charter.md)
- [Platform Support Addendum](./platform-support-addendum-2026-04-09.md)
- [Claude 审查报告 — Round 2](./claude-review-round-2-2026-04-09.md)
- [Codex Review — Round 3](./codex-review-round-3-2026-04-09.md)

## 原始目的

本仓库是用于学习和理解 Ansible 功能、特性、最佳实践与平台差异的 demo。

这轮不是继续扩展功能，而是把已经宣布“已落地”的内容真正收口，避免:
- 文档领先于代码
- 支持声明领先于实现
- `.gitignore` 方案与仓库真实状态不一致

## 本轮关注范围

1. 收口 Vault 方案 B
2. 收口平台支持矩阵在 meta / README / preflight / Molecule 之间的差异
3. 修正文档中对 Rocky / Alma / database role 的过度声明
4. 同步 `playbooks/vault_demo.yml` 的路径与当前仓库结构

## 本轮不展开

- 不恢复或扩展新的平台实现
- 不新增新 role / 新场景
- 不继续讨论 `examples/advanced_patterns.yml` 的 `when: false`

## 判断标准

- 是否减少误导
- 是否让默认路径更自洽
- 是否把“方向正确”收口成“仓库事实一致”

## 你需要修的具体问题

### 1. Vault 方案 B 目前未真正落地

问题:
- `.gitignore` 已排除 `inventory/**/vault.yml`
- 但 `inventory/production/group_vars/all/vault.yml` 仍是已被 git 跟踪的文件

这意味着:
- README 中“默认不提交明文 vault.yml”的说法没有和仓库事实对齐
- `.gitignore` 只对未来新文件有效，对当前文件无效

建议你二选一，但必须让仓库事实一致:

方案 B1:
- 从 git 中移除 `inventory/production/group_vars/all/vault.yml`
- 保留 `vault.example.yml`
- README 明确“复制示例 -> 本地生成 -> 加密 -> 不纳入 git”

方案 B2:
- 保留 `vault.yml` 被跟踪
- 那就不要再称其为“方案 B 不提交 vault.yml”
- README 和 docs 改成“仓库中保留占位版/示例版”

倾向:
- 优先 B1，更符合当前 charter 和 README 叙述

请核对:
- `.gitignore`
- `README.md`
- `inventory/production/group_vars/all/vault.yml`
- `inventory/production/group_vars/all/vault.example.yml`

### 2. `common` role 的平台声明仍未完全同步

当前状态:
- `preflight.yml` 已接受 Debian + RedHat family
- `molecule/common` 已有 Rocky 9
- README 也写了 Rocky / Alma Tier 1
- 但 `roles/common/meta/main.yml` 仍只列 Ubuntu / Debian

你需要决定:
- 是补 `common/meta/main.yml` 的 RedHat-compatible 平台声明
- 还是把 README / docs 收窄为“common role 的 RedHat family 只在 preflight 和 Molecule common 场景演示”

默认倾向:
- 对齐到“common role 支持 Debian + RedHat family 的 Tier 1/2 分层”

### 3. `database` role 现在有过度声明

当前状态:
- `roles/database/meta/main.yml` 仍只写 Ubuntu
- `roles/database/tasks/install.yml` 仍明显是 Ubuntu 路线
- `molecule/database` 也只有 Ubuntu
- 但 `roles/database/meta/argument_specs.yml` 描述里写了 Rocky Linux 9+ Tier 1

这属于典型的“文档/规格超前于实现”。

你需要收口成一致状态，优先选下面这个方向:

- `database` role 仍明确标记为 Tier 1: Ubuntu
- RedHat-compatible 只保留在项目级平台矩阵或 future work 中
- 不要在 `database` role 自身文档里宣称 Rocky Tier 1

请核对:
- `roles/database/meta/main.yml`
- `roles/database/meta/argument_specs.yml`
- `roles/database/tasks/install.yml`
- `README.md`

### 4. README 对 Rocky / Alma 的验证范围写得过满

当前:
- README 写 `Rocky Linux 9 / AlmaLinux 9 | ✅ | common 场景测试`
- 实际只有 Rocky 9 出现在 `molecule/common/molecule.yml`

你需要修成两种一致方案之一:

方案 A:
- README 改成 “Rocky Linux 9 ✅；AlmaLinux 9 预期兼容/未验证”

方案 B:
- 如果你确实补了 AlmaLinux 9 场景，再保留现有说法

默认倾向:
- 方案 A，避免继续扩大声明

### 5. `playbooks/vault_demo.yml` 仍使用旧路径

当前文件仍写:
- `group_vars/all/vault.yml`

而当前仓库标准路径已经是:
- `inventory/production/group_vars/all/vault.yml`

你需要把:
- 注释中的命令
- 变量来源说明

全部同步到当前路径。

## 输出要求

你的审查/修复文档开头必须包含:

```md
## 原始目的
## 本轮关注范围
## 本轮不展开
## 判断标准
```

结论状态只允许使用:
- 已落地
- 已部分落地
- 方向确认，尚未收口

## 证据要求

每个“已落地”项，至少附以下核对:

| 项目 | 文件 | 状态 |
|------|------|------|
| 代码 | ... | ... |
| README/docs | ... | ... |
| meta/specs | ... | ... |
| 测试或仓库状态 | ... | ... |

其中 Vault 项请额外检查:
- `git ls-files inventory/production/group_vars/all/vault.yml`

如果它仍有输出，就不能宣称“方案 B 已落地”。

