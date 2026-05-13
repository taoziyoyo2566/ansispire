# Round 5 变更日志 — 架构改进轮

日期: 2026-04-14
执行者: Claude (Sonnet 4.6)
参照:
- [Claude 架构审查报告 — Round 5](./claude-review-round-5-2026-04-14.md)
- [Review Iteration Charter](./review-iteration-charter.md)

---

## 原始目的

前一阶段（Round 1-4）已完成教学正确性和默认路径自洽性的收口。

本轮目标：以 2025-2026 年 Ansible 主流设计为基准，从架构层面补强工具链、安全默认值、测试完整性和面向未来的预留配置。

## 本轮变更清单

| # | 文件 | 变更类型 | 摘要 |
|---|------|---------|------|
| 1 | `.ansible-navigator.yml` | 新增 | ansible-navigator 配置（EE 模式、stdout 默认、artifact 存储） |
| 2 | `.gitignore` | 修改 | 新增 `.cache/`、`collections/`、`.venv/`、`uv.lock` 排除项 |
| 3 | `inventory/production/group_vars/all/secrets_external.example.yml` | 新增 | 外部密钥管理器集成示例（HashiCorp Vault/AWS SM/Azure KV，全注释） |
| 4 | `requirements.yml` | 修改 | 预留 community.hashi_vault、azure.azcollection、google.cloud（注释状态） |
| 5 | `ansible.cfg` | 修改 | 注释 host_key_checking（恢复安全默认）、StrictHostKeyChecking 改为 accept-new、新增 collections_path |
| 6 | `Makefile` | 修改 | 重写：新增 setup/ee-build/navigator/navigator-local/clean，完善所有命令的 help 注释 |
| 7 | `.github/workflows/ci.yml` | 修改 | 新增 dry-run 作业、Molecule 矩阵新增 full-stack 场景、ANSIBLE_HOST_KEY_CHECKING 环境变量 |
| 8 | `pyproject.toml` | 新增 | Python 依赖声明（core/test/cloud/dev 分组，支持 uv 和 pip） |
| 9 | `.editorconfig` | 新增 | 跨编辑器格式配置（YAML 2空格、Python 4空格、Makefile Tab） |
| 10 | `.github/dependabot.yml` | 新增 | GitHub Actions 和 pip 依赖自动更新（每周一） |
| 11 | `molecule/full-stack/molecule.yml` | 新增 | Full-stack 集成测试场景配置 |
| 12 | `molecule/full-stack/converge.yml` | 新增 | Full-stack converge playbook（common→webserver→database） |
| 13 | `molecule/full-stack/verify.yml` | 新增 | Full-stack 验证 playbook（三 role 服务共存验证） |
| 14 | `tox.ini` | 新增 | tox-ansible 集成（lint + 4 个 molecule 场景） |
| 15 | `roles/common/README.md` | 新增 | common role 使用文档（变量、依赖、示例、标签） |
| 16 | `roles/webserver/README.md` | 新增 | webserver role 使用文档（变量、vhost 定义、示例） |
| 17 | `roles/database/README.md` | 新增 | database role 使用文档（变量、vault 要求、复制配置） |
| 18 | `extensions/eda/rulebooks/README.md` | 新增 | EDA 目录骨架和规则文件示例（面向未来预留） |
| 19 | `inventory/dynamic/azure_rm.yml` | 新增 | Azure 动态 inventory 配置模板（全注释，预留） |
| 20 | `inventory/dynamic/gcp_compute.yml` | 新增 | GCP 动态 inventory 配置模板（全注释，预留） |
| 21 | `CLAUDE.md` | 新增 | Claude Code 项目级指令（文档强制要求、工作原则） |

## 变更意图详解

### 1. 工具链现代化

**`.ansible-navigator.yml`**

ansible-navigator 是 ansible-playbook 的现代替代，AAP 2.x 内部使用此工具。增加此配置文件后，开发者可以：
- `ansible-navigator run playbooks/site.yml` 使用 EE 容器执行
- `ansible-navigator run playbooks/site.yml --ee false` 等价于 ansible-playbook（本地模式）
- 在 CI 中 `mode: stdout` 自动输出传统日志格式

配置与 `execution-environment.yml` 对齐（相同镜像名、相同 inventory 路径）。

### 2. 安全默认值

**`ansible.cfg` 两处修改**

| 修改前 | 修改后 | 原因 |
|--------|--------|------|
| `host_key_checking = false` | 注释（默认 true） | 生产模板应默认安全 |
| `StrictHostKeyChecking=no` | `StrictHostKeyChecking=accept-new` | accept-new 接受首次连接，后续变更拒绝（MITM 检测） |

非生产环境的使用方式：
- Staging 部署：`ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook ...`（在 Makefile 中显式设置）
- Molecule CI：通过 `ANSIBLE_HOST_KEY_CHECKING: "False"` 环境变量（在 ci.yml 中设置）

### 3. Python 依赖声明

**`pyproject.toml`**

分组策略：
- `dependencies`：最小核心（ansible-core、ansible-lint、yamllint、jmespath）
- `[test]`：molecule 测试工具链
- `[cloud]`：boto3、pymysql、netaddr（与 EE 依赖对齐）
- `[dev]`：pre-commit、detect-secrets
- `[all]`：全部可选依赖

安装方式：
```bash
uv sync --extra all   # 推荐（快）
pip install -e ".[all]"  # 传统方式
```

### 4. 集成测试补强

**`molecule/full-stack/`（3 个文件）**

设计原则：
- 在单机上按 site.yml 顺序执行 common→webserver→database
- `converge.yml` 保留 pre_tasks apt cache 更新，与生产行为一致
- `verify.yml` 最终有一个服务共存断言，验证 nginx 和 mysql 同时运行

这是唯一一个验证三 role 协同工作的场景，弥补了单 role 测试场景无法覆盖的集成路径。

### 5. CI 流水线补强

**`ci.yml` 两处修改**

1. 新增 `dry-run` 作业：
   - 使用 `--check --diff --connection=local` 不需要真实主机
   - 与 `molecule` 并行运行（都依赖 lint+syntax）
   - 让 PR 审查者能预览实际变更 diff

2. Molecule 矩阵新增 `full-stack`：
   - `fail-fast: false` 确保所有场景独立运行

### 6. 面向未来预留

**EDA 骨架**：`extensions/eda/rulebooks/README.md` 包含完整的规则文件示例（Alertmanager webhook 触发器），开箱即用。

**多云 inventory**：`azure_rm.yml` 和 `gcp_compute.yml` 与现有 `aws_ec2.yml` 保持相同的设计模式（keyed_groups、compose、过滤条件），全注释不影响当前 AWS 配置。

## 本轮未做的事

- 未修改 role 核心实现逻辑
- 未扩展操作系统支持范围
- 未实现 EDA 规则
- 未激活 Azure/GCP dynamic inventory（保持注释）
- 未更新主 `README.md`（遗留给下一轮）
- 未修复 `rolling_update.yml` 中的硬编码 lb 主机
- 未修复 `motd.j2` 依赖根级 `filter_plugins/` 的问题

## 自检结果

| 检查项 | 结果 |
|--------|------|
| YAML 语法检查（62 个文件） | 全部通过 |
| ansible.cfg 一致性验证 | 通过（host_key_checking 未硬编码、collections_path 已设置、StrictHostKeyChecking=accept-new） |
| pyproject.toml TOML 语法 | 通过 |
| CI 作业结构验证 | 通过（6 个作业，dry-run 依赖正确，full-stack 在矩阵中） |
| Molecule 场景完整性 | 通过（4 个场景各有 molecule.yml + converge.yml + verify.yml） |
| 关键文件存在性 | 全部 12 个关键新文件存在 |
| 变更文件范围 | 仅在预期范围内（无意外修改） |
