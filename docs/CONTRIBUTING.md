# 贡献与迭代流程

本文定义了对此仓库进行修改时必须遵守的**质量保证流程**。
所有人（包括 AI 协作者）的每次修改都应按此流程操作。

---

## 一、修改前

### 1. 明确改动范围

在开始修改前，必须能回答：

- 这次改什么？（文件列表）
- 为什么改？（来源：review / bug / 需求）
- 不改什么？（边界）

### 2. 记录当前基线

```bash
# 确认当前工作树状态
git status
git stash list  # 确认没有未处理的 stash

# 如果有未提交的变更，先提交或 stash
git add -A && git commit -m "wip: checkpoint before <task name>"
```

---

## 二、修改中

### 按文件逐一修改，不批量替换

- 每次只改一个逻辑单元（一个 role、一个 playbook、一个 section）
- 改完一个单元立即做自检（见下方"自检清单"）

---

## 三、修改后（提交前必做）

### 3. Diff 自检（每次提交前必须执行）

```bash
# 1. 查看所有改动的文件列表
git diff --stat HEAD

# 2. 逐文件检查 diff，重点核对：
#    - 是否有非预期的删除（红色 - 行）
#    - 是否有非预期的新增（绿色 + 行）
git diff HEAD -- <file>

# 3. 对于 README 等文档，额外检查：
#    - 章节是否完整（没有意外删掉某一 section）
#    - 表格行数是否合理（不应减少）
#    - 代码块是否配对（每个 ``` 都有对应的 ```）
git diff HEAD -- README.md | grep "^-" | grep -v "^---" | wc -l
git diff HEAD -- README.md | grep "^+" | grep -v "^+++" | wc -l
# 删除行数不应大幅超过新增行数，除非是有意重构
```

### 自检清单（针对常见遗漏）

| 检查项 | 命令 / 方法 |
|--------|------------|
| README 中无意删除的章节 | `git diff HEAD -- README.md \| grep "^-## "` |
| 性能建议等非功能章节是否保留 | `grep "性能\|Vault 工作流\|动态 Inventory" README.md` |
| 变量命名是否一致 | `grep -r "nginx_\b\|mysql_\b" roles/ --include="*.yml"` |
| 硬编码主机名是否残留 | `grep -r "lb01\.example\|example\.com" playbooks/ --include="*.yml"` |
| YAML 语法无误 | `python3 -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))" <file>` |
| 模板中无自定义 filter 隐式依赖 | `grep -r "\| env_badge\| to_nginx" roles/*/templates/` |

### 4. 检查非预期删除后的处置

- **发现非预期删除** → 立即还原，再提交
- **发现删除是必要的重构** → 在 commit message 中说明 `removed: <原因>`
- **不确定** → 默认还原，在 review 文档中提出讨论

---

## 四、提交规范

### Commit message 格式

```
<type>(<scope>): <简短描述>

[可选正文: 解释为什么，不是什么]

[可选尾注: 关联 review round / 已关闭问题]
```

**type 取值：**

| type | 含义 |
|------|------|
| `feat` | 新增功能或内容 |
| `fix` | 修复 bug 或错误 |
| `docs` | 仅文档变更 |
| `refactor` | 重构（不改变行为）|
| `review` | 响应 review 意见的修改 |
| `chore` | 工具链、配置、CI 变更 |
| `revert` | 还原误删内容 |

**示例：**

```bash
git commit -m "review(round-2): fix preflight to use Tier 1/2/3 platform model

Replace hard-coded Debian/Ubuntu check with OS family acceptance
and Tier-1 warning. Aligns with platform-support-addendum.

Closes: TODO-2 (Codex Round 2)"
```

### 何时提交

| 场景 | 策略 |
|------|------|
| 单个逻辑单元完成且自检通过 | 立即提交 |
| 一轮 review 修复全部完成 | 按 round 提交，message 带 round 编号 |
| 中途发现需要还原 | 先 `revert` commit，再重新修改 |
| 不确定是否改对 | 提交 `wip:` commit，继续验证后 squash |

---

## 五、Review 轮次提交流程

每完成一个完整的 review round（Codex 审查 + Claude 修复）：

```bash
# 1. 自检所有变更文件
git diff --stat HEAD

# 2. 逐文件 diff 检查（重点看删除行）
git diff HEAD

# 3. 确认 review 文档已更新
ls docs/reviews/

# 4. 分批提交（按逻辑分组）
git add roles/ && git commit -m "review(round-N): <角色修改描述>"
git add playbooks/ && git commit -m "review(round-N): <playbook 修改描述>"
git add docs/ && git commit -m "docs(round-N): add review and change log"
git add . && git commit -m "chore(round-N): update CI, EE, pre-commit"
```

---

## 六、AI 协作者的额外约束

当 AI（Claude / Codex）参与修改时：

1. **每次修改文件后，必须用 `git diff HEAD -- <file>` 验证实际改动**
2. **发现非预期删除，必须在提交前还原**
3. **不得以"已重构替代"为由跳过对有价值内容的还原**
4. **审查文档中的"已落地"结论，必须附有对应的 diff 证据**
5. **README 的每次重写，必须核对章节数量不减少**

```bash
# AI 修改 README 后的必检命令
git diff HEAD -- README.md | grep "^-## " | wc -l   # 应为 0
git diff HEAD -- README.md | grep "^+## " | wc -l   # 新增章节数
```

---

## 七、快速参考

```bash
# 改前快照
git status

# 改后验证
git diff --stat HEAD          # 文件级概览
git diff HEAD -- README.md    # README 专项检查
git diff HEAD -- README.md | grep "^-## "  # 被删章节

# 提交
git add <具体文件>
git commit -m "review(round-N): <描述>"

# 如发现误删，还原单个文件
git checkout HEAD -- <file>
```
