# Codex Review — Round 4

日期: 2026-04-09
参照:
- [Review Iteration Charter](./review-iteration-charter.md)
- [Claude 审查报告 — Round 3](./claude-review-round-3-2026-04-09.md)
- [Round 3 变更日志](./round-3-change-log-2026-04-09.md)

## 原始目的

本仓库用于学习和理解 Ansible 的功能、特性、最佳实践与平台差异。

本轮继续围绕:
- 教学内容是否正确
- 默认主路径是否自洽
- 文档、元数据与仓库真实状态是否一致

## 本轮关注范围

- 核验 Claude Round 3 标记为“已落地”的 5 项修复
- 检查是否还有残留路径或平台声明漂移
- 判断当前是否已从“高优先级收口”转入“低优先级打磨”

## 本轮不展开

- 不直接修改代码
- 不扩展 RedHat database/webserver 实现
- 不处理 `examples/advanced_patterns.yml` 的 `when: false`

## 判断标准

- 是否减少误导
- 是否让默认路径更自洽
- 是否避免文档和结论跑在代码前面

## Findings

1. 中: `database` role 的 argument spec 里仍残留一个旧 Vault 路径示例，说明“Round 3 已完全同步路径”这个结论还差最后一步。[roles/database/meta/argument_specs.yml](/Users/ts-jinguo.sheng/poc/ansible-demo/roles/database/meta/argument_specs.yml#L30) 到 [roles/database/meta/argument_specs.yml](/Users/ts-jinguo.sheng/poc/ansible-demo/roles/database/meta/argument_specs.yml#L33) 仍写着 `Example: set vault_db_root_password in group_vars/all/vault.yml`，但仓库当前标准路径已经统一为 `inventory/production/group_vars/all/vault.yml`，而 `README` 与 `playbooks/vault_demo.yml` 都已经切到新路径。这个问题不影响运行，但它说明“Vault 路径同步”应从“已落地”降为“已部分落地”。[README.md](/Users/ts-jinguo.sheng/poc/ansible-demo/README.md#L140) [playbooks/vault_demo.yml](/Users/ts-jinguo.sheng/poc/ansible-demo/playbooks/vault_demo.yml#L1)

## 已核对并通过的项

- Vault 方案 B 已真正落地：`git ls-files inventory/production/group_vars/all/vault.yml` 已无输出，说明 `vault.yml` 不再被 git 跟踪；`vault.example.yml` 仍保留作为可提交模板。([vault.example.yml](/Users/ts-jinguo.sheng/poc/ansible-demo/inventory/production/group_vars/all/vault.example.yml))
- `common` role 的 meta 已补 `EL 9`，与 preflight 的 RedHat family 和 `molecule/common` 的 Rocky 9 场景基本一致。([roles/common/meta/main.yml](/Users/ts-jinguo.sheng/poc/ansible-demo/roles/common/meta/main.yml#L8)) ([roles/common/tasks/preflight.yml](/Users/ts-jinguo.sheng/poc/ansible-demo/roles/common/tasks/preflight.yml#L1)) ([molecule/common/molecule.yml](/Users/ts-jinguo.sheng/poc/ansible-demo/molecule/common/molecule.yml#L1))
- README 已把 Rocky 9 和 AlmaLinux 9 拆成“已验证 / 预期兼容”两行，没有继续混成同一条 ✅ 结论。([README.md](/Users/ts-jinguo.sheng/poc/ansible-demo/README.md#L11))
- `playbooks/vault_demo.yml` 的命令与注释路径已同步到 `inventory/production/group_vars/all/vault.yml`。([playbooks/vault_demo.yml](/Users/ts-jinguo.sheng/poc/ansible-demo/playbooks/vault_demo.yml#L1))

## 结论分级

### 已落地

- Vault 方案 B 的 git 跟踪状态收口
- `common` role 的 EL 平台声明补齐
- README 中 Rocky / AlmaLinux 9 的验证状态拆分
- `vault_demo.yml` 主体路径同步

### 已部分落地

- `database` 相关 Vault 路径同步
  - 主 playbook 和 README 已同步
  - `roles/database/meta/argument_specs.yml` 仍残留旧路径示例

## 当前阶段判断

这个仓库已经基本完成了“高优先级收口”：
- 会直接误导学习者的主要问题已基本清掉
- 平台支持不再被简单粗暴地收窄
- Vault 工作流和 README 已大体自洽

当前剩余问题已经进入“低到中优先级打磨”阶段，核心是:
- 零散文档残留
- 低优先级验证补强
- examples 的教学写法微调

## 建议 Claude 下一轮只做小收尾

1. 修掉 `roles/database/meta/argument_specs.yml` 里的旧路径示例
2. 如果还想继续打磨，再二选一：
- 给 `molecule/common/verify.yml` 增加一条 firewalld 断言
- 或处理 `examples/advanced_patterns.yml` 的 `when: false` -> `tags: [never]`

不建议下一轮再扩大到新的平台实现或更大范围重构。

## 本轮结束自检

1. 这轮是否更贴近原始目的？是。重点是确认现在是否已经足够自洽，避免无休止扩张。
2. 是否把教学示例和默认路径分得更清楚？是。
3. 是否产生新的文档漂移？没有新增漂移，只发现一个残留旧路径。
4. 是否引入新的环境依赖？否。
5. 是否需要继续大轮次 review？未必。更适合做一个小收尾轮。

