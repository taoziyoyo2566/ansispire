# Codex Review — Round 3

日期: 2026-04-09
参照:
- [Review Iteration Charter](./review-iteration-charter.md)
- [Platform Support Addendum](./platform-support-addendum-2026-04-09.md)
- [Claude 审查报告 — Round 2](./claude-review-round-2-2026-04-09.md)
- [Round 2 变更日志](./round-2-change-log-2026-04-09.md)
- [Codex Review Brief — Round 3](./codex-review-round-3-brief-2026-04-09.md)

## 原始目的

本仓库用于学习和理解 Ansible 的功能、特性、最佳实践与平台差异。

本轮继续围绕三件事判断:
- 教学内容是否正确
- 默认主路径是否自洽
- 文档、元数据、测试与代码是否一致

## 本轮关注范围

- 核对 Claude Round 2 中标记为“已落地”的事项
- 检查平台支持分层是否真正同步到各层声明
- 检查 Vault 工作流是否真的按方案 B 落地
- 检查新增 Rocky 路径是否被文档过度表述

## 本轮不展开

- 不直接修改代码
- 不新增新一轮功能
- 不替 Claude 执行 Round 3 修复，只给出下一步准确问题清单

## 判断标准

- 是否减少误导
- 是否让默认路径更自洽
- 是否避免把“方向正确”过早写成“已完成”

## Findings

1. 中高: 方案 B 的 Vault 工作流并未真正落地，因为 `vault.yml` 仍然是被 git 跟踪的文件。[.gitignore](/Users/ts-jinguo.sheng/poc/ansible-demo/.gitignore#L5) 新增了 `inventory/**/vault.yml` 排除规则，但仓库中 [vault.yml](/Users/ts-jinguo.sheng/poc/ansible-demo/inventory/production/group_vars/all/vault.yml) 依然是已跟踪文件，`git ls-files` 仍能列出它；这意味着 README 中“默认不提交明文 vault.yml”的说法只对未来新文件成立，对当前仓库事实并不成立。[README.md](/Users/ts-jinguo.sheng/poc/ansible-demo/README.md#L140) [inventory/production/group_vars/all/vault.yml](/Users/ts-jinguo.sheng/poc/ansible-demo/inventory/production/group_vars/all/vault.yml)

2. 中高: `common` role 的平台支持声明仍然没有完全同步。README 和 preflight 都把 Rocky/Alma 的 RedHat 家族纳入 Tier 1/Tier 2 叙述，但 [roles/common/meta/main.yml](/Users/ts-jinguo.sheng/poc/ansible-demo/roles/common/meta/main.yml#L8) 仍只声明 Ubuntu 和 Debian，没有任何 RedHat-compatible 平台；与此同时，`molecule/common` 确实已经引入 Rocky 9，因此当前是代码/测试比 role metadata 更宽，而不是完全一致。这个问题不影响运行，但会继续误导“支持矩阵到底以哪个文件为准”。[README.md](/Users/ts-jinguo.sheng/poc/ansible-demo/README.md#L7) [roles/common/tasks/preflight.yml](/Users/ts-jinguo.sheng/poc/ansible-demo/roles/common/tasks/preflight.yml#L1) [molecule/common/molecule.yml](/Users/ts-jinguo.sheng/poc/ansible-demo/molecule/common/molecule.yml#L1)

3. 中高: `database` role 的文档/规格现在过度声明了 Rocky Tier 1 支持，但实际实现和测试并没有跟上。[roles/database/meta/argument_specs.yml](/Users/ts-jinguo.sheng/poc/ansible-demo/roles/database/meta/argument_specs.yml#L18) 明确写了 “Supports Tier 1 platforms: Ubuntu 20.04+, Rocky Linux 9+”，但 [roles/database/meta/main.yml](/Users/ts-jinguo.sheng/poc/ansible-demo/roles/database/meta/main.yml#L7) 只声明 Ubuntu，`molecule/database` 也只有 Ubuntu；更关键的是 [roles/database/tasks/install.yml](/Users/ts-jinguo.sheng/poc/ansible-demo/roles/database/tasks/install.yml#L2) 仍写死 `mysql-server`、`mysql-client`、`python3-mysqldb`、`mysql` 服务名，这并不足以支撑 Rocky 9 的 Tier 1 叙述。这个问题比普通文档漂移更严重，因为它会让学习者误以为数据库 role 已具备跨发行版实现。

4. 中: README 对 Rocky/Alma 的验证范围写得过满。[README.md](/Users/ts-jinguo.sheng/poc/ansible-demo/README.md#L12) 写的是 “Rocky Linux 9 / AlmaLinux 9 | ✅ | common 场景测试”，但当前实际只有 Rocky 9 平台被纳入 [molecule/common/molecule.yml](/Users/ts-jinguo.sheng/poc/ansible-demo/molecule/common/molecule.yml#L26)，没有 AlmaLinux 9 场景；同时 [molecule/common/verify.yml](/Users/ts-jinguo.sheng/poc/ansible-demo/molecule/common/verify.yml#L1) 也没有对 firewalld 路径做显式断言。更准确的说法应是“Rocky 9 已在 common 场景验证；AlmaLinux 9 为预期兼容”。

5. 中: `vault_demo.yml` 里的路径与当前仓库布局已不一致，仍在继续传播旧路径。[playbooks/vault_demo.yml](/Users/ts-jinguo.sheng/poc/ansible-demo/playbooks/vault_demo.yml#L5) 到 [playbooks/vault_demo.yml](/Users/ts-jinguo.sheng/poc/ansible-demo/playbooks/vault_demo.yml#L18) 的命令示例仍写 `group_vars/all/vault.yml`，变量说明也仍写“在 `group_vars/all/vault.yml` 中定义”，但当前仓库标准路径已经是 `inventory/production/group_vars/all/vault.yml`，README 也已经按新路径编写。[README.md](/Users/ts-jinguo.sheng/poc/ansible-demo/README.md#L143) 这会把用户重新带回旧目录结构认知。

## 结论分级

### 已部分落地

- 平台支持从“直接收窄”转向“Tier 1/2/3 分层”这一方向
- `argument_specs required + defaults` 的数据库密码冲突修复
- `rolling_update.yml` 去硬编码 LB 主机
- `motd.j2` 去除对根级 `filter_plugins` 的隐式依赖
- `execution-environment.yml` 中 `ansible-lint` 自洽

### 方向确认，尚未收口

- Vault 方案 B
- common role 的 RedHat Tier 声明同步
- database role 的平台声明同步
- README 中 Rocky/Alma 验证范围表述
- vault_demo 路径同步

## 建议 Claude 下一轮优先顺序

1. 先收口 Vault 方案 B
- 处理当前已跟踪的 `inventory/production/group_vars/all/vault.yml`
- 让 `.gitignore`、README、仓库真实跟踪状态三者一致

2. 再收口平台声明
- `roles/common/meta/main.yml`
- `roles/database/meta/main.yml`
- `roles/database/meta/argument_specs.yml`
- README 平台矩阵

3. 最后处理验证措辞
- 把 AlmaLinux 9 从“已验证”改为“预期兼容”，或补实际场景
- 如保留 Rocky common 场景结论，可考虑在 `molecule/common/verify.yml` 里补一条 firewalld 相关断言

4. 同步 `vault_demo.yml`
- 所有 Vault 命令与注释路径改到当前 inventory 结构

## 本轮结束自检

1. 这轮是否更贴近原始目的？是。重点在于防止“文档和结论先跑到代码前面”。
2. 是否把教学示例和默认路径分得更清楚？是。尤其把 Vault 和平台支持里的“表述过满”问题区分出来了。
3. 是否产生新的文档漂移？没有新增漂移，只识别了已有残留。
4. 是否引入新的环境依赖？否。
5. 是否需要交回 Claude 处理？可以，但建议以上述 4 项为明确待办继续，而不是再做泛化重构。

