# Round 4 变更日志

日期: 2026-04-09
执行者: Codex
参照:
- [Codex Review — Round 4](./codex-review-round-4-2026-04-09.md)

---

## 原始目的

本轮不是扩展新功能，而是把仓库中剩余的低优先级不一致项继续收尾，让：
- 示例写法更清晰
- common 场景的跨平台验证更具体
- Vault 路径示例彻底统一

## 本轮变更

| 文件 | 变更类型 | 摘要 |
|------|---------|------|
| `roles/database/meta/argument_specs.yml` | 修改 | 将最后一处旧 Vault 路径示例从 `group_vars/all/vault.yml` 改为 `inventory/production/group_vars/all/vault.yml` |
| `molecule/common/verify.yml` | 修改 | 新增跨平台断言：Debian 断言 `ufw` 存在；RedHat 断言 `firewalld` 包存在且服务运行 |
| `examples/advanced_patterns.yml` | 修改 | 将 4 处 `when: false` 示例禁用方式改为 `tags: [never, example]` |
| `docs/reviews/codex-review-round-4-2026-04-09.md` | 新增 | Round 4 审查文档 |

## 变更意图

### 1. Vault 路径统一

此前 Round 3 已基本完成 Vault 路径同步，但 `roles/database/meta/argument_specs.yml` 还残留一处旧示例路径。

本轮将其统一为当前仓库标准路径：

```text
inventory/production/group_vars/all/vault.yml
```

### 2. common 场景验证补强

此前 `molecule/common/verify.yml` 主要验证：
- timezone
- curl
- MOTD
- app user / app dir

但它没有直接验证跨平台防火墙分支是否真正生效。

本轮补充：
- Debian family: `ufw` 已安装
- RedHat family: `firewalld` 已安装
- RedHat family: `firewalld.service` 正在运行

这样 `common` role 的 “UFW / firewalld 分支” 不只停留在代码层和 README 层，也进入了验证层。

### 3. 示例禁用写法调整

`examples/advanced_patterns.yml` 中原有 4 处：

```yaml
when: false
```

这类写法虽然能达到“默认不执行”的效果，但不如下面这种表达更贴近 Ansible 常见约定：

```yaml
tags: [never, example]
```

本轮统一改为 `tags: [never, example]`，使其语义更明确：
- 这些任务是示例
- 默认不执行
- 需要显式带 tag 才运行

## 本轮未做的事

- 未运行 `ansible-playbook` / `ansible-lint` / `molecule`
- 未新增更多平台实现
- 未继续扩展 RedHat database/webserver 支持

## 当时未提交改动（现已提交）

本节记录的是 Codex Round 4 结束当时的工作树状态。
这些改动后续已由 Claude 在 `review(round-4): finish low-priority items, close current review phase`
中提交，当前不再作为未提交变更存在。

当时的工作树中预期存在以下未提交改动：

- `examples/advanced_patterns.yml`
- `molecule/common/verify.yml`
- `roles/database/meta/argument_specs.yml`
- `docs/reviews/codex-review-round-4-2026-04-09.md`
- `docs/reviews/round-4-change-log-2026-04-09.md`

当前状态:
- 上述变更已提交
- 当前 review 阶段已进入结项状态

