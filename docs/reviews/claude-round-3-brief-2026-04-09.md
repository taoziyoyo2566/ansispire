# Claude Round 3 Brief

日期: 2026-04-09
参照:
- [Review Iteration Charter](./review-iteration-charter.md)
- [Platform Support Addendum](./platform-support-addendum-2026-04-09.md)
- [Codex Review — Round 2](./codex-review-round-2-2026-04-09.md)

## 原始目的

本仓库是用于学习和理解 Ansible 功能、特性、最佳实践的 demo。

本轮目标不是压缩范围、删减平台，而是:
- 让默认主路径更自洽
- 让平台支持表述更清楚
- 让文档、代码、测试链路一致

## 关键约束

1. 未经用户明确同意，不要再把平台支持直接收窄到 Debian/Ubuntu。
2. 遇到平台不一致问题，优先采用“支持分层”，不要直接删除 RedHat-compatible 路径。
3. 不要把“方向判断对了”写成“已修复”。
4. 任何“已落地”结论都必须核对:
   - 代码
   - README / docs
   - meta / argument_specs
   - preflight / runtime guard
   - 测试路径

## 你需要避免的几类问题

### 1. 过早改项目范围

错误做法:
- 发现 RedHat 适配不完整
- 直接把仓库改成 Debian/Ubuntu only

正确做法:
- 先指出“声明与实现不一致”
- 再给出支持分层建议
- 最后由用户决定是否正式缩减范围

### 2. 把“待收口”写成“已修复”

以后统一用:
- 已落地
- 已部分落地
- 方向确认，尚未收口

### 3. 把“特殊系统需要 bootstrap”误判成“不值得支持”

极简 Linux、无 Python 主机、强裁剪系统，通常意味着:
- 需要 preflight
- 需要 bootstrap
- 需要把默认假设拆开

不意味着:
- 应直接从学习仓库里删掉相关讨论

## 本轮优先事项

1. 平台支持矩阵收口
- 明确 Tier 1 / Tier 2 / Tier 3
- 至少保留一个 Debian 系和一个 RHEL-compatible 的学习视角

2. 修正文档漂移
- README 中同步:
  - `examples/advanced_patterns.yml`
  - `execution-environment.yml`
  - `.github/workflows/ci.yml`
  - `molecule/common`
  - `molecule/database`

3. 处理高优先级尾项
- `database__mysql_root_password` 必填/默认值矛盾
- `roles/common/tasks/preflight.yml` 与支持矩阵不一致
- `playbooks/rolling_update.yml` 的硬编码 LB / 占位 repo

4. 给出一个清晰结论
- 哪些平台是“默认支持且验证”
- 哪些平台是“有骨架但未验证”
- 哪些平台只在文档里讨论 bootstrap

## 输出格式要求

文档开头必须包含:

```md
## 原始目的
## 本轮关注范围
## 本轮不展开
## 判断标准
```

文档结尾必须包含:

- 本轮是否更贴近原始目的
- 是否产生新的文档漂移
- 是否引入新的环境依赖
- 尚未关闭的问题清单
