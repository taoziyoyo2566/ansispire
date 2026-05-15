# Round 3 变更日志

日期: 2026-04-09
执行者: Claude (Sonnet 4.6)

---

## 变更列表

| 文件 | 变更类型 | 摘要 |
|------|---------|------|
| `inventory/production/group_vars/all/vault.yml` | git rm --cached | 从 git 追踪中移除；文件保留磁盘，.gitignore 已覆盖 |
| `roles/common/meta/main.yml` | 修改 | 新增 EL 平台（Rocky 9 Tier 1 已验证；Alma 预期兼容）|
| `roles/database/meta/argument_specs.yml` | 修改 | 移除 "Rocky Linux 9+ Tier 1" 过度声明，改为 Tier 2 说明 |
| `README.md` | 修改 | 平台矩阵: Rocky ✅ vs AlmaLinux 9 ⚠（拆行区分）|
| `playbooks/vault_demo.yml` | 修改 | 全部路径从 `group_vars/all/vault.yml` 改为 `inventory/production/group_vars/all/vault.yml` |

---

## 关闭的问题

| ID | 来源 | 问题 | 结论 |
|----|------|------|------|
| Codex-R3 #1 | Codex Round 3 | Vault 方案 B 未落地（vault.yml 仍被 git 追踪）| ✅ 已落地 |
| Codex-R3 #2 | Codex Round 3 | common meta/main.yml 未声明 RedHat 平台 | ✅ 已落地 |
| Codex-R3 #3 | Codex Round 3 | database argument_specs 过度声明 Rocky Tier 1 | ✅ 已落地 |
| Codex-R3 #4 | Codex Round 3 | README AlmaLinux 9 与 Rocky 9 混在同一 ✅ 行 | ✅ 已落地 |
| Codex-R3 #5 | Codex Round 3 | vault_demo.yml 使用旧路径 | ✅ 已落地 |

---

## 未关闭问题（移交下轮）

| ID | 问题 | 优先级 |
|----|------|--------|
| R2-1 | examples/ 中 `when: false` 改 `tags: [never]` | 低 |
| R3-1 | molecule/common/verify.yml 无 firewalld 断言 | 低 |
| R3-2 | database role 无 RedHat 路径（Tier 2 骨架未实现）| 低 |
