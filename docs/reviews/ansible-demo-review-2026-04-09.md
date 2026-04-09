# Ansible Demo 项目审查报告

日期: 2026-04-09

范围:
- 本地仓库结构与关键 Ansible 内容静态审查
- 对照最新 Ansible 官方文档
- 参考当前社区常见实践

结论:
这个 demo 项目的整体方向是对的，已经覆盖了 inventory、roles、group_vars/host_vars、动态 inventory、Vault、Molecule、自定义插件等核心主题，适合学习 Ansible 的主要功能和组织方式。

但它目前更像“教学型展示骨架”，还不是“默认即可跑通、且实践收口较完整”的模板。主要问题集中在:
- 部分内容会直接执行失败
- 文档、支持矩阵与真实实现不一致
- 变量命名体系混用，容易造成配置看似生效但实际未被 role 消费
- 安全与工具链配置仍有明显缺口

## 高优先级问题

1. `inventory/production/group_vars/all/vault.yml`

当前仍是明文敏感信息，不是 Vault 加密后的内容。这会直接误导学习路径，也存在真实泄密风险。

补充:
- `.pre-commit-config.yaml` 配置了 `detect-secrets --baseline .secrets.baseline`
- 仓库中不存在 `.secrets.baseline`
- `exclude` 配置写的是 `group_vars/all/vault.yml`，与实际路径不一致

影响:
- pre-commit 不是开箱即用
- secret 扫描配置也没有准确覆盖当前仓库结构

2. `ansible.cfg`

文件中大量使用:

```ini
key = value  # 注释
```

这种写法。Ansible 配置文件基于 INI 语义，行内注释不应使用这种形式，存在把注释内容一起解析为值的风险。

补充:
- `stdout_callback = yaml` 这个配置也偏旧
- 建议改用默认 stdout callback，并通过 `callback_result_format = yaml` 控制输出格式

3. `requirements.yml`

包含占位依赖:

```yaml
- name: my_company.base_hardening
  src: https://github.com/example/ansible-hardening.git
```

但 `Makefile` 中 `make install` 会直接安装它。

影响:
- 新用户会在安装依赖阶段直接失败
- 教学占位内容混入默认主路径，不利于“开箱可运行”

建议:
- 注释掉占位依赖
- 或拆成 `requirements.optional.yml`

4. `roles/database/tasks/configure.yml`

引用了不存在的模板:

```yaml
src: backup.sh.j2
```

但仓库中 `roles/database/templates/` 只有 `my.cnf.j2`。

同时:
- `inventory/production/group_vars/dbservers/vars.yml` 中开启了 `mysql_backup_enabled: true`

影响:
- 数据库 role 在备份分支会直接失败

5. `roles/webserver/tasks/vhosts.yml`

对单个 vhost 文件使用:

```yaml
validate: nginx -t -c %s
```

这里的 `%s` 是单个 server 配置片段，不是完整 nginx 主配置。`nginx -c` 会把它当主入口处理，这种校验方式不成立。

影响:
- validate 本身可能误报失败
- 或者产生错误的“配置校验”认知

## 中高优先级问题

6. 变量命名体系不统一

当前仓库混用了至少三套风格:
- `webserver__*`
- `database__*`
- `nginx_*` / `mysql_*`

例如:
- `roles/webserver/defaults/main.yml` 主要使用 `webserver__*`
- `inventory/production/group_vars/webservers/vars.yml` 使用 `nginx_*`
- `roles/database/templates/my.cnf.j2` 同时混用了 `mysql_*` 和 `database__*`

影响:
- inventory 中定义的变量可能不会真正影响 role
- 阅读者会误以为“都能覆盖”，但实际只有部分变量生效

建议:
- 统一采用 role 前缀命名
- 如需保留教学友好别名，显式做 alias 映射，不要在 task/template 内部直接混用

7. 支持矩阵与真实实现不一致

`roles/common/tasks/preflight.yml` 声称支持:
- Debian
- RedHat

但后续实现明显偏 Debian/Ubuntu:
- `community.general.ufw`
- `ansible.builtin.apt`
- `dpkg-query`

数据库 role 也默认了 Ubuntu 风格路径和服务名。

影响:
- README 和 preflight 给出的支持承诺不准确
- 用户会误以为当前代码已经跨发行版适配完成

建议:
- 要么收窄为 Debian/Ubuntu
- 要么补齐 RedHat 分支和对应测试

## 其他值得修正的问题

8. pre-commit 配置不是完全可运行状态

当前仓库有:
- `.ansible-lint`
- `.yamllint`
- `.pre-commit-config.yaml`

这是好的。

但仍有明显缺口:
- `.secrets.baseline` 缺失
- `ansible-lint` hook 的版本较旧
- 没有 CI 把这些检查真正串起来

9. 主路径和教学路径混在一起

`advanced_patterns.yml` 这种“教学全集”文件本身有价值，但像下面这类内容不适合放在默认主路径里:
- `vars_prompt`
- fire-and-forget 异步升级
- 占位 Git 仓库依赖
- 不可直接运行的演示校验逻辑

建议:
- 主路径保留“默认可运行”的最小集合
- 教学示例迁到 `examples/` 或 `docs/`

10. 本地验证链条不完整

当前环境里未安装:
- `ansible`
- `ansible-playbook`
- `ansible-lint`

因此这次仅完成静态审查，未完成真实语法检查和 lint 验证。

这不一定是仓库本身的问题，但意味着项目还缺少一种“无需依赖操作者本机环境”的可复现执行方式。

## 与官方文档的对照结论

1. 目录组织

项目按环境拆分 inventory，并结合 `group_vars/host_vars`、`roles/`、`playbooks/` 组织内容，这与 Ansible 官方 sample setup / best practices 方向一致。

2. 动态 inventory

同时展示:
- inventory plugin
- 自定义动态 inventory 脚本

这很适合教学。按当前官方方向，更推荐优先使用 inventory plugins，脚本方式更适合作为兼容性或原理示例。

3. Role argument validation

仓库使用了 `meta/argument_specs.yml`，这是对的，也是当前官方推荐能力之一。

4. Collections / FQCN

大部分任务已经使用 FQCN，这与当前 Ansible 对 collections 的使用方式一致。

5. 输出与配置

`ansible.cfg` 需要按当前官方配置方式整理，尤其是:
- 行内注释写法
- stdout callback 的现代写法

## 社区实践对照

社区中较成熟的 Ansible 项目，通常会具备以下特征:
- `Molecule` 场景覆盖主要 role
- `ansible-lint` 和 `yamllint`
- `pre-commit`
- CI 持续运行 lint/test
- 尽量统一变量命名
- 明确支持矩阵

这个 demo 已经具备其中一部分，但还没有真正收口到“社区常见的可维护项目状态”。

尤其还缺:
- 更完整的 Molecule 场景
- CI
- 更严格的依赖和执行环境管理

## 建议补充内容

1. 增加执行环境定义

建议新增:
- `execution-environment.yml`

目的:
- 固化 controller 环境
- 减少“我本机装了什么工具”带来的差异
- 更接近 AWX / Automation Controller / CI 的实际使用方式

2. 补充 CI

建议至少增加:
- YAML lint
- ansible-lint
- `ansible-playbook --syntax-check`
- Molecule

3. 扩展 Molecule

当前只有 `webserver` 场景。

建议补:
- `common`
- `database`

如果还保留 RedHat 支持宣称，再增加对应平台测试。

4. 收敛变量命名

建议统一为:
- `common__*`
- `webserver__*`
- `database__*`

5. 拆分教学示例与默认主路径

建议目录:
- `playbooks/` 保留默认可运行内容
- `examples/` 放高级模式、实验性或教学型示例

6. 修正安全工作流

建议:
- 真正加密 `vault.yml`
- 提供 `vault.example.yml` 或示例密文字段说明
- 修正 `detect-secrets` 配置

7. 更新 README 安装说明

建议明确:
- 推荐使用 `pipx` 或虚拟环境
- 说明 `ansible` 与 `ansible-core` 的差异
- 补一段“第一次运行前必须完成哪些文件初始化”

## 我会给这个项目的判断

如果目标是“学习 Ansible 能做什么”，这个项目已经有相当不错的覆盖面。

如果目标是“给新人一个可以直接照着跑、并逐步演进成真实项目的模板”，它还需要至少一轮系统收口，重点是:
- 修掉直接失败项
- 统一变量体系
- 修正配置与安全工作流
- 把测试和执行环境补齐

## 推荐的下一步整改顺序

1. 修复会直接失败的问题
- `vault.yml`
- `backup.sh.j2`
- `requirements.yml` 占位依赖
- `pre-commit` baseline

2. 修正 `ansible.cfg`
- 去掉有风险的行内注释
- 更新 stdout 输出配置方式

3. 统一变量命名
- inventory
- defaults
- templates
- tasks
- argument_specs

4. 收窄或补齐支持矩阵
- 先只支持 Debian/Ubuntu
- 或补齐 RedHat 实现与测试

5. 增加 CI 和更多 Molecule 场景

## 附注

本次结论基于:
- 本地仓库静态审查
- 最新 Ansible 官方文档方向
- 社区常见 role / collection 项目结构与工作流

本次未完成:
- 实际 `ansible-playbook --syntax-check`
- 实际 `ansible-lint`
- 实际 Molecule 运行

原因:
- 当前工作环境未安装 `ansible`、`ansible-playbook`、`ansible-lint`
