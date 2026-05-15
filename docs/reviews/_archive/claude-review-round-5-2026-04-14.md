# Claude 架构审查报告 — Round 5（架构改进轮）

日期: 2026-04-14
执行者: Claude (Sonnet 4.6)
参照:
- [Review Iteration Charter](./review-iteration-charter.md)
- [Review Phase Closeout (Round 1-4)](./review-phase-closeout-2026-04-09.md)
- [Round 5 变更日志](./round-5-change-log-2026-04-14.md)

---

## 原始目的

本仓库是 Ansible 开发初始模板项目。前一阶段（Round 1-4，2026-04-09）已完成"教学正确性、默认路径自洽性、文档一致性"的收口。

本轮目标不同于前一阶段：以 **2025-2026 年主流设计和未来趋势** 为基准，从架构层面全面审查和改进项目，使其更符合当前社区最佳实践，并为未来功能（EDA、AAP 2.7+、多云）预留接口。

## 本轮关注范围

1. 现代工具链配置（ansible-navigator、Execution Environment）
2. 安全默认配置（host_key_checking、密钥管理分层）
3. Python 依赖管理（pyproject.toml、uv 支持）
4. 集成测试完整性（full-stack Molecule 场景）
5. CI/CD 流水线补强（dry-run 阶段、full-stack 矩阵）
6. 面向未来的预留配置（EDA、多云 inventory）
7. 开发体验（Makefile、editorconfig、Dependabot）
8. 文档完整性（Role README、tox-ansible）

## 本轮不展开

- 不修改 role 的核心实现逻辑（common/webserver/database 功能不变）
- 不扩展新的操作系统支持
- 不引入 Ansible Lightspeed / AI 辅助配置（仅在文档中提及）
- 不实现 EDA 规则（仅提供骨架和文档）
- 不实现 Azure/GCP 动态 inventory（仅提供注释模板）

## 判断标准

每项改动必须满足：
1. 符合 2025-2026 官方推荐或社区主流实践
2. 不破坏现有功能的可运行性
3. 改进幅度与复杂度代价相称（不过度工程化）
4. 有预留配置的项，须以注释/骨架形式存在，不影响默认运行路径

---

## 架构分析

### 当前状态评估（改进前）

基于对官方文档、ansible-lint 最新版本（v25.x）、Molecule 最新实践、AAP 路线图的综合研究：

| 维度 | 改进前状态 | 问题 |
|------|-----------|------|
| 执行工具 | 仅支持 ansible-playbook | ansible-navigator 是现代推荐工具，缺少配置 |
| 安全默认值 | host_key_checking=false（硬编码） | 生产环境安全风险，应默认为 true |
| SSH 安全 | StrictHostKeyChecking=no | 关闭 MITM 检测，应改为 accept-new |
| 密钥管理 | 仅 ansible-vault | 企业环境需要 HashiCorp Vault / AWS SM 等 |
| Python 依赖 | 无声明文件 | 开发者无法快速搭建一致的开发环境 |
| Molecule 测试 | 3 个独立场景 | 缺少集成测试（全链路场景） |
| CI/CD | 无 dry-run 阶段 | PR 无法预览实际变更效果 |
| 开发工具 | Makefile 不完整 | 缺少 setup、ee-build、navigator 等关键命令 |
| 文档 | 无 Role README | 每个 role 缺少独立的使用文档 |
| 未来预留 | 无 EDA/多云骨架 | 无迁移路径 |

### 改进决策

#### 1. ansible-navigator 配置（Task #1）

**背景**: ansible-navigator 是 Red Hat 推荐的 ansible-playbook 替代工具，支持 EE 容器化执行和交互式 TUI。AAP 2.x 内部即使用此工具。

**决策**: 新增 `.ansible-navigator.yml`，默认 `mode: stdout`（兼容 CI），配置与 `execution-environment.yml` 对齐。

**架构原则**: 工具链统一，本地开发与 CI/AAP 行为一致。

#### 2. 外部密钥管理器预留（Task #2）

**背景**: 企业环境的密钥管理通常需要 HashiCorp Vault、AWS Secrets Manager 或 Azure Key Vault，ansible-vault 仅适合小型团队或开发环境。

**决策**: 新增 `secrets_external.example.yml`，提供三种方案的注释示例；在 `requirements.yml` 中预留对应 collection。不破坏现有 ansible-vault 工作流。

**架构原则**: 提供分层密钥管理的迁移路径，不强制升级。

#### 3. 安全默认值修复（Task #3）

**背景**: `host_key_checking=false` 是开发便利性设置，不应成为默认值。生产模板应默认安全。`StrictHostKeyChecking=no` 完全禁用 MITM 检测，有安全风险。

**决策**:
- `ansible.cfg`：注释 `host_key_checking`（恢复默认 true）
- SSH args：`StrictHostKeyChecking=no` → `StrictHostKeyChecking=accept-new`
- 非生产环境通过 `ANSIBLE_HOST_KEY_CHECKING=False` 环境变量覆盖

**架构原则**: 安全默认值（secure by default），便利性通过显式覆盖实现。

#### 4. Python 依赖管理（Task #4）

**背景**: 2025-2026 趋势是用 `pyproject.toml` + `uv` 管理 Python 依赖。uv 速度是 pip 的 10-100 倍，且 `ansible-dev-tools` 已集成 uv 支持。

**决策**: 新增 `pyproject.toml`，分 core/test/cloud/dev 四个依赖组，同时兼容 uv 和传统 pip。

**架构原则**: 声明式依赖管理，开发环境可复现。

#### 5. ansible.cfg collections_path（Task #5）

**背景**: 未显式声明 `collections_path` 时依赖默认路径，不同环境行为可能不一致。

**决策**: 显式声明 `collections_path = collections:~/.ansible/collections`，与 `roles_path` 风格一致。

#### 6. Makefile 完善（Task #6）

**背景**: 原 Makefile 缺少 `setup`、`ee-build`、`navigator` 等与新工具链对应的命令。

**决策**: 重写 Makefile，覆盖完整生命周期（setup/lint/test/deploy/ee/vault/clean），自动检测 uv/pip。

#### 7-8. .editorconfig + Dependabot（Task #7、#8）

**背景**: 团队协作需要统一编辑器配置；依赖版本自动更新是现代项目的标准实践。

**决策**: 新增两个标准配置文件，与现有 `.yamllint` 设置对齐。

#### 9. full-stack 集成测试（Task #9）

**背景**: 现有 3 个 Molecule 场景各自独立测试单个 role，但 site.yml 的实际运行路径是三个 role 协同工作。缺少端到端集成验证。

**决策**: 新增 `molecule/full-stack/` 场景，按 site.yml 顺序（common→webserver→database）在单机上执行，并验证服务共存。

**架构原则**: 测试层次完整（单元测试=单 role，集成测试=全链路）。

#### 10. CI dry-run 阶段（Task #10）

**背景**: PR 审查时，审查者需要能预览实际变更效果而不需要真实主机。

**决策**: 新增 `dry-run` CI 作业（`--check --diff --connection=local`），与 `molecule` 并行运行；同时将 full-stack 加入 molecule 矩阵。

#### 11. tox-ansible（Task #11）

**背景**: `tox-ansible` 是 ansible-dev-tools 生态的标准测试编排工具，支持多 Ansible 版本矩阵。

**决策**: 新增 `tox.ini`，配置 lint 和所有 4 个 molecule 场景，与 `pyproject.toml` 中的测试依赖对齐。

#### 12. Role READMEs（Task #12）

**背景**: 每个 role 缺少独立文档，使用者需要查看源代码才能了解变量和用法。

**决策**: 为 common/webserver/database 各新增 README.md，内容与 `defaults/main.yml` 和 `meta/argument_specs.yml` 保持一致。

#### 13. EDA + 多云 inventory 预留（Task #13）

**背景**:
- Event-Driven Ansible 从 AAP 2.4 开始 GA，增长迅速，是下一阶段的主流趋势
- 当前只有 AWS EC2 动态 inventory，缺少 Azure/GCP 对应配置

**决策**:
- 新增 `extensions/eda/rulebooks/README.md` 骨架，含规则文件示例
- 新增 `azure_rm.yml` 和 `gcp_compute.yml`（全注释，不影响现有 AWS 配置）

---

## 本轮结束问题检查

1. **这轮修改是否更贴近原始目的？** 是。项目目标是"主流最佳实践的 Ansible 初始模板"，所有改动都服务于此目标。

2. **是否把"教学示例"和"默认路径"分得更清楚？** 是。预留配置明确标注为注释，不进入默认执行路径。

3. **是否产生了新的文档漂移？** 无。所有新功能都有对应文档（Role README、EDA README）。

4. **是否引入了新的环境依赖？** 无强制依赖。`uv`/`tox`/`ansible-navigator` 均为可选工具，不影响原有 `ansible-playbook` 工作流。

5. **是否还有未关闭的前置矛盾？** 见下方"遗留问题"。

---

## 遗留问题（本轮未处理）

以下问题来自 `review-iteration-charter.md` 的"已知高优先级尾项"，本轮未处理（范围控制）：

| 问题 | 状态 | 建议下一轮处理 |
|------|------|---------------|
| `README.md` 未同步新增文件（navigator、EDA、full-stack 等） | 未处理 | 建议 Round 6 优先处理 |
| `playbooks/rolling_update.yml` 仍有硬编码 `lb01.example.com` | 未处理 | 低优先级 |
| `roles/common/templates/motd.j2` 依赖根级 `filter_plugins/` | 未处理 | 中优先级 |
