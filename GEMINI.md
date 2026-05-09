# GEMINI.md — Project Governance & Execution Rules

This file is the foundational mandate for all Gemini CLI sessions. It takes precedence over general defaults.

## 0. AI Behavioral Protocol (The Peer Rule)
- **Proactive Challenge**: AI MUST NOT blindly implement changes. Perform an Impact Analysis first.
- **Sync Guard (Consistency)**: Before marking any task as "Done", AI MUST verify:
    1. Does the change affect `SUMMARY.md` (Architecture)? If yes, sync it.
    2. Does the change affect `README.md` (Operational)? If yes, sync it.
    3. Is there a relevant `Feature Map`? Create/Update it.
    **Only after all three are confirmed can the task be closed in the ledger.**

## 1. Workload Classification & Branch Constraints

### The Task Ledger (Branch: `todo`)
- **SSOT**: The authoritative task list is `TODO.md` on the `todo` branch. 
- **Isolation**: `TODO.md` MUST NOT exist on `master` or other code branches.
- **Operation**: Use `git show todo:TODO.md` to read, and `git checkout todo -- TODO.md` to update progress.

### Branch Naming & Semantics
- Pattern: `<type>/<subsystem>-<target>`.
- **Branch Flow**: `feat/*` (or `fix/*`) MUST merge into `dev` first.
- **Promotion**: `dev` -> `stg` (after successful functional tests). `stg` -> `master` (final stable production).
- **feat**: Requires Design RFC.
- **fix**: Requires RCA (Root Cause Analysis).
- **refactor**: No new features. Behavioral equivalence only.

## 2. Layered Context Governance (Lazy-loading)
1. **Design Truth**: `SUMMARY.md` (Global architecture - Read FIRST).
2. **Dynamic Truth**: `todo branch / TODO.md` (Task state - Read SECOND).
3. **Investigation Truth**: `docs/investigations/` (Empirical history - Always check `INDEX.md` first; lazy-load full reports ONLY when task relates to same subsystem or RCA).
4. **Logic Truth**: `docs/features/<name>/summary.md` (Module scope).
5. **Deep Implementation**: `details.md` or Code (Deep-dive on demand).

## 3. Engineering Standards
- **Control vs. Data**: Decouple Controller from Roles.
- **Vendor Integrity**: Note local patches to external roles in SUMMARY.md.
- **Resource Decoupling (Volatile Resource Rule)**: Test VPS, temporary IPs, and developer-specific credentials MUST NOT be committed to the repository. Use git-ignored `inventory/local/*.ini` or `-i "host,"` for volatile testing.
- **Upgrade Safety Protocol (Mandatory Interaction)**: ... (unchanged)

## 4. Git 卫生与完整性协议 (Git Hygiene Protocol)

### 4.1 线性演进 / Linear Development
- **Requirement**: 若任务 B 依赖任务 A，分支必须基于 A 的最新 commit。
- **Command Sequence**: 
    1. `git remote update`
    2. `git checkout dev`
    3. `git pull --ff-only origin dev`
- **Constraint**: 严禁在多个独立 feature 分支中重复创建相同的架构文件。

### 4.2 合并审计 / Pre-merge Audit
- **Condition**: 在执行 `merge` 或 `push` 前。
- **Verification**: 
    - 执行 `git remote update`。
    - 检查 `git status` 确保无 `untracked` 文件或 `divergence`。
    - 检查 `git log --oneline -5` 确认历史基准。

### 4.3 冲突阻断 / Conflict Stop Rule (CRITICAL)
- **Trigger**: 发现 `merge conflict`、`untracked overwrite` 或 `remote divergence`。
- **Protocol**:
    1. **STOP**: 立即停止所有自动化修改脚本。
    2. **LOCK**: 不得执行 `--force` 或任何自动覆盖/删除操作。
    3. **REPORT**: 输出冲突文件清单及 `git diff` 结果。
    4. **REQUEST**: 请求用户人工裁决。

### 4.4 原子提交 / Atomic Commit
- **Pattern**: `<type>(<scope>): <subject>` (e.g., `feat(infra): add docker role`)。
- **Content**: 每次 commit 必须具有功能独立性且经过验证。

## 5. 提问与回声审计协议 (Echo Audit Protocol)
- **Radius Search**: 每当用户提出疑问或指正时，AI 不得仅停留于表面回答，必须执行“半径 3 米”审计：
    1. **关联漏洞**: 检查该问题是否暗示了代码库其他位置存在类似逻辑缺陷。
    2. **文档脱节**: 检查现有的 Guideline 或 README 是否与最新的修改产生了冲突。
    3. **架构隐患**: 评估该提问是否触及了更深层的解耦或安全问题。
- **Self-Correction**: AI 必须在回答中主动列出这些关联发现，并征求处理意见。
## 6. 治理校准与强制准则 (Governance Recalibration)
- **Task-Start Audit**: 每个新任务 `[TASK-XXX]` 开始前，AI 必须复读当前核心禁令（如：不直接 root 运维、不掩盖警告、解耦原则）。
- **Mandatory Gate**: 任何对代码、Inventory 或配置的修改（无论多微小），在声明“完成”或“提出下一步”前，必须提供 `make syntax` 和 `ansible-lint` 的通过日志。
- **Periodic Rule Review**: 每 10 轮对话，AI 必须主动对当前 `GEMINI.md` 的所有规则进行一次“现状一致性审计”。

## 7. 层级上下文治理 (Layered Context Governance)... (remaining unchanged)
- **Evidence-based Verification**: Every unit must provide terminal logs (lint/syntax/test).
- **Test Governance (TSVS)**: ALL functional, loopback, and integration tests MUST be documented using the `docs/test-specs/TEMPLATE.md` format. No task involving "testing" is considered "Done" without a corresponding PASS record in `docs/test-specs/`.
