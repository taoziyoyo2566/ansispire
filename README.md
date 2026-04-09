# Ansible 完整参考项目

基于 Ansible 官方最佳实践与社区共识构建的脚手架，包含 dummy 内容。
用于学习 Ansible 的所有主要功能、设计模式和使用技巧。

---

## 完整目录结构

```
ansible-demo/
├── ansible.cfg                          # 项目级配置（优先于全局）
├── requirements.yml                     # 外部 roles + collections 依赖
├── Makefile                             # 常用命令快捷入口
├── .ansible-lint                        # Lint 规则（profile: production）
├── .pre-commit-config.yaml              # 提交前检查（lint/secret扫描/格式）
├── .yamllint                            # YAML 格式规范
├── .gitignore
│
├── inventory/
│   ├── production/                      # 生产环境
│   │   ├── hosts.ini                    # 静态 inventory（.ini 格式）
│   │   ├── group_vars/
│   │   │   ├── all/
│   │   │   │   ├── vars.yml             # 明文公共变量
│   │   │   │   └── vault.yml            # ansible-vault 加密敏感变量
│   │   │   ├── webservers/vars.yml      # webservers 组专用变量
│   │   │   └── dbservers/vars.yml       # dbservers 组专用变量
│   │   └── host_vars/
│   │       └── web01.example.com/vars.yml  # 主机级变量（最高优先级）
│   ├── staging/                         # Staging 环境（覆盖部分生产变量）
│   │   ├── hosts.ini
│   │   └── group_vars/all/vars.yml
│   └── dynamic/
│       ├── aws_ec2.yml                  # AWS EC2 动态 inventory 插件配置
│       └── custom_inventory.py          # 自定义动态 inventory 脚本（CMDB 示例）
│
├── playbooks/
│   ├── site.yml                         # 主 Playbook（串联所有 Play）
│   ├── rolling_update.yml               # 滚动更新（serial/delegate_to/run_once）
│   ├── advanced_patterns.yml            # 高级用法全集（教学参考）
│   └── vault_demo.yml                   # Vault 工作流完整演示
│
├── roles/
│   ├── common/                          # 所有主机基础配置
│   │   ├── defaults/main.yml            # 最低优先级的可覆盖默认变量
│   │   ├── vars/
│   │   │   └── os/                      # OS 特定变量（include_vars + first_found）
│   │   │       ├── Debian.yml
│   │   │       ├── RedHat.yml
│   │   │       └── default.yml
│   │   ├── tasks/
│   │   │   ├── main.yml                 # 入口（import_tasks 引入子文件）
│   │   │   ├── preflight.yml            # 前置检查（OS/版本/磁盘/必填变量）
│   │   │   ├── packages.yml             # 包安装、用户管理、block/rescue
│   │   │   └── security.yml             # SSH加固、防火墙、async任务
│   │   ├── handlers/main.yml            # SSH/cron 重启，listen 机制
│   │   ├── templates/motd.j2            # Jinja2 模板（ansible_managed/循环/条件）
│   │   └── meta/
│   │       ├── main.yml                 # Galaxy 元数据与依赖声明
│   │       └── argument_specs.yml       # 角色参数校验（Ansible 2.11+）
│   │
│   ├── webserver/                       # Nginx 角色
│   │   ├── defaults/main.yml
│   │   ├── vars/main.yml                # 内部常量（不希望被外部覆盖）
│   │   ├── tasks/
│   │   │   ├── main.yml
│   │   │   ├── preflight.yml            # vhost 配置校验
│   │   │   ├── install.yml              # 安装 Nginx、目录、静态文件
│   │   │   ├── configure.yml            # 主配置（validate/blockinfile/replace）
│   │   │   └── vhosts.yml               # 虚拟主机（symlink管理/过期清理）
│   │   ├── handlers/main.yml            # listen 多事件绑定
│   │   ├── templates/
│   │   │   ├── nginx.conf.j2            # 引用 facts（vcpus/内存）
│   │   │   └── vhost.conf.j2            # 按 item 条件渲染 SSL/PHP-FPM
│   │   ├── files/default_index.html     # copy 模块的静态文件
│   │   └── meta/
│   │       ├── main.yml                 # 声明依赖 common role
│   │       └── argument_specs.yml
│   │
│   └── database/                        # MySQL 角色
│       ├── defaults/main.yml
│       ├── tasks/
│       │   ├── main.yml
│       │   ├── install.yml
│       │   └── configure.yml            # no_log、community.mysql、cron 备份
│       ├── handlers/main.yml
│       ├── templates/my.cnf.j2          # 按 db_role（primary/replica）条件渲染
│       └── meta/
│           ├── main.yml
│           └── argument_specs.yml
│
├── library/
│   └── app_config.py                    # 自定义模块（JSON 配置文件管理，幂等）
│
├── filter_plugins/
│   └── custom_filters.py                # 自定义 Jinja2 过滤器（6个示例）
│
├── lookup_plugins/
│   └── config_value.py                  # 自定义 Lookup 插件（CMDB 配置查询）
│
├── callback_plugins/
│   └── human_log.py                     # 自定义 Callback（人类友好输出+耗时）
│
└── molecule/
    └── webserver/
        ├── molecule.yml                 # Docker driver 测试配置
        ├── converge.yml                 # 测试执行 Playbook
        └── verify.yml                  # 断言验证（assert + uri + stat）
```

---

## 快速开始

```bash
# 1. 安装依赖
pip install ansible ansible-lint molecule[docker] pre-commit
ansible-galaxy role install -r requirements.yml
ansible-galaxy collection install -r requirements.yml

# 2. 初始化 pre-commit
pre-commit install

# 3. 创建 vault 密码文件（加入 .gitignore）
echo "your-vault-password" > .vault_pass
chmod 600 .vault_pass

# 4. 加密敏感变量文件
ansible-vault encrypt inventory/production/group_vars/all/vault.yml

# 5. 语法检查
ansible-playbook playbooks/site.yml --syntax-check

# 6. Dry-run
ansible-playbook playbooks/site.yml --check --diff

# 7. 运行 Molecule 测试
molecule test -s webserver
```

---

## 核心概念

### 1. 变量优先级（从低到高）

```
role defaults/         ← 最容易被覆盖，用于"合理默认值"
inventory group_vars/  ← 组级变量
inventory host_vars/   ← 主机级变量
play vars:             ← playbook 中直接写的 vars
role vars/             ← 内部常量，比 group_vars 优先级高！
task vars:             ← task 级 vars（include_role 的 vars）
extra_vars -e          ← 命令行 -e，最高优先级，不可被覆盖
```

> 陷阱: `vars/main.yml` 的优先级高于 `group_vars`，不适合放用户可配置的变量。

### 2. import_tasks vs include_tasks

| 特性 | `import_tasks`（静态）| `include_tasks`（动态）|
|------|----------------------|----------------------|
| 解析时机 | 编译期 | 运行期 |
| Tags 透传 | ✅ 支持 | ❌ 不支持 |
| 动态文件名 | ❌ 不支持 | ✅ 支持 |
| loop 支持 | ❌ | ✅ |
| 调试可见性 | 好（提前展开）| 差（运行时才知道）|

**经验法则:** 默认用 `import_tasks`；需要动态文件名或 loop 时才用 `include_tasks`。

### 3. Tags 约定

```bash
# 执行指定 tag
ansible-playbook site.yml --tags nginx,config

# 跳过指定 tag
ansible-playbook site.yml --skip-tags hardening

# 列出所有 tag
ansible-playbook site.yml --list-tags

# never tag: 默认不执行，需要显式触发
# tasks:
#   - name: Full OS upgrade
#     tags: [upgrade, never]
ansible-playbook site.yml --tags upgrade  # 才会运行 never tag 的 task
```

本项目 Tag 规范:

| Tag | 含义 |
|-----|------|
| `always` | 始终执行（preflight 检查）|
| `never` | 默认跳过（升级、破坏性操作）|
| `preflight` | 前置检查 |
| `packages` | 包安装 |
| `hardening` | 安全加固 |
| `nginx` / `mysql` | 组件相关 |
| `verify` | 验证类（只读）|

### 4. Handlers 设计原则

```yaml
# ✅ 正确: 用 listen 解耦，纯服务操作
- name: Reload Nginx
  ansible.builtin.systemd:
    name: nginx
    state: reloaded
  listen: Reload Nginx

# ❌ 错误: handler 中包含 when 条件或复杂逻辑
- name: Restart service
  ansible.builtin.systemd:
    name: nginx
    state: restarted
  when: some_condition    # 不应在 handler 中放条件

# meta: flush_handlers — 立即执行已触发的 handler（不等 play 结束）
- name: Force handler execution now
  ansible.builtin.meta: flush_handlers
```

### 5. Role Argument Validation（Ansible 2.11+）

在 `meta/argument_specs.yml` 中声明参数规范，Ansible 在执行 role 前自动校验：

```yaml
argument_specs:
  main:
    options:
      my_required_var:
        type: str
        required: true
      my_optional_var:
        type: int
        required: false
        default: 8080
```

### 6. OS 特定变量模式（include_vars + first_found）

```yaml
- name: Load OS-specific variables
  ansible.builtin.include_vars: "{{ lookup('ansible.builtin.first_found', files) }}"
  vars:
    files:
      files:
        - "os/{{ ansible_distribution }}-{{ ansible_distribution_major_version }}.yml"
        - "os/{{ ansible_os_family }}.yml"
        - "os/default.yml"
      paths: ["{{ role_path }}/vars"]
```

---

## 功能速查表

| 功能 | 示例位置 |
|------|---------|
| `ansible.cfg` 完整配置 | `ansible.cfg` |
| 多环境 Inventory | `inventory/production/` vs `inventory/staging/` |
| group_vars 目录（明文+vault 分离）| `group_vars/all/vars.yml` + `vault.yml` |
| host_vars 主机级覆盖 | `host_vars/web01.example.com/` |
| AWS EC2 动态 inventory 插件 | `inventory/dynamic/aws_ec2.yml` |
| 自定义动态 inventory 脚本 | `inventory/dynamic/custom_inventory.py` |
| Role Argument Validation | `roles/*/meta/argument_specs.yml` |
| Preflight 前置检查模式 | `roles/*/tasks/preflight.yml` |
| OS 特定变量（first_found）| `roles/common/vars/os/` + `tasks/main.yml` |
| `import_tasks` vs `include_tasks` | `roles/common/tasks/main.yml` |
| `loop` + `loop_control` | `roles/common/tasks/packages.yml` |
| `subelements` 嵌套循环 | `roles/common/tasks/packages.yml` |
| `block` / `rescue` / `always` | `roles/common/tasks/packages.yml` |
| `register` + `changed_when` + `failed_when` | `roles/common/tasks/security.yml` |
| `async` / `poll` 异步任务 | `roles/common/tasks/security.yml` |
| `check_mode: false` 感知 | `roles/common/tasks/security.yml` |
| `set_fact` + `ternary` | `roles/common/tasks/security.yml` |
| `never` 标签 | `roles/common/tasks/security.yml` |
| `validate` 写前校验 | `roles/webserver/tasks/configure.yml` |
| `blockinfile` / `replace` | `roles/webserver/tasks/configure.yml` |
| `creates` 幂等条件 | `roles/webserver/tasks/configure.yml` |
| `throttle` 并发控制 | `roles/webserver/tasks/configure.yml` |
| Handler `listen` 机制 | `roles/webserver/handlers/main.yml` |
| `no_log: true` 敏感数据保护 | `roles/database/tasks/configure.yml` |
| 主从条件渲染模板（`db_role`）| `roles/database/templates/my.cnf.j2` |
| `vars_prompt` 交互输入 | `playbooks/advanced_patterns.yml` |
| `add_host` / `group_by` 动态分组 | `playbooks/advanced_patterns.yml` |
| `meta: flush_handlers` / `end_host` / `end_play` | `playbooks/advanced_patterns.yml` |
| `throttle` 任务级并发控制 | `playbooks/advanced_patterns.yml` |
| `environment` 任务环境变量 | `playbooks/advanced_patterns.yml` |
| `hostvars` / `groups` 魔法变量 | `playbooks/advanced_patterns.yml` |
| 内置 lookups（file/env/pipe/password）| `playbooks/advanced_patterns.yml` |
| `ansible.builtin.uri` REST API | `playbooks/advanced_patterns.yml` |
| `ansible.builtin.raw` / `script` | `playbooks/advanced_patterns.yml` |
| `include_role` / `import_role` | `playbooks/advanced_patterns.yml` |
| `selectattr` / `rejectattr` / `combine` | `playbooks/advanced_patterns.yml` |
| `json_query` (jmespath) | `playbooks/advanced_patterns.yml` |
| `serial` 滚动更新 | `playbooks/site.yml` |
| `strategy: free` / `linear` | `playbooks/site.yml` |
| `gather_subset` 性能优化 | `playbooks/site.yml` |
| `delegate_to` / `run_once` | `playbooks/rolling_update.yml` |
| `until` / `retries` / `delay` 轮询 | `playbooks/rolling_update.yml` |
| Ansible Vault 完整工作流 | `playbooks/vault_demo.yml` |
| 自定义模块（Python）| `library/app_config.py` |
| 自定义 Jinja2 过滤器 | `filter_plugins/custom_filters.py` |
| 自定义 Lookup 插件 | `lookup_plugins/config_value.py` |
| 自定义 Callback 插件 | `callback_plugins/human_log.py` |
| `ansible_managed` 模板头 | `roles/*/templates/*.j2` |
| Molecule 测试（Docker driver）| `molecule/webserver/` |
| pre-commit + ansible-lint 集成 | `.pre-commit-config.yaml` + `.ansible-lint` |

---

## Vault 工作流速查

```bash
# 加密文件
ansible-vault encrypt group_vars/all/vault.yml

# 查看（不落盘解密）
ansible-vault view group_vars/all/vault.yml

# 编辑
ansible-vault edit group_vars/all/vault.yml

# 加密单个字符串，直接嵌入 vars.yml
ansible-vault encrypt_string 'MyPassword123' --name 'vault_db_password'

# 多 vault-id（不同环境用不同密码）
ansible-playbook site.yml \
  --vault-id prod@.vault_pass_prod \
  --vault-id dev@.vault_pass_dev
```

**命名约定:** vault 文件中的变量统一加 `vault_` 前缀，在明文 vars 中引用：
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

# 同时使用多个 inventory 源（用冒号分隔）
ansible-playbook site.yml -i inventory/production:inventory/dynamic

# 在 ansible.cfg 中配置多源
[defaults]
inventory = inventory/production:inventory/dynamic
```

---

## 常用命令

```bash
make install           # 安装 roles + collections
make lint              # ansible-lint 检查
make dry-run           # --check --diff
make deploy-staging    # 部署 staging
make deploy-prod       # 部署 production（有确认提示）

# Ad-hoc 命令
ansible all -m ansible.builtin.ping
ansible webservers -m ansible.builtin.setup -a "filter=ansible_distribution*"
ansible all -m ansible.builtin.shell -a "df -h" --become
ansible webservers -m ansible.builtin.service -a "name=nginx state=restarted" --become

# 按 tag 执行
ansible-playbook playbooks/site.yml --tags preflight,packages
ansible-playbook playbooks/site.yml --skip-tags hardening

# 按主机过滤
ansible-playbook playbooks/site.yml --limit web01.example.com
ansible-playbook playbooks/site.yml --limit 'webservers:!web03*'

# Molecule
molecule test -s webserver      # 完整测试（create+converge+verify+destroy）
molecule converge -s webserver  # 只执行 converge（不销毁，调试用）
molecule verify -s webserver    # 只跑 verify
molecule login -s webserver     # SSH 进入测试容器
```

---

## 性能优化建议

| 技巧 | 配置 |
|------|------|
| SSH 持久连接 | `ansible.cfg`: `ssh_args = -o ControlPersist=60s` |
| 管道传输 | `ansible.cfg`: `pipelining = true` |
| fact 缓存 | `ansible.cfg`: `fact_caching = jsonfile` |
| 精简 facts | playbook: `gather_subset: [min, hardware]` |
| 并发主机数 | `ansible.cfg`: `forks = 20` |
| 策略选择 | playbook: `strategy: free`（独立主机可用）|
| 减少 facts 收集 | 纯配置 play: `gather_facts: false` |

---

## 推荐阅读

- [Ansible 官方最佳实践](https://docs.ansible.com/ansible/latest/tips_tricks/ansible_tips_tricks.html)
- [Jeff Geerling 的 roles 源码](https://github.com/geerlingguy) — 社区最广泛参考
- [dev-sec hardening roles](https://github.com/dev-sec) — 安全加固 role 参考
- [Ansible Lint 规则文档](https://ansible.readthedocs.io/projects/lint/)
- [Molecule 文档](https://ansible.readthedocs.io/projects/molecule/)
