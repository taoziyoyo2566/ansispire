# 技术调查报告 — 迁移方案 + 项目框架深度审计

## 1. 调查概览
- **调查 ID**: `IVG-DEEP-AUDIT-2026-05-15`
- **关联工作**: feat-reality-migration plan-2026-05-15、IVG-REALITY-OPS-VERIFICATION、review-2026-05-15-gemini-r1
- **调查类型**: 可行性研究 + 架构审计（多目标）
- **目标**:
  1. 用 [pre-accept-verification](../../../../../home/netcup/.claude/projects/-home-netcup-workspace-ansispire/memory/feedback_pre_accept_verification.md) 规范重审 reality 迁移方案——找出之前漏掉的可验证但未验证的声明。
  2. 审计 Ansispire 现有框架，识别迁移会**继承**的潜在缺陷，让阶段 1 实施前心里有数。
- **触发**: user 2026-05-15 在 D6 修订后明确要求"用这种方式（可验证就验证、有现成方案先查、不臆断）重新审查整体设计"。

## 2. 背景
- D6 决策反转事件（自写 `_VaultedString` → 复用 `AnsibleLoader`）暴露了一类系统性疏漏：accept Gemini findings 时只看字面合理性、不做实证。
- 既然方案要进 round 2 实施，必须先把可验证项跑完，避免实施时才发现"plan §X 里那行 API 用法不对"。
- 项目框架本身已两年滚动开发（不计 vendor），plan 里某些"复用现有模式"的假设需要对照实际代码确认。

## 3. 调查方法
对每条具体技术声明，跑三步：
1. **可验证性判定**: API 行为 / 文件存在 / 配置内容 / 命令存在性 / 字段类型——可执行验证就跑。
2. **项目约定核查**: grep / read 既有同类文件做对比。
3. **是否重复造轮子**: 引入新代码前先 search 标准库、Ansible、项目内既有 plugin。

工具：`Bash`（`python -c`、`grep -rn`、`source .venv/bin/activate && ansible-vault ...`、`git log`）、`Read`、`WebFetch`（保留备用，本次未触发）。

## 4. 证据与发现

### 4.1 已验证为真（plan / IVG 主要声明）

| ID | 声明 | 验证手段 | 结论 |
|---|---|---|---|
| V1 | `ansible.parsing.yaml.loader.AnsibleLoader` 能 load `!vault` 不报错 | `python -c` 执行 | ✅ 真，但 `EncryptedString.__str__` 触发解密尝试（footgun，已在 plan §3.3a 警告） |
| V2 | PyYAML `safe_load` 见未知 tag 抛 `ConstructorError` | `python -c` 执行 | ✅ 真 |
| V3 | reality-ops `feat/tag-acl-routing` HEAD 自 IVG 写作以来未变 | `git fetch + git log` | ✅ 仍是 `1fb10f0`，29 份明文私钥情况未变 |
| V4 | Ansispire `requirements.txt` 含 `ansible-core>=2.20.5` + `cryptography>=42.0.0` | `cat` + `pyproject.toml` 对比 | ✅ 真，且 `pyproject.toml` 与 `requirements.txt` 一致 |
| V5 | `vps_manager` 不 import 任何跨 plugin 模块 | `grep -nE 'from plugins\|import plugins' plugins/vps_manager/*.py` | ✅ 零匹配，plan §3.4 的"目录范式复用，不 import 模块"约束有先例 |
| V6 | `.vault_pass` 已 gitignore | `grep vault .gitignore` | ✅ `.gitignore` 第 2 行 `.vault_pass`、第 3 行 `*.vault_pass`、第 21 行 `inventory/**/vault.yml` |
| V7 | `runtime/state/` 是 Ansispire 既有目录 | `ls runtime/state/` | ✅ `tasks/` + `vps_inventory.yml` 已存在；plan D1 选 `runtime/state/reality_users/` 与现有约定一致 |
| V8 | `config/manifest.yml::ansispire_ports` 是控制端 host 端口，不与 reality user 端口冲突 | `cat config/manifest.yml` | ✅ semaphore_host=3300、audit_sink_host=3310、prometheus_host=9390——全部 controller 上 |

### 4.2 Bugs in plan（需修订）

| ID | 严重度 | 位置 | 问题 | 证据 | 建议修订 |
|---|---|---|---|---|---|
| **B1** | 🔴 High | plan §3.3a `encrypt_field` 草案 | 缺 `--encrypt-vault-id default` 标志——直接调 `ansible-vault encrypt_string --vault-password-file .vault_pass` 在本项目会报 `vault-ids default,default are available to encrypt. Specify the vault-id to encrypt with --encrypt-vault-id` | 实测：`echo test \| ansible-vault encrypt_string --vault-password-file .vault_pass --stdin-name foo` → ERROR。加 `--encrypt-vault-id default` → 成功输出 vault 块 | 加 `--encrypt-vault-id default` 到 subprocess 参数 |
| **B2** | 🟡 Medium | plan §2 隐含的"acl_matrix 落到 inventory/prod/group_vars/all.yml" | 实际路径是**目录**而非单一文件：`inventory/prod/group_vars/all/` 含 `vars.yml`（无 `vault.yml`） | `ls inventory/prod/group_vars/all/` 仅 `vars.yml` | 阶段 2 落地时新建 `inventory/prod/group_vars/all/reality.yml`（Ansible 自动合并），不污染 vars.yml |
| **B3** | 🟡 Medium | plan §4 T1.5 未声明 CI 接入 | `Makefile::verify` 包含 `test-vps-manager`，但 `.github/workflows/ci.yml` python-tests 步骤只跑 `make test-eda` + `make test-filters`——**vps_manager 测试不在 CI 跑**。reality_manager 若只加 Makefile target 不动 ci.yml，会沿用同一漏洞 | `grep test- .github/workflows/ci.yml` → 只有 test-eda / test-filters | T1.5 增子任务：同时改 `.github/workflows/ci.yml::python-tests` 加 `make test-reality-manager` |
| **B4** | 🟢 Low | plan §3.1 `runtime/state/reality_users/` 范围说明未提日志 | `vps_manager` 用 `runtime/logs/vps_manager/`（execution-environment.yml 同目录约定），plan 没说 reality_manager 是否要 `runtime/logs/reality_manager/` | `ls runtime/logs/` → 已有 `vps_manager/` 子目录 | plan §3.1 加一行：CLI 行为日志写 `runtime/logs/reality_manager/<date>.log` |

### 4.3 Latent risks（迁移会继承的现有项目问题，不阻塞阶段 1，但应登记）

| ID | 严重度 | 来源 | 问题 |
|---|---|---|---|
| **R1** | 🟡 Medium | `ARCHITECTURE.md §4` vs 实际 | ARCHITECTURE 声明 "Audit Integrity: Every action must leave a trace"，但 plugin CLI 操作（vps_manager + 未来 reality_manager）**不发事件到 Audit Plane**（sink/relay/reactor 只消费 Semaphore API events）。runtime/logs/vps_manager/ 是本地日志，不在审计链路里。 |
| **R2** | 🟢 Low | `execution-environment.yml` | EE python deps 里没显式列 `cryptography`（依赖 ansible-core 的传递依赖）。EE base image 更换时存在断链风险。不影响 reality_manager 阶段 1（CLI 在本地 venv 跑），但若未来把 CLI 容器化运行需补 |
| **R3** | 🟡 Medium | Vault 位置 SSOT 不明 | 两套并存：`inventory/local/vault.yml`（被 deploy_hub.yml 引用）+ `inventory/dev/group_vars/all/vault.yml`（per-env），ARCHITECTURE.md 不指定哪一套是 canonical。reality_manager 走 per-field encrypt_string 不受影响，但项目整体存在 vault 文件位置二义性 |
| **R4** | 🟢 Low | feature-map sync rule | INDEX.md 同步纪律列了 `roles/ playbooks/ controller/ extensions/eda/ inventory/ Makefile config/manifest.yml`——**不含 `plugins/`**。但 vps_manager 已经登记进 INDEX.md §3.4。规则与实践不一致，未来 reality_manager 落地时同样需要登记，但规则文本没保证 |
| **R5** | 🟢 Low | 测试模式 | vps_manager 测试用 `unittest` + `sys.path.insert(0, str(Path(__file__).resolve().parents[3]))` 手动接根目录——非 pytest 项目级 conftest 模式。reality_manager 跟随同一模式会延续 hack |

### 4.4 已推翻（仍然成立）

| ID | 之前认为 / 别人提议 | 重审结论 |
|---|---|---|
| RJ1 | Gemini r1 finding 2.2 "与 manifest.yml 端口冲突" | 仍然 reject；见 V8 |
| RJ2 | Gemini r1 framing "`add --force` ≈ rotate" | 仍然 reject；语义不等价 |
| RJ3 | 自己第一遍方案"自写 `_VaultedString`" | 已 D6 反转，复用 `AnsibleLoader`；本次审计 V1 再次确认 AnsibleLoader 行为可靠 |

### 4.5 漏掉的视角（self-audit 真正命中）

1. **`encrypt_string` 命令实测**: D6 决策时只验证了"AnsibleLoader 能读"——没验证"ansible-vault encrypt_string 命令实际怎么调"。导致 B1 漏到现在才发现。**教训**：plan 里写 subprocess 调用的命令行，必须当场跑一次实测。
2. **`inventory/prod/group_vars/all` 是目录而非文件**: plan §2 表格里写"inventory/prod/group_vars/all.yml"（隐含单一 YAML 文件）。实测是目录含 `vars.yml`。**教训**：plan 里写的路径必须 `ls` 过。
3. **CI 与 Makefile 的 drift**: `make verify` 包含 vps_manager 测试，CI 没跑。是上游项目层面就存在的问题——我假设"加 Makefile target 就自动进 CI"。**教训**：CI 是单独的 SSOT，必须显式核对。
4. **vps_manager 1175 行 vs 我的 plan T1.3 预算 45min**: vps_manager.py 1175 行做 VPS lifecycle 是有 task queue + archive + redaction + multi-action 这些复杂功能；reality_manager 范围远小（4 个 subcommand），但 plan 没有给量化对照。**信号**：阶段 1 预算 ~2h 仍合理（reality_manager 没 task queue / archive 这些），但要预留 vault 子进程交互的调试时间。

## 5. 结论与建议

### 5.1 总判决
- **Plan 方向不变**：D1-D6 决策依然成立，阶段 1 路径仍是 plugin + per-field vault + UserStore 抽象。
- **修订 4 处 bug**（B1-B4），登记 5 项继承风险（R1-R5），不阻塞 round 2 实施。
- **方法论收获**：self-audit 流程发现 4 个具体可执行验证（V1-V8 + B1-B4），证明 pre-accept-verification 规范确实捕到了第一遍漏掉的问题。

### 5.2 阶段 1 实施前必须先落的 plan 修订（4 项）

1. **plan §3.3a**: `encrypt_field` 命令行加 `--encrypt-vault-id default`（B1）
2. **plan §2 Gap Analysis 表**: 修正 acl_matrix 目标位置为 `inventory/prod/group_vars/all/reality.yml`（B2）
3. **plan §4 T1.5**: 拆出 T1.5b "更新 `.github/workflows/ci.yml::python-tests` 跑 reality_manager 测试"（B3）
4. **plan §3.1 / §3.3a**: 加 `runtime/logs/reality_manager/` 日志目录约定（B4）

### 5.3 不动 plan，但要记下的项目层风险（5 项）

1. **R1 Audit Plane 集成缺失** → 升级到 IVG §6.2 阶段 6 之后的项目级 hardening 任务（不是 reality 专属）
2. **R2 EE 缺 cryptography** → 升 backlog，等 CLI 容器化场景出现时再处理
3. **R3 Vault 位置 SSOT 不明** → 升 backlog，建议未来一次性把 `inventory/local/vault.yml` 与 `inventory/{env}/group_vars/all/vault.yml` 二选一
4. **R4 feature-map sync 规则不含 `plugins/`** → 提议把 INDEX.md §0 同步纪律的清单加上 `plugins/`（小幅 CLAUDE.md 调整）
5. **R5 测试模式手动 sys.path** → 升 backlog，未来一次性引入 conftest.py 让所有 plugin 测试更标准

### 5.4 经验教训
- **凡 plan 里写具体命令行 / 调 subprocess / 调 stdlib API 的——当场跑一次**。这次 B1 就是因为没在 plan 草案阶段实测 `encrypt_string` 命令。
- **路径声明 → `ls`**；**字段类型声明 → `python -c`**；**API 行为声明 → 实跑或读源码**。不要凭"应该是这样"。
- 项目里两个声称统一的 SSOT（CI vs Makefile、vault 位置、ARCHITECTURE 声明 vs 实践）都有 drift——所以**凡是迁移要 hook 到的现有约定，都要 cross-check 文档与代码**。

## 6. 关联验证
- **TSVS 引用**: 暂无；阶段 1 实施时建立 `docs/reference/test-specs/TEST-REALITY-MGR-001.md`。
- **验证结果**: N/A（本次为审计；落实施验证在阶段 1 round 2）。

---
*Generated by Ansispire Investigation Engine — deep audit applying pre-accept-verification discipline retroactively to plan-2026-05-15.*
