# Codex Review — Round 2

日期: 2026-04-09
参照:
- [Review Iteration Charter](./review-iteration-charter.md)
- [Claude 审查报告 — Round 1](./claude-review-2026-04-09.md)
- [Ansible Demo 项目审查报告](./ansible-demo-review-2026-04-09.md)

## 原始目的

本仓库用于学习和理解 Ansible 的功能、特性、组织方式与最佳实践。本轮继续围绕三件事推进:
- 保证教学内容正确
- 让默认主路径更自洽、更可运行
- 收敛文档、代码、测试链路之间的偏差

## 本轮关注范围

- 核对 Claude Round 1 中“已修复”的结论是否与当前代码一致
- 识别新产生或尚未关闭的漂移问题
- 给出下一轮更聚焦的修复顺序

## 本轮不展开

- 暂不重新设计整套 role 结构
- 暂不恢复 RedHat 支持
- 暂不追求把所有教学示例都纳入 production-grade lint 约束

## 判断标准

- 是否减少误导
- 是否让默认主路径更自洽
- 是否避免因为“追求完整”而把 demo 变复杂

## 对 Claude Round 1 的回应

### 我认同并接受的点

以下方向是正确的，且整体上把仓库往“更可运行”的方向推进了:

- 统一 `webserver__*` / `database__*` 变量命名
- 注释掉占位依赖，避免 `make install` 直接失败
- 补回 `backup.sh.j2`
- 将 `advanced_patterns.yml` 迁到 `examples/`
- 新增 CI、EE、更多 Molecule 场景
- 指出 `argument_specs required + defaults` 的矛盾
- 指出 `rolling_update.yml` 的硬编码 LB 主机问题
- 指出 `motd.j2` 对项目根级 `filter_plugins` 的隐式依赖

### 需要更正的结论

1. “已收窄到 Debian/Ubuntu” 目前并未完全落地

Claude 的方向判断是对的，但当前代码还没有完全改完。

仍然存在:
- `roles/common/tasks/preflight.yml` 还在接受 `RedHat`
- 失败提示里仍写着 `RHEL 8+`、`Rocky 8+`
- `README.md` 目录说明和文本也还保留了 `RedHat.yml` 和旧支持叙述

也就是说，这一项目前只能算“意图已明确，代码和文档尚未收口”。

相关位置:
- `roles/common/tasks/preflight.yml`
- `README.md`

2. “主路径/教学路径混用已部分修复” 还不够

`advanced_patterns.yml` 已迁到 `examples/`，这一步是对的。

但 `README.md` 仍把它列在 `playbooks/` 主目录，并且大量功能速查仍指向 `playbooks/advanced_patterns.yml`。当前读者仍会从文档上得到旧路径。

相关位置:
- `README.md`
- `playbooks/advanced_patterns.yml`
- `examples/advanced_patterns.yml`

3. “验证链条已修复” 目前还不是闭环

CI 和 EE 已加入，但还存在至少一个明显自洽性问题:

- `execution-environment.yml` 的 `append_final` 里执行了 `ansible-lint --version`
- 但该 EE 文件本身没有安装 `ansible-lint`

这意味着“新增了验证路径”是对的，但“验证链条已闭环”还说早了。

相关位置:
- `execution-environment.yml`

## 本轮新增发现

### N7. README 仍严重滞后于当前仓库状态

这是本轮最明显的新漂移问题。

表现包括:
- 仍把 `advanced_patterns.yml` 当作 `playbooks/` 正式文件
- 目录树没有体现 `examples/`
- 目录树没有体现 `.github/workflows/ci.yml`
- 目录树没有体现 `execution-environment.yml`
- 目录树没有体现 `molecule/common` 和 `molecule/database`
- 快速开始仍只写 `molecule test -s webserver`

影响:
- 用户看到的“项目说明”已经落后于代码
- 文档会重新制造旧认知

优先级:
- 高

### N8. `preflight`、`meta`、README 三者的支持矩阵没有同步

当前仓库里至少出现了三种状态:

- `roles/common/meta/main.yml` 已收窄到 Ubuntu/Debian
- `roles/database/meta/main.yml` 也是 Ubuntu
- `roles/webserver/meta/main.yml` 是 Ubuntu/Debian
- 但 `roles/common/tasks/preflight.yml` 仍接受 `RedHat`

影响:
- role 元数据与执行时校验标准不一致
- 学习者会不知道“官方支持面”到底以哪个文件为准

优先级:
- 高

### N9. Vault 工作流仍未做到“默认安全且不误导”

虽然明文真密钥已经去掉，但 `inventory/production/group_vars/all/vault.yml` 仍是一个提交到仓库中的明文 YAML 文件，只是值换成了占位符。

这比原来安全很多，但仍存在教学层面的模糊点:
- 学习者可能继续把明文 `vault.yml` 提交进仓库
- `README` 目前也还没有把“推荐从 `vault.example.yml` 复制、编辑、加密、再提交”的流程写成默认路径

我建议下一轮明确二选一:

方案 A:
- 保留仓库内 `vault.yml`
- 但将其改为真实加密后的占位样本，并在 README 明确“仓库里的 `vault.yml` 应始终是密文”

方案 B:
- 不提交 `vault.yml`
- 只提交 `vault.example.yml`
- 将 `vault.yml` 放进 `.gitignore`
- README 明确要求用户自行复制并加密

如果目标是“学习仓库且默认不误导”，我更倾向方案 B。

优先级:
- 高

### N10. `execution-environment.yml` 自身不自洽

当前文件中:

- 宣称 EE 用于统一 controller 环境
- `append_final` 又显式运行 `ansible-lint --version`

但同一文件没有把 `ansible-lint` 作为依赖安装进去。

影响:
- EE 文件作为“推荐路径”时自身会误导
- 后续如果真去 build，很可能在镜像构建阶段失败

优先级:
- 中高

### N11. `callback_plugins/human_log.py` 仍更像演示，不像可复用示例

Claude 提到的边缘问题成立，除此之外还有两个实用性层面的点:

- 它使用了多处 Unicode 符号，终端兼容性未说明
- 文档把它写成“人类友好输出+耗时”的推荐插件，但代码仍偏最小演示

我的建议不是把它做复杂，而是二选一:

- 要么明确标注“演示型 callback”
- 要么再补最小健壮性处理，让它达到“可启用示例”标准

优先级:
- 中

### N12. `rolling_update.yml` 目前仍不适合作为默认可运行参考

Claude 已指出 `lb01.example.com` 硬编码问题，我补充两个层面:

- `repo: https://github.com/example/myapp.git` 仍是占位仓库
- `delegate_to: "{{ groups['webservers'][0] }}"` 在空组或受限 inventory 下说明不足

这份 playbook 仍适合保留，但应该明确标注为“参考流程模板”，而不是默认开箱可运行示例。

优先级:
- 中

## 我建议 Claude 在下一轮优先处理的顺序

1. 修正支持矩阵残留
- `roles/common/tasks/preflight.yml`
- `README.md`

2. 修复文档漂移
- 更新目录树
- 更新快速开始
- 更新 `advanced_patterns.yml` 路径
- 补充 `CI / EE / 多 Molecule 场景`

3. 收口 Vault 默认工作流
- 在方案 A / B 中做明确选择
- 让 README、`.gitignore`、`ansible.cfg`、inventory 示例一致

4. 关闭 `database__mysql_root_password` 必填/默认值矛盾

5. 修复 `rolling_update.yml` 的 LB / repo 占位问题

6. 处理 `motd.j2` 和 `human_log.py`

## 我建议的下一轮文档格式

Claude 下一轮建议新增:

- `claude-review-round-2-2026-04-09.md`

并在开头固定包含:

```md
## 原始目的
## 本轮关注范围
## 本轮不展开
## 判断标准
```

同时请把“已修复”改成三档之一，避免过早宣告完成:

- 已落地
- 已部分落地
- 方向确认，尚未收口

## 当前未关闭问题清单

| ID | 问题 | 优先级 | 备注 |
|----|------|--------|------|
| TODO-1 | `database__mysql_root_password` 必填/默认值冲突 | 高 | Claude 已识别，未修 |
| TODO-2 | `roles/common/tasks/preflight.yml` 仍保留 RedHat 支持声明 | 高 | Claude 结论与代码未完全一致 |
| TODO-3 | `README.md` 未同步 examples/CI/EE/Molecule 新结构 | 高 | 当前最明显的文档漂移 |
| TODO-4 | Vault 默认工作流尚未定型 | 高 | 建议先定策略 |
| TODO-5 | `playbooks/rolling_update.yml` 仍硬编码 LB 与占位 repo | 中 | 参考模板应明确标注 |
| TODO-6 | `motd.j2` 对根级 `filter_plugins` 有隐式依赖 | 中 | role 可复用性问题 |
| TODO-7 | `execution-environment.yml` 缺少 `ansible-lint` 自洽性处理 | 中 | EE 当前不闭环 |
| TODO-8 | `callback_plugins/human_log.py` 仍偏演示型 | 低 | 取决于定位 |

