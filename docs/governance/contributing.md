# Contribution and iteration workflow

This document defines the **quality-assurance workflow** that every change to
this repository must follow. Everyone (including AI collaborators) must apply
this workflow to every change.

---

## 1. Before editing

### 1.1 Define the scope of the change

Before starting, you must be able to answer:

- What is being changed? (file list)
- Why? (source: review / bug / requirement)
- What is explicitly NOT being changed? (boundary)

### 1.2 Record the current baseline

```bash
# Confirm the current working tree state
git status
git stash list  # confirm no unresolved stashes

# If there are uncommitted changes, commit or stash first
git add -A && git commit -m "wip: checkpoint before <task name>"
```

---

## 2. While editing

### One logical unit at a time — no batch replacements

- Change one logical unit at a time (one role, one playbook, one section)
- Self-check the moment a unit is done (see the "self-check list" below)

---

## 3. After editing (mandatory before committing)

### 3.1 Diff self-check (required before every commit)

```bash
# 1. List every modified file
git diff --stat HEAD

# 2. Review the diff file by file, paying attention to:
#    - Unintended deletions (red "-" lines)
#    - Unintended additions (green "+" lines)
git diff HEAD -- <file>

# 3. For READMEs and other docs, additionally check:
#    - All sections are intact (no section silently removed)
#    - Table row counts look right (should not decrease)
#    - Code blocks are balanced (every ``` has a matching ```)
git diff HEAD -- README.md | grep "^-" | grep -v "^---" | wc -l
git diff HEAD -- README.md | grep "^+" | grep -v "^+++" | wc -l
# Deletions should not vastly exceed additions unless it's a deliberate refactor.
```

### Self-check list (common pitfalls)

| Check | Command / method |
|-------|------------------|
| No README sections silently removed | `git diff HEAD -- README.md \| grep "^-## "` |
| Non-functional sections (e.g. performance tips) still present | `grep "Performance\|Vault workflow\|Dynamic inventory" README.md` |
| Variable naming stays consistent | `grep -r "nginx_\b\|mysql_\b" roles/ --include="*.yml"` |
| No hard-coded hostnames left behind | `grep -r "lb01\.example\|example\.com" playbooks/ --include="*.yml"` |
| YAML parses cleanly | `python3 -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))" <file>` |
| Templates don't silently depend on a custom filter | `grep -r "\| env_badge\| to_nginx" roles/*/templates/` |

### 3.2 Handling unintended deletions

- **Unintended deletion found** → restore immediately, then commit
- **Deletion is a deliberate refactor** → note `removed: <reason>` in the commit message
- **Unsure** → default to restoring, and raise it in the review document

---

## 4. Commit conventions

### Commit message format

```
<type>(<scope>): <short description>

[optional body: explain why, not what]

[optional footer: reference review round / closed issues]
```

**Valid type values:**

| type | Meaning |
|------|---------|
| `feat` | New feature or content |
| `fix` | Bug fix |
| `docs` | Docs-only change |
| `refactor` | Refactor (no behavior change) |
| `review` | Change responding to review feedback |
| `chore` | Tooling, configuration, or CI change |
| `revert` | Restore accidentally removed content |

**Example:**

```bash
git commit -m "review(round-2): fix preflight to use Tier 1/2/3 platform model

Replace hard-coded Debian/Ubuntu check with OS family acceptance
and Tier-1 warning. Aligns with platform-support-addendum.

Closes: TODO-2 (Codex Round 2)"
```

### When to commit

| Situation | Strategy |
|-----------|----------|
| A logical unit is done and self-check passes | Commit immediately |
| A full review round of fixes is done | Commit per round; include the round number in the message |
| Need to revert mid-stream | `revert` the commit first, then redo the change |
| Not sure the change is correct | Commit a `wip:` commit; squash after verification |

---

## 5. Review-round commit flow

After completing a full review round (Codex review + Claude fixes):

```bash
# 1. Self-check all changed files
git diff --stat HEAD

# 2. Review per-file diffs (watch deletions)
git diff HEAD

# 3. Confirm the review document has been updated
ls docs/reviews/

# 4. Commit in logical batches
git add roles/ && git commit -m "review(round-N): <role changes>"
git add playbooks/ && git commit -m "review(round-N): <playbook changes>"
git add docs/ && git commit -m "docs(round-N): add review and change log"
git add . && git commit -m "chore(round-N): update CI, EE, pre-commit"
```

---

## 6. Extra constraints for AI collaborators

When an AI (Claude / Codex) participates in a change:

1. **After editing a file, you must verify the actual change with `git diff HEAD -- <file>`**
2. **If an unintended deletion is found, it must be restored before committing**
3. **"Replaced by refactor" is not a valid reason to skip restoring valuable content**
4. **Any "already landed" claim in a review document must be backed by a concrete diff**
5. **Every README rewrite must preserve the section count (sections must not decrease)**

```bash
# Required checks after an AI edits the README
git diff HEAD -- README.md | grep "^-## " | wc -l   # should be 0
git diff HEAD -- README.md | grep "^+## " | wc -l   # number of newly added sections
```

---

## 7. Quick reference

```bash
# Snapshot before editing
git status

# Verify after editing
git diff --stat HEAD          # file-level overview
git diff HEAD -- README.md    # README-specific check
git diff HEAD -- README.md | grep "^-## "  # deleted sections

# Commit
git add <specific files>
git commit -m "review(round-N): <description>"

# If an accidental deletion is found, restore a single file
git checkout HEAD -- <file>
```
