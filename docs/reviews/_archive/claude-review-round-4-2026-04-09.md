# Claude 审查报告 — Round 4

日期: 2026-04-09
审查者: Claude (Sonnet 4.6)
参照:
- [Review Iteration Charter](./review-iteration-charter.md)
- [Codex Review — Round 4](./codex-review-round-4-2026-04-09.md)
- [Round 4 变更日志](./round-4-change-log-2026-04-09.md)
- [Claude Round 5 Brief](./claude-round-5-brief-2026-04-09.md)

---

## 原始目的

本仓库用于学习 Ansible 功能、特性与最佳实践。
本轮目标：审查 Codex Round 4 的 3 处收尾改动是否合理，并判断当前是否可以结束这一阶段的 review 迭代。

## 本轮关注范围

1. `examples/advanced_patterns.yml`：`when: false` → `tags: [never, example]`
2. `molecule/common/verify.yml`：新增 UFW / firewalld 断言
3. `roles/database/meta/argument_specs.yml`：最后一处旧 Vault 路径修正

## 本轮不展开

- 不新增平台支持或 role 实现
- 不做大范围 README 重写
- 不开新的功能迭代

## 判断标准

- 改动是否减少误导
- 是否引入新的歧义或复杂度
- 当前阶段是否足以结束

---

## 逐项评估

### 改动 1：`examples/advanced_patterns.yml` — `when: false` → `tags: [never, example]`

**Codex 意图：** 让示例中"默认不执行"的任务语义更明确，符合 Ansible 约定。

**Diff 核查：**
- 4 处 `when: false`（用于禁用示例 task）全部改为 `tags: [never, example]`
- 剩余的 `changed_when: false` 均为正常幂等控制，未被误改

**评估：合理，已落地。**

`tags: [never, example]` 比 `when: false` 更符合 Ansible 官方约定：
- `never` 标签在官方文档中明确定义为"默认不执行，需显式指定才运行"
- 学习者可以用 `--tags example` 运行这些示例，`when: false` 完全阻断了这个路径
- 不存在 `literal-compare` lint 警告风险（这正是 R2-1 最初提出的问题）

**R2-1 结论：✅ 已落地**

---

### 改动 2：`molecule/common/verify.yml` — 新增 UFW / firewalld 断言

**Codex 意图：** 让 `common` role 的跨平台防火墙分支（UFW vs firewalld）进入验证层，不只停留在代码和 README。

**Diff 核查：**
```yaml
# 新增的断言逻辑
- service_facts 采集（为 firewalld 服务检查做准备）
- ufw 包存在断言（when: ansible_os_family == 'Debian'）
- firewalld 包存在断言（when: ansible_os_family == 'RedHat'）
- firewalld.service 运行状态断言（when: ansible_os_family == 'RedHat'）
```

**一个细节确认：**
`services['firewalld.service']` 使用了 `service_facts` 注入的短变量名 `services`（而非 `ansible_facts.services`）。这是 Ansible 约定的合法写法，在 Molecule verify playbook 中可以正常工作。

**评估：合理，已落地。**

这使得 `molecule/common` 在 Rocky 9 上运行时会真正验证：
1. firewalld 包已安装
2. firewalld 服务正在运行

**R3-1 结论：✅ 已落地**

---

### 改动 3：`roles/database/meta/argument_specs.yml` — Vault 路径修正

**Diff 核查：**
```
- Example: set vault_db_root_password in group_vars/all/vault.yml
+ Example: set vault_db_root_password in
+ inventory/production/group_vars/all/vault.yml
```

**评估：合理，已落地。**

现在所有文件（README、vault_demo.yml、argument_specs.yml）中的 Vault 路径引用全部统一为 `inventory/production/group_vars/all/vault.yml`。

**Vault 路径同步结论：✅ 已落地（从"已部分落地"升级）**

---

## 本轮证据核对矩阵

| 问题 | 代码 | README/docs | meta/specs | 测试 | 结论 |
|------|:----:|:-----------:|:----------:|:----:|------|
| R2-1: `when: false` → `tags: [never]` | ✅ | — | — | — | **已落地** |
| R3-1: firewalld verify 断言 | ✅ | — | — | ✅ | **已落地** |
| Vault 路径完全统一 | ✅ | ✅ | ✅ | — | **已落地** |

---

## 三个必答问题（来自 Round 5 Brief）

### Q1：Codex Round 4 的 3 处改动是否都合理？

**是。** 三处改动均正确，无引入新问题：
- `when: false` → `tags: [never, example]`：符合 Ansible 官方约定，教学价值更高
- firewalld 断言：逻辑正确，与 `security.yml` 的实现对应
- Vault 路径：最后一处遗漏，修正后完全统一

### Q2：还有没有必须继续修的中高优先级问题？

**没有。**

当前剩余的已知问题全部为低优先级：

| ID | 问题 | 建议处置 |
|----|------|---------|
| R3-2 | database role 无 RedHat 路径（Tier 2 骨架未实现）| 接受为"已知 Tier 2 限制"，不继续处理 |
| — | webserver role 无 Rocky Molecule 场景 | 接受，Tier 1 仅 Ubuntu，与文档一致 |
| — | examples/ 中仍有部分 Jinja2 注释未更新 | 无误导性，不影响学习 |

### Q3：这个项目是否可以结束当前 review 阶段？

**是，可以结束当前 review 阶段。**

依据：
1. Charter 中的 4 类高优先级问题（直接失败 / 误导学习者 / 文档不一致 / 安全工作流）已全部解决
2. 平台支持 Tier 1/2/3 已清晰声明，代码、meta、Molecule 三层一致
3. Vault 工作流已按方案 B 收口，所有路径统一
4. 默认主路径（site.yml、roles、inventory）自洽可运行
5. 教学示例（examples/）与默认路径边界清晰

剩余问题均属"已接受的范围限制"，不影响项目作为 Ansible 学习 demo 的核心价值。

---

## 最终遗留问题登记（不建议继续迭代，仅存档）

| ID | 问题 | 接受原因 |
|----|------|---------|
| R3-2 | database role Tier 2 RedHat 骨架未实现 | 实现 RedHat MySQL 路径超出当前 demo 范围 |
| — | webserver + database 无 Rocky Molecule 场景 | Tier 1 明确标注 Ubuntu，已如实声明 |
| — | AlmaLinux 9 仅"预期兼容"，无实际验证 | Tier 2 定义允许此状态 |

---

## 本轮结束自检

1. **更贴近原始目的？** 是。三处改动均提升了教学正确性和验证完整性，无范围扩张。
2. **教学/默认路径分得更清楚？** 是。`tags: [never, example]` 让 examples/ 的教学意图更明确。
3. **产生新的文档漂移？** 否。
4. **引入新的环境依赖？** 否。
5. **还有未关闭的前置矛盾？** 否。所有中高优先级问题已关闭。

**建议：结束当前 review 迭代阶段。**
