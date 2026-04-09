# Review Phase Closeout

日期: 2026-04-09
阶段范围:
- 初始审查
- Claude Round 1-4
- Codex Round 2-4

## 原始目的

本轮 review 链条的原始目的，是把这个仓库从“方向对但存在若干误导和不自洽”的学习骨架，收口成一个：

- 更适合学习 Ansible
- 默认主路径更自洽
- 文档、代码、测试和平台声明更一致

的 demo 项目。

## 本阶段已完成的核心收口

### 1. 会直接失败或误导运行的关键问题

- 修复了缺失模板 `backup.sh.j2`
- 修正了 vhost 级错误的 `nginx -t -c %s`
- 去除了 `rolling_update.yml` 中的硬编码 LB 主机
- 清理了占位依赖导致的安装失败风险

### 2. 变量体系和角色边界

- inventory 与 role defaults 统一到 `role__*` 命名
- 清除了 database role 中 `required: true` 与 defaults 默认值冲突
- 移除了 `motd.j2` 对项目根级自定义 filter 的隐式依赖

### 3. Vault 与安全工作流

- `vault.yml` 不再被 git 跟踪
- `vault.example.yml` 作为可提交模板保留
- README、Vault demo、argument specs 的路径说明已统一到当前 inventory 结构

### 4. 平台支持表达

- 避免了“直接收窄到 Debian/Ubuntu”的错误方向
- 建立了 Tier 1 / Tier 2 / Tier 3 分层支持模型
- `common` role 已在文档、preflight、Molecule 层面体现 Debian/RedHat family 差异
- README 中 Rocky 和 AlmaLinux 的状态已分开表述

### 5. 工具链与验证链条

- 增加了 CI、Execution Environment、更多 Molecule 场景
- `molecule/common` 现在会验证 Debian 的 UFW 和 RedHat 的 firewalld 分支
- examples 中原本的 `when: false` 已改成 `tags: [never, example]`

## 当前接受的剩余限制

这些问题当前不再建议继续作为同一轮 review 的阻塞项处理：

- `database` role 的 RedHat-compatible 实现仍未完成
- `webserver` / `database` 没有 Rocky / Alma 的 Molecule 场景
- Tier 2 平台主要仍停留在“骨架 + 文档说明”层面

这些限制是已接受的，因为：
- 它们不会继续误导当前默认主路径
- 它们属于“能力扩展”，不是“收口一致性”
- 继续做下去会把学习 demo 推向更重的维护面

## 结论

当前 review 阶段可以结束。

此时仓库已经达到一个合理状态：
- 适合继续学习和演示 Ansible 的主要能力
- 默认路径和教学路径边界较清楚
- 剩余问题主要属于可选扩展，而非必须继续收口

## 后续建议

如果未来还要继续迭代，建议将其视为**新阶段**，而不是延续当前 review 链条。

更合适的新阶段主题可以是：

1. RedHat-compatible database/webserver 最小实现
2. Tier 2 平台的 Molecule 补测
3. 进一步打磨 examples 的可执行体验
4. 将部分 demo 抽成更标准的 role / collection 教学样板

