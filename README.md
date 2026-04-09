# Ansible 完整参考项目

基于 Ansible 官方最佳实践与社区共识构建的脚手架，包含 dummy 内容，用于学习 Ansible 的功能、设计模式和使用技巧。

---

## 平台支持矩阵

| 层级 | 平台 | CI/Molecule | 说明 |
|------|------|:-----------:|------|
| **Tier 1** | Ubuntu 20.04 / 22.04 | ✅ | 默认测试目标 |
| **Tier 1** | Rocky Linux 9 / AlmaLinux 9 | ✅ | common 场景测试 |
| **Tier 2** | Debian 11 / 12 | 未测试 | 有代码骨架，预期兼容 |
| **Tier 2** | AlmaLinux 8 / CentOS Stream 9 | 未测试 | 有代码骨架 |
| **Tier 3** | Alpine / 无 systemd / 无 Python | ❌ | 需额外 bootstrap，见 `examples/` |

Tier 3 的处理模式参见 `examples/advanced_patterns.yml` 中的 `raw + script bootstrap` 章节。

---

## 完整目录结构

```
ansible-demo/
├── ansible.cfg                          # 项目级配置（纯 INI，无行内注释）
├── requirements.yml                     # 外部 roles + collections 依赖
├── Makefile                             # 常用命令快捷入口
├── execution-environment.yml            # Ansible EE 定义（ansible-builder）
├── .ansible-lint                        # Lint 规则（profile: production）
├── .pre-commit-config.yaml              # 提交前检查
├── .yamllint                            # YAML 格式规范
├── .secrets.baseline                    # detect-secrets 基线
├── .gitignore                           # 含 vault.yml 排除规则
│
├── .github/workflows/ci.yml             # CI: lint + syntax-check + Molecule(3场景)
│
├── inventory/
│   ├── production/
│   │   ├── hosts.ini                    # 静态 inventory
│   │   ├── group_vars/
│   │   │   ├── all/
│   │   │   │   ├── vars.yml             # 明文公共变量（统一 role 前缀命名）
│   │   │   │   ├── vault.yml            # 加密敏感变量（.gitignore 排除）
│   │   │   │   └── vault.example.yml   # 结构示例（可提交）
│   │   │   ├── webservers/vars.yml      # webserver__ 前缀变量
│   │   │   └── dbservers/vars.yml       # database__ 前缀变量
│   │   └── host_vars/web01.example.com/vars.yml
│   ├── staging/
│   └── dynamic/
│       ├── aws_ec2.yml                  # AWS EC2 动态 inventory 插件
│       └── custom_inventory.py          # 自定义动态 inventory 脚本
│
├── playbooks/
│   ├── site.yml                         # 主 Playbook
│   ├── rolling_update.yml               # 滚动更新参考模板（⚠ 需配置变量）
│   └── vault_demo.yml                   # Vault 工作流演示
│
├── examples/                            # ⚠ 教学参考，非默认执行路径
│   └── advanced_patterns.yml            # 高级用法全集（vars_prompt/add_host/等）
│
├── roles/
│   ├── common/                          # 基础配置（Tier 1: Ubuntu + Rocky）
│   │   ├── defaults/main.yml
│   │   ├── vars/os/                     # OS 特定变量（first_found 加载）
│   │   │   ├── Debian.yml               # UFW / apt / ssh
│   │   │   ├── RedHat.yml               # firewalld / dnf / sshd
│   │   │   └── default.yml
│   │   ├── tasks/
│   │   │   ├── main.yml                 # import_tasks 入口
│   │   │   ├── preflight.yml            # Tier 1/2 OS 检查、磁盘、Python
│   │   │   ├── packages.yml             # 包安装、用户、block/rescue
│   │   │   └── security.yml             # SSH + 跨平台防火墙 + async 升级
│   │   ├── handlers/main.yml
│   │   ├── templates/motd.j2            # 内联 Jinja2（不依赖 filter_plugins）
│   │   └── meta/
│   │       ├── main.yml
│   │       └── argument_specs.yml
│   │
│   ├── webserver/                       # Nginx（Tier 1: Ubuntu）
│   │   ├── defaults/main.yml
│   │   ├── vars/main.yml                # 内部常量
│   │   ├── tasks/
│   │   │   ├── main.yml
│   │   │   ├── preflight.yml            # vhost 配置前置校验
│   │   │   ├── install.yml
│   │   │   ├── configure.yml            # validate/blockinfile/replace
│   │   │   └── vhosts.yml               # symlink 管理 + 统一 nginx -t 校验
│   │   ├── handlers/main.yml
│   │   ├── templates/
│   │   │   ├── nginx.conf.j2
│   │   │   └── vhost.conf.j2
│   │   ├── files/default_index.html
│   │   └── meta/
│   │       ├── main.yml
│   │       └── argument_specs.yml
│   │
│   └── database/                        # MySQL（Tier 1: Ubuntu）
│       ├── defaults/main.yml            # 注: mysql_root_password 无默认值
│       ├── tasks/
│       │   ├── main.yml
│       │   ├── install.yml
│       │   └── configure.yml            # no_log / community.mysql
│       ├── handlers/main.yml
│       ├── templates/
│       │   ├── my.cnf.j2                # primary/replica 条件渲染
│       │   └── backup.sh.j2             # 备份脚本模板
│       └── meta/
│           ├── main.yml
│           └── argument_specs.yml       # required: true（无默认值，见注释）
│
├── library/app_config.py                # 自定义模块（JSON 配置管理）
├── filter_plugins/custom_filters.py     # 自定义 Jinja2 过滤器
├── lookup_plugins/config_value.py       # 自定义 Lookup 插件
├── callback_plugins/human_log.py        # 演示型 Callback（可启用示例）
│
└── molecule/
    ├── common/      # Ubuntu 22 + Rocky 9（Tier 1 双平台）
    ├── webserver/   # Ubuntu 22
    └── database/    # Ubuntu 22
```

---

## 快速开始

### 前置准备

```bash
# 安装工具（推荐用 pipx 隔离）
pip install ansible ansible-lint molecule[docker] pre-commit ansible-navigator

# 安装 Galaxy 依赖
ansible-galaxy role install -r requirements.yml
ansible-galaxy collection install -r requirements.yml

# 初始化 pre-commit
pre-commit install
```

### Vault 工作流（方案 B：不提交明文 vault.yml）

```bash
# 1. 从示例复制结构
cp inventory/production/group_vars/all/vault.example.yml \
   inventory/production/group_vars/all/vault.yml

# 2. 填写真实密码
vim inventory/production/group_vars/all/vault.yml

# 3. 创建 vault 密码文件（加入 .gitignore）
echo "your-vault-password" > .vault_pass
chmod 600 .vault_pass

# 4. 加密（此后 vault.yml 才可提交，但默认已在 .gitignore 中）
ansible-vault encrypt inventory/production/group_vars/all/vault.yml

# vault.yml 已在 .gitignore 中排除（inventory/**/vault.yml）
# 如需提交加密后的 vault.yml，从 .gitignore 中删除该条目
```

### 运行

```bash
# Dry-run
ansible-playbook playbooks/site.yml --check --diff

# 完整部署
ansible-playbook playbooks/site.yml

# Molecule 测试
molecule test -s common     # Ubuntu 22 + Rocky 9
molecule test -s webserver  # Ubuntu 22
molecule test -s database   # Ubuntu 22

# Lint
make lint
```

---

## 核心概念

### 变量优先级（从低到高）

```
role defaults/         ← 最容易被覆盖，用于"合理默认值"
inventory group_vars/  ← 组级变量（命名约定: role 前缀）
inventory host_vars/   ← 主机级变量
play vars:             ← playbook 中直接写的 vars
role vars/             ← 内部常量，比 group_vars 优先级高！
task vars:             ← task 级 vars（include_role 传入的 vars）
extra_vars -e          ← 命令行 -e，最高优先级，不可被覆盖
```

> **变量命名约定:** group_vars 与 role defaults 统一使用 `role__*` 前缀
> （如 `webserver__worker_processes`），避免"变量看似设置但未被消费"的问题。

### import_tasks vs include_tasks

| | `import_tasks`（静态）| `include_tasks`（动态）|
|---|---|---|
| 解析时机 | 编译期 | 运行期 |
| Tags 透传 | ✅ | ❌ |
| 动态文件名 | ❌ | ✅ |
| loop 支持 | ❌ | ✅ |

**经验法则:** 默认用 `import_tasks`；只有需要动态文件名或 loop 时才改用 `include_tasks`。

### Role Argument Validation（Ansible 2.11+）

`meta/argument_specs.yml` 在 role 执行前自动校验参数类型/必填/枚举。
**注意:** `required: true` 与 `defaults/main.yml` 中的默认值不能并存（见 `roles/database/meta/argument_specs.yml` 注释）。

### Tags 约定

```bash
ansible-playbook site.yml --tags nginx,config   # 只跑指定 tag
ansible-playbook site.yml --skip-tags hardening  # 跳过指定 tag
ansible-playbook site.yml --list-tags            # 列出所有 tag
ansible-playbook site.yml --tags upgrade         # 运行 never tag 的 task
```

| Tag | 含义 |
|-----|------|
| `always` | 始终执行（preflight 检查）|
| `never` | 默认跳过（升级、破坏性操作，需显式触发）|
| `preflight` | 前置检查 |
| `packages` | 包安装 |
| `hardening` | 安全加固 |
| `nginx` / `mysql` | 组件相关 |
| `verify` | 验证类（只读，可单独运行）|

### Handlers 设计原则

```yaml
# ✅ 推荐: 用 listen 解耦，纯服务操作，全部 FQCN
- name: Reload Nginx
  ansible.builtin.systemd:
    name: nginx
    state: reloaded
  listen: Reload Nginx   # task 侧 notify: Reload Nginx

# ❌ 避免: handler 中含 when 条件或复杂逻辑
- name: Restart service
  ansible.builtin.systemd:
    name: nginx
    state: restarted
  when: some_condition   # 应在 task 侧控制是否 notify，不在 handler 侧

# meta: flush_handlers — 立即执行已触发的 handler（不等 play 结束）
- name: Force handler execution now
  ansible.builtin.meta: flush_handlers
```

### Vault 最佳实践

```
vault.example.yml  ← 结构说明，可提交
vault.yml          ← 加密后才能提交；未加密版排除在 .gitignore 中
```

命名约定: vault 变量用 `vault_` 前缀，在明文 vars.yml 中引用：
```yaml
# vault.yml（加密）: vault_db_password: "real_secret"
# vars.yml（明文）:  db_password: "{{ vault_db_password }}"
```

---

## 功能速查表

| 功能 | 示例位置 |
|------|---------|
| ansible.cfg 无行内注释 INI 格式 | `ansible.cfg` |
| 多环境 Inventory | `inventory/production/` vs `inventory/staging/` |
| group_vars 目录（明文+vault 分离）| `group_vars/all/vars.yml` + `vault.example.yml` |
| host_vars 主机级覆盖 | `host_vars/web01.example.com/` |
| AWS EC2 动态 inventory 插件 | `inventory/dynamic/aws_ec2.yml` |
| 自定义动态 inventory 脚本 | `inventory/dynamic/custom_inventory.py` |
| Role Argument Validation | `roles/*/meta/argument_specs.yml` |
| required: true 无默认值设计 | `roles/database/meta/argument_specs.yml` |
| Preflight 前置检查（Tier 1/2）| `roles/common/tasks/preflight.yml` |
| OS 特定变量（first_found）| `roles/common/vars/os/` |
| 跨平台防火墙（UFW + firewalld）| `roles/common/tasks/security.yml` |
| `strategy: free` / `linear` | `playbooks/site.yml` |
| `gather_subset` 精简 facts 采集 | `playbooks/site.yml` |
| import_tasks vs include_tasks | `roles/common/tasks/main.yml` |
| loop + subelements + loop_control | `roles/common/tasks/packages.yml` |
| block / rescue / always | `roles/common/tasks/packages.yml` |
| register / changed_when / failed_when | `roles/common/tasks/security.yml` |
| async / poll 异步任务（双平台）| `roles/common/tasks/security.yml` |
| never 标签 | `roles/common/tasks/security.yml` |
| check_mode 感知 | `roles/common/tasks/security.yml` |
| ansible_managed（无 filter 依赖）| `roles/common/templates/motd.j2` |
| validate 写前校验 | `roles/webserver/tasks/configure.yml` |
| blockinfile / replace | `roles/webserver/tasks/configure.yml` |
| vhost 部署后统一 nginx -t | `roles/webserver/tasks/vhosts.yml` |
| handler listen 机制 | `roles/webserver/handlers/main.yml` |
| no_log 敏感数据保护 | `roles/database/tasks/configure.yml` |
| 主从条件渲染（db_role）| `roles/database/templates/my.cnf.j2` |
| 备份脚本模板 | `roles/database/templates/backup.sh.j2` |
| serial + delegate_to + run_once | `playbooks/rolling_update.yml` |
| lb_host 变量化（不硬编码）| `playbooks/rolling_update.yml` |
| Vault 工作流完整演示 | `playbooks/vault_demo.yml` |
| vars_prompt / add_host / group_by | `examples/advanced_patterns.yml` |
| meta 指令 / throttle / environment | `examples/advanced_patterns.yml` |
| hostvars / groups 魔法变量 | `examples/advanced_patterns.yml` |
| 内置 lookups（file/env/pipe/password）| `examples/advanced_patterns.yml` |
| uri REST API / wait_for | `examples/advanced_patterns.yml` |
| raw + script bootstrap | `examples/advanced_patterns.yml` |
| 高级 Jinja2（selectattr/combine/json_query）| `examples/advanced_patterns.yml` |
| 自定义模块 | `library/app_config.py` |
| 自定义 Jinja2 过滤器 | `filter_plugins/custom_filters.py` |
| 自定义 Lookup 插件 | `lookup_plugins/config_value.py` |
| 演示型 Callback（健壮版）| `callback_plugins/human_log.py` |
| `ansible_managed` 模板头 | `roles/*/templates/*.j2` |
| `delegate_to` / `run_once` | `playbooks/rolling_update.yml` |
| `until` / `retries` / `delay` 轮询 | `playbooks/rolling_update.yml` |
| Ansible Vault 完整工作流 | `playbooks/vault_demo.yml` |
| Molecule（3 场景，双平台）| `molecule/common/` `molecule/webserver/` `molecule/database/` |
| CI（5 job，含双平台 Molecule）| `.github/workflows/ci.yml` |
| EE 定义（ansible-lint 自洽）| `execution-environment.yml` |
| pre-commit + ansible-lint + detect-secrets | `.pre-commit-config.yaml` + `.secrets.baseline` |

---

## 常用命令

```bash
make install           # 安装 roles + collections
make lint              # ansible-lint
make syntax            # --syntax-check
make dry-run           # --check --diff
make deploy-staging    # 部署 staging
make deploy-prod       # 部署 production（需确认）

# Ad-hoc
ansible all -m ansible.builtin.ping
ansible webservers -m ansible.builtin.setup -a "filter=ansible_distribution*"
ansible all -m ansible.builtin.shell -a "df -h" --become

# 按标签执行
ansible-playbook playbooks/site.yml --tags preflight,packages
ansible-playbook playbooks/site.yml --skip-tags hardening

# 按主机过滤
ansible-playbook playbooks/site.yml --limit web01.example.com
ansible-playbook playbooks/site.yml --limit 'webservers:!web03*'

# Ad-hoc 服务操作
ansible webservers -m ansible.builtin.service -a "name=nginx state=restarted" --become

# Molecule（完整测试 / 调试）
molecule test -s common
molecule converge -s webserver   # 不销毁容器，方便调试
molecule verify -s webserver
molecule login -s webserver      # SSH 进入测试容器
```

---

## Vault 工作流速查

```bash
# 加密整个文件
ansible-vault encrypt inventory/production/group_vars/all/vault.yml

# 查看加密文件（不落盘解密）
ansible-vault view inventory/production/group_vars/all/vault.yml

# 编辑加密文件
ansible-vault edit inventory/production/group_vars/all/vault.yml

# 修改 vault 密码
ansible-vault rekey inventory/production/group_vars/all/vault.yml

# 加密单个字符串（嵌入 vars.yml 中）
ansible-vault encrypt_string 'MyPassword123' --name 'vault_db_password'
# 输出可直接粘贴到 vars.yml:
# vault_db_password: !vault |
#   $ANSIBLE_VAULT;1.1;AES256
#   66...

# 多 vault-id（不同环境用不同密码）
ansible-playbook site.yml \
  --vault-id prod@.vault_pass_prod \
  --vault-id dev@.vault_pass_dev
```

**命名约定:** vault 文件中的变量统一加 `vault_` 前缀，在明文 vars.yml 中引用：
```yaml
# vault.yml（加密）
vault_db_password: "SuperSecret123"

# vars.yml（明文）
db_password: "{{ vault_db_password }}"
```

---

## 动态 Inventory

```bash
# 测试自定义脚本
python inventory/dynamic/custom_inventory.py --list | python -m json.tool

# 同时使用多个 inventory 源
ansible-playbook site.yml -i inventory/production:inventory/dynamic

# 在 ansible.cfg 中配置多源
[defaults]
inventory = inventory/production:inventory/dynamic
```

---

## 性能优化建议

| 技巧 | 配置位置 |
|------|---------|
| SSH 持久连接 | `ansible.cfg`: `ssh_args = -o ControlPersist=60s` |
| 管道传输（减少 SSH 往返）| `ansible.cfg`: `pipelining = true` |
| Fact 缓存（避免重复采集）| `ansible.cfg`: `fact_caching = jsonfile` |
| 精简 facts 采集范围 | playbook: `gather_subset: [min, hardware]` |
| 并发主机数 | `ansible.cfg`: `forks = 20` |
| 任务调度策略 | playbook: `strategy: free`（主机间无依赖时可用）|
| 纯配置 play 关闭 facts | playbook: `gather_facts: false` |

---

## 推荐阅读

- [Ansible 官方最佳实践](https://docs.ansible.com/ansible/latest/tips_tricks/ansible_tips_tricks.html)
- [Jeff Geerling 的 roles](https://github.com/geerlingguy) — 社区最广泛参考
- [dev-sec hardening roles](https://github.com/dev-sec) — 安全加固参考
- [Ansible Lint 规则](https://ansible.readthedocs.io/projects/lint/)
- [Molecule 文档](https://ansible.readthedocs.io/projects/molecule/)
- [Ansible Builder / EE](https://ansible.readthedocs.io/projects/builder/)
