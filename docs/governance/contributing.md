# Contribution and iteration workflow

This document defines the **quality-assurance workflow** that every change to
this repository must follow. Everyone (including AI collaborators) must apply
this workflow to every change.

---

## 1. Before editing

Edit authority is defined in
[`../../.agents/rules/authorization.md`](../../.agents/rules/authorization.md).
A user change/fix/implementation request authorizes its necessary in-scope
workspace edits and normal verification; do not request confirmation per file.
Review-only work remains read-only.

### 1.1 Define the scope of the change

Before starting, you must be able to answer:

- What is being changed? (file list)
- Why? (source: review / bug / requirement)
- What is explicitly NOT being changed? (boundary)

### 1.2 Record the current baseline

```bash
# Confirm the current working tree state
git status --short --branch
git stash list  # confirm no unresolved stashes
```

If there are uncommitted changes:

- identify which changes belong to the current task and which are unrelated;
- preserve and work around unrelated or unrecognized changes;
- do not commit, stash, switch branches, restore files, or stage a broad path
  merely to make the tree clean;
- if safe separation requires a Git mutation, follow
  `../../.agents/rules/authorization.md` and `../../.agents/rules/git.md`;
  commit requests also require `../../.agents/rules/commits.md`.

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

- **Deletion introduced by the current edit is unintended** → reverse only that
  known edit, then re-check the diff
- **Deletion is a deliberate refactor** → note `removed: <reason>` in the commit message
- **Deletion predates the task or ownership is unclear** → preserve it and raise
  it in the review; do not restore or overwrite it
- `git checkout -- <path>` and `git restore <path>` require the exact approval
  defined in `../../.agents/rules/git.md`

---

## 4. Commit conventions

### Commit message format

```
<type>(<scope>): <short description>

[optional body: explain why, not what]

[optional footer: reference review round / closed issues]
```

Valid type values and identity requirements are defined once in
`../../.agents/rules/commits.md`.

**Example:**

```bash
git commit -m "fix(preflight): use Tier 1/2/3 platform model

Replace hard-coded Debian/Ubuntu check with OS family acceptance
and Tier-1 warning. Aligns with platform-support-addendum."
```

### When to commit

| Situation | Strategy |
|-----------|----------|
| A logical unit is done and self-check passes | Report it as ready; do not stage or commit |
| The user directly requests commit preparation | Propose exact paths, stage only those paths, run gates, and present the commit manifest |
| The user approves the exact post-preparation manifest | Re-check it is unchanged, then create one commit |
| A full review round of fixes is done | Propose a scoped checkpoint and exact paths; a proposal is not authorization |
| Need to revert or restore existing work | Stop and obtain the exact authorization required by `../../.agents/rules/git.md` |
| Not sure the change is correct | Keep it uncommitted and report the uncertainty; do not create an unsolicited WIP commit |

---

## 5. Review-round commit flow

After completing a full review round, a direct commit-preparation request may
start this flow. It does not authorize the final commit:

```bash
# 1. Self-check all changed files
git diff --stat HEAD

# 2. Review per-file diffs (watch deletions)
git diff HEAD

# 3. Inspect the current topic in both roots
# New/migrated topics use docs/workstreams/; unmigrated topics remain whole
# under docs/reviews/. Output for one topic must come from one root only.
topic="<kind>-<topic>"
for root in docs/workstreams docs/reviews; do
  [ ! -d "$root/$topic" ] || find "$root/$topic" -type f -print
done

# 4. Stage only the exact reviewed paths and commit logical units
git add <specific-reviewed-paths>

# 5. Run staged checks and present the exact manifest and full message.
# Stop and wait for the user's later confirmation of that manifest.

# 6. Re-check that the manifest is unchanged, then create exactly one commit.
git commit -m "<type>(<scope>): <description>"

# Never use git add . or git add -A to collect a mixed working tree.
```

---

## 6. Extra constraints for AI collaborators

When an AI (Claude / Codex) participates in a change:

1. **After editing a file, you must verify the actual change with `git diff HEAD -- <file>`**
2. **If the current edit caused an unintended deletion, reverse only that known
   edit before committing; preserve unrelated or unrecognized deletions**
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
git status --short --branch

# Verify after editing
git diff --stat HEAD          # file-level overview
git diff HEAD -- README.md    # README-specific check
git diff HEAD -- README.md | grep "^-## "  # deleted sections

# An initial request permits preparation only. Commit after the exact staged
# manifest is shown and the user confirms it in a later message.
git add <specific-reviewed-paths>
git commit -m "<type>(<scope>): <description>"

# If an accidental deletion came from the current edit, reverse only that edit.
# git checkout/restore of an existing path requires explicit approval.
```
