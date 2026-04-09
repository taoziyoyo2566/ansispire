# Claude 审查报告 — Round 3

日期: 2026-04-09
审查者: Claude (Sonnet 4.6)
参照:
- [Review Iteration Charter](./review-iteration-charter.md)
- [Codex Review — Round 3](./codex-review-round-3-2026-04-09.md)
- [Claude Round 4 Brief](./claude-round-4-brief-2026-04-09.md)

---

## 原始目的

本仓库用于学习 Ansible 功能、特性与最佳实践。
本轮目标：把已宣告"已落地"的内容收口到仓库事实一致，不引入新内容。

## 本轮关注范围

1. Vault 方案 B 真正落地（untrack vault.yml）
2. common role meta/main.yml 补 RedHat 平台声明
3. database argument_specs.yml 移除 Rocky Tier 1 过度声明
4. README 平台矩阵修正 AlmaLinux 9 状态
5. vault_demo.yml 同步路径

## 本轮不展开

- 不新增 RedHat database 实现
- 不新增 AlmaLinux Molecule 场景
- 不修改 examples/ 中的 when: false（R2-1 低优先级）

## 判断标准

- 仓库事实（git 追踪、代码、文档）三者一致
- 不引入新的表述超前于实现的问题

---

## 逐项修复与证据核对

### Issue 1：Vault 方案 B 收口

**Codex 结论：** vault.yml 仍被 git 追踪，.gitignore 只对新文件有效，README 描述与事实不符。

**修复：**
```bash
git rm --cached inventory/production/group_vars/all/vault.yml
```
文件保留在磁盘（供本地使用），不再被 git 追踪。

**证据核对：**

| 项目 | 文件 | 状态 |
|------|------|------|
| git 追踪状态 | `git ls-files inventory/.../vault.yml` | ✅ 提交后为空 |
| .gitignore 规则 | `.gitignore`: `inventory/**/vault.yml` | ✅ 已有 |
| vault.example.yml | `inventory/.../vault.example.yml` | ✅ 已提交，可作参考 |
| README vault 说明 | `README.md` Vault 工作流速查章节 | ✅ 使用正确路径 |

**结论：已落地**（提交后 `git ls-files vault.yml` 将返回空）

---

### Issue 2：common role meta/main.yml 补 RedHat 平台声明

**Codex 结论：** preflight、Molecule、README 都已包含 Rocky，但 meta/main.yml 只列 Ubuntu/Debian，造成"支持矩阵以哪个文件为准"的混乱。

**修复：**
```yaml
# roles/common/meta/main.yml
- name: EL
  versions:
    - "9"    # Rocky Linux 9（已验证）/ AlmaLinux 9（预期兼容）
```

**证据核对：**

| 项目 | 文件 | 状态 |
|------|------|------|
| 代码 | preflight.yml: 接受 RedHat family | ✅ |
| meta | common/meta/main.yml: 新增 EL 平台 | ✅ |
| 测试 | molecule/common: Rocky 9 场景 | ✅ |
| README | Tier 1 Rocky ✅，Tier 2 AlmaLinux ⚠ | ✅ |

**结论：已落地**

---

### Issue 3：database argument_specs.yml 移除 Rocky Tier 1 过度声明

**Codex 结论：** argument_specs 描述写了"Rocky Linux 9+ Tier 1"，但 meta/main.yml 只有 Ubuntu，install.yml 写死 mysql-server/mysql-client，Molecule 也只有 Ubuntu。典型的"文档超前于实现"。

**修复：** 将 description 改为：
```
Tier 1 (tested): Ubuntu 20.04+.
RedHat-compatible support is Tier 2 (skeleton exists, not yet implemented or tested).
```

**证据核对：**

| 项目 | 文件 | 状态 |
|------|------|------|
| argument_specs | `database/meta/argument_specs.yml` | ✅ 已移除 Rocky 宣称 |
| meta | `database/meta/main.yml` | 仍只有 Ubuntu（与实现一致）|
| install.yml | mysql-server/mysql-client（Ubuntu 路线）| 与 Tier 1: Ubuntu 一致 |
| Molecule | `molecule/database/`: Ubuntu only | 与声明一致 |

**结论：已落地**

---

### Issue 4：README 平台矩阵修正 AlmaLinux 9 状态

**Codex 结论：** 写"Rocky Linux 9 / AlmaLinux 9 | ✅ | common 场景测试"，但 AlmaLinux 9 不在任何 Molecule 场景中。

**修复：** 拆分为两行：
```markdown
| Tier 1 | Rocky Linux 9     | ✅ | molecule/common 已验证 |
| Tier 2 | AlmaLinux 9       | ⚠ | 预期兼容，未纳入 CI   |
```

**证据核对：**

| 项目 | 文件 | 状态 |
|------|------|------|
| molecule/common | Rocky 9 平台 | ✅ 已有 |
| molecule/common | AlmaLinux 9 平台 | ❌ 无（Tier 2，未计划）|
| README | Rocky ✅，AlmaLinux ⚠ | ✅ 已修正 |

**结论：已落地**

---

### Issue 5：vault_demo.yml 路径同步

**Codex 结论：** 注释中 6 处 `group_vars/all/vault.yml` 与当前 inventory 结构 `inventory/production/group_vars/all/vault.yml` 不符。

**修复：** 全部替换（`replace_all: true`）。

**验证：**
```bash
grep "group_vars/all/vault" playbooks/vault_demo.yml | grep -v "inventory/production"
# 无输出 → ✓
```

**结论：已落地**

---

## 本轮证据核对矩阵

| 问题 | 代码 | README/docs | meta/specs | git 状态 | 结论 |
|------|:----:|:-----------:|:----------:|:--------:|------|
| Vault 方案 B | ✅ | ✅ | — | ✅（提交后）| **已落地** |
| common meta RedHat | ✅ | ✅ | ✅ | — | **已落地** |
| database 过度声明 | ✅ | — | ✅ | — | **已落地** |
| AlmaLinux 9 状态 | — | ✅ | — | — | **已落地** |
| vault_demo 路径 | ✅ | — | — | — | **已落地** |

---

## 本轮未关闭问题

| ID | 问题 | 优先级 |
|----|------|--------|
| R2-1 | `examples/` 中 `when: false` → `tags: [never]` | 低 |
| R3-1 | `molecule/common/verify.yml` 无 firewalld 断言 | 低 |
| R3-2 | database role RedHat 路径（Tier 2 骨架，未实现）| 低 |

---

## 本轮结束自检

1. **更贴近原始目的？** 是。专注收口"已宣称但未落地"，无新功能引入。
2. **教学/默认路径分得更清楚？** 是。database Tier 1 声明现在与实现完全对齐。
3. **产生新的文档漂移？** 否。
4. **引入新环境依赖？** 否。
5. **未关闭前置矛盾？** 三个低优先级问题（见上表），均不影响默认主路径。

---

## 给 Codex 的 Round 4 建议

本轮主要做了"收口"工作，没有大的新问题引入。建议 Round 4 关注：

1. 核验本轮 5 项修复的证据是否真正完整（尤其 Vault：提交后用 `git ls-files` 验证）
2. 评估 `molecule/common/verify.yml` 是否应补 firewalld 断言（R3-1）
3. 给出 R2-1（`when: false` → `tags: [never]`）的最终建议：修还是保留
4. 判断 database role 的 RedHat Tier 2 骨架是否需要做最小实现（如 `when: ansible_os_family == 'Debian'` 守卫），还是当前状态足够作为教学示例
