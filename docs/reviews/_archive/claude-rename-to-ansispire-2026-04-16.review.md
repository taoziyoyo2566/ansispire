# Rename Plan — `ansible-demo` → `Ansispire`

**Date**: 2026-04-16
**Author**: Claude (plan-only; execution handed off to another operator)
**Governance**: CLAUDE.md §2 (plan-first), §5 (non-round configuration-style artifact), R10 (suitability/conflict check), R11 (global refactor, not append)
**Pair with changelog**: `docs/reviews/claude-rename-to-ansispire-YYYY-MM-DD.changelog.md` (to be written **by the executor** after landing)

---

## 0. TL;DR for the executor

1. Close all running controller containers first (`make controller-audit-down && make controller-down`).
2. Edit 25 files (manifest in §5); one global find/replace is **not** sufficient — a few cases need semantic edits (see §5 callouts).
3. Rename the working directory from `ansible-demo` → `ansispire`.
4. Migrate three Docker named volumes (§6) — **this is the only destructive step**; skip it and the old data becomes orphan but nothing breaks.
5. Run smoke sequence (§8). All must pass before declaring done.
6. Write the paired changelog.

Estimated effort: **1.5–2.5 hours** (L2 tier, see §3).

---

## 1. Decision summary

**Chosen name**: `Ansispire` (portmanteau of *Ansible* + *spire*).

- Written as `Ansispire` in prose, `ansispire` in code/paths/identifiers.
- No hyphen anywhere. All lowercase in package/container/image/network names.

**Why this name** (recap for context):

- GitHub / PyPI / Docker Hub: no conflict found in the prior search session (2026-04-16).
- `.com` and `.io` were clean in that same search — **executor must re-verify the day they act**; the prior session documented aggressive recent squatting on adjacent names.
- Keeps the Ansible identity (important for discoverability — this remains a *reference Ansible control system*, not a generic orchestration product).
- `spire` metaphor matches the Stage 1 architectural posture: a single vertical control point (control plane over data plane).

**Level declaration** (CLAUDE.md §1.B): **Engineering** — it is a cross-cutting identifier/identity change with no behavioral or architectural shift. No NFR change. No new subsystem.

---

## 2. Scope boundaries

### In scope (L2 per §3 tier definition)

- Repo / working directory identity
- Python project metadata (`pyproject.toml`)
- Docker container names, image names, volume prefixes (via compose project)
- Semaphore's stored project record (one-time `ansible-demo` project name inside the SQLite DB)
- Makefile identifiers
- All runtime prose (README, controller README, RBAC doc)
- CLAUDE.md §8 positioning block (the name used in the prose)
- Inventory example comments referencing the old name

### Explicitly OUT of scope (do not expand)

- **No Ansible role/collection renames**. `roles/common`, `roles/webserver`, `roles/database` keep their names — they are technical role names, not project-identity names.
- **No inventory group renames**. `webservers`, `dbservers`, etc. stay.
- **No env-var prefix changes**. There is currently **no** `ANSIBLE_DEMO_*` env var in the repo (verified via grep); nothing to rename.
- **No Python module rename**. `pyproject.toml` declares a dependency list only — there is no `src/ansible_demo/` importable package. Renaming the `[project].name` is sufficient.
- **No Chinese snapshot rewriting**. `docs/reference-cn/snapshot-2026-04-14/` is a frozen historical snapshot; occurrences of `ansible-demo` inside it are intentional and MUST NOT be edited. A note about the rename belongs in a fresh snapshot if/when the next one is taken — not this round.
- **No historical `docs/reviews/` round docs rewritten**. Round 2/3/4/5/7/8/9 change logs and the codex review docs reference `ansible-demo` as an accurate statement of what the project was named *at that time*. They are immutable artifacts; do not touch them.
- **No git remote setup**. There is currently no remote (`git remote -v` empty). Adding one is a separate, explicitly authorized decision.
- **No `.claude/settings.local.json` edits**. Grepped — no `ansible-demo` string in it (permission globs are path-agnostic loopback patterns).

> If the executor encounters a file with `ansible-demo` that is NOT in §5's manifest, they must STOP and flag it, not improvise. The manifest was produced by exhaustive grep; an unlisted occurrence means either (a) it belongs to the explicit-exclusion list above, or (b) the file changed between this plan and execution, in which case the plan needs updating.

---

## 3. Scope tier

From the prior planning session (preserved verbatim as the decision frame):

| Tier | Contents | Cost | Risk |
|---|---|---|---|
| **L1 façade** | README titles, doc prose, CLAUDE.md §8 | small (<30min) | very low, trivially reversible |
| **L2 identifier** | + directory rename, Makefile `PROJECT_NAME`, Docker image/container/compose prefixes, Semaphore project name | medium (1–2 h) | low; breaks running containers and local image cache |
| **L3 contract** | + Python module rename, env-var prefix rename, persistence path rename, published artifact rename | large (multi-round) | high; involves data migration, compatibility shims, downstream consumers |

**This plan executes L2 end-to-end.** L3 is moot because there is no Python module, no `ANSIBLE_DEMO_*` env-var prefix, and no published artifact (verified via grep).

Rationale: Stage 2 is still early (no downstream users, no published artifacts), so doing L2 in one pass has better ROI than L1-now + L2-later.

---

## 4. Pre-flight (do this before any edit)

1. **Stop containers** — the rename changes container names; old containers will conflict unless torn down:
   ```bash
   make controller-audit-down
   make controller-down
   ```
   Verify no `ansible-demo-*` containers remain:
   ```bash
   docker ps -a --filter 'name=ansible-demo' --format '{{.Names}}'
   ```
   Expect: empty output.

2. **Snapshot current volumes** (safety, cheap):
   ```bash
   docker volume ls --filter 'name=ansible-demo' --format '{{.Name}}' > /tmp/ansible-demo-volumes-before.txt
   ```
   Keep this file for reference during §6 (volume migration) and §10 (rollback).

3. **Verify git is clean or state is intentional**:
   ```bash
   git status --short
   ```
   The executor should either commit pending work first, or accept that the rename commit will include whatever is currently staged. Recommend committing pending work first so the rename diff is reviewable in isolation.

4. **Verify no git remote is configured** (if one has been added since this plan was written, pause and re-check §2 out-of-scope list):
   ```bash
   git remote -v
   ```
   Expected: empty.

5. **Re-verify naming availability** (the prior search was 2026-04-16; if execution is later, re-run):
   - GitHub: `gh search repos ansispire --limit 5` (or browser)
   - npm / PyPI / Docker Hub: quick browser check
   - Domains `ansispire.com` / `ansispire.io`: whois

---

## 5. File change manifest (25 files)

**Legend**:
- **Kind** = `s/old/new/` (pure substitution safe) or `semantic` (requires judgment — do not blindly s///)
- All substitutions are **literal**: `ansible-demo` → `ansispire`, `ansible_demo` → `ansispire` (no underscores in this name, so both map to the same word). Uppercase `ANSIBLE_DEMO` has no occurrences (verified).

### 5.1 Code / config (authoritative; behavior depends on these)

| # | File | Kind | Change detail |
|---|---|---|---|
| 1 | `pyproject.toml` | **semantic** | Line 14: `name = "ansible-demo"` → `name = "ansispire"`. Line 16 description — also rewrite to reflect new positioning: `"Ansispire — an Ansible-based reference multi-server management control system"`. Lines 54 and 60 (self-reference inside extras): `"ansible-demo[test,cloud,dev]"` → `"ansispire[test,cloud,dev]"`, `"ansible-demo[all]"` → `"ansispire[all]"`. Per R11, while editing this file, verify `[build-system] build-backend` value `"hatchling.backends"` — this looks suspicious (the standard is `hatchling.build`) but **do not fix it in this rename**; file a separate note if it turns out broken. |
| 2 | `Makefile` | s/// | Line 28: `AUDIT_CONTAINER := ansible-demo-audit-sink` → `AUDIT_CONTAINER := ansispire-audit-sink`. Line 87: build tag `ansible-demo-ee:latest` → `ansispire-ee:latest`. |
| 3 | `.ansible-navigator.yml` | s/// | Line 17: `image: ansible-demo-ee:latest` → `image: ansispire-ee:latest`. |
| 4 | `execution-environment.yml` | s/// | Lines 5–6 comment block: both `ansible-demo-ee:latest` → `ansispire-ee:latest`. |
| 5 | `controller/semaphore/docker-compose.yml` | s/// | Line 14: `container_name: ansible-demo-semaphore` → `container_name: ansispire-semaphore`. |
| 6 | `controller/audit/docker-compose.yml` | s/// | Lines 24 & 63: two `container_name:` values — `ansible-demo-audit-sink` → `ansispire-audit-sink`, `ansible-demo-audit-relay` → `ansispire-audit-relay`. |
| 7 | `controller/semaphore/bootstrap.yml` | **semantic** | Line 22 play name and line 31 `project_name: "ansible-demo"` — both to `ansispire`. **Important**: this changes the name the bootstrap playbook *creates inside Semaphore*. If a Semaphore container is running with the old `ansible-demo` project already present, re-running bootstrap will create a *second* project called `ansispire` — the old one must be removed manually (§7) or a fresh DB accepted. |
| 8 | `controller/audit/loop-smoke.sh` | s/// | Line 20 default `SINK_CONTAINER` value; line 82 log hint. Both `ansible-demo-audit-*` → `ansispire-audit-*`. |
| 9 | `controller/rbac/smoke.sh` | **semantic** | Lines 110, 113, 122: comments and the Python one-liner that greps Semaphore's project list for name `'ansible-demo'`. Change the string literal to `'ansispire'` **and** the comments. |

### 5.2 Runtime prose (user-facing docs — keep wording idiomatic)

| # | File | Kind | Change detail |
|---|---|---|---|
| 10 | `README.md` | **semantic** | Line 1 H1 title `# Ansible Complete Reference Project` → `# Ansispire — Ansible-based Reference Control System` (or operator's preferred phrasing). Line 47 ASCII tree: `ansible-demo/` → `ansispire/`. Line 3 opening paragraph — review for dated phrasing while editing (R11). |
| 11 | `controller/semaphore/README.md` | s/// | Line 57 "Project: `ansible-demo`" → `ansispire`. Lines 91 & 97: Docker volume name in backup/restore commands `ansible-demo_semaphore-data` → `ansispire_semaphore-data`. |
| 12 | `controller/rbac/README.md` | s/// | Line 130 reference inside a table. |
| 13 | `controller/rbac/role-matrix.md` | s/// | Lines 45 and 60. |

### 5.3 Commented-example files (technically config, practically docs)

| # | File | Kind | Change detail |
|---|---|---|---|
| 14 | `inventory/production/group_vars/all/secrets_external.example.yml` | s/// | 7 occurrences, all in commented examples of HashiCorp Vault / AWS SM / Azure KV lookup paths. Rename consistently; these are illustrative, not live. |

### 5.4 Governance (CLAUDE.md and memory-adjacent)

| # | File | Kind | Change detail |
|---|---|---|---|
| 15 | `CLAUDE.md` | **semantic** | §8 "Project Background" — update the sentence that currently reads "An Ansible-based multi-server management control system — not a generic development template" to lead with the project name: "Ansispire is an Ansible-based multi-server management control system — …". Do NOT rewrite other sections; per R11, a *global* review is still warranted — specifically, check whether any §7 rule source-attribution references the old name (none should, but verify). |

### 5.5 Historical / frozen artifacts — DO NOT EDIT

These are listed here **only** so the executor can cross-check them against their grep results and confirm "yes, this match is intentionally left":

| File | Why skipped |
|---|---|
| `docs/reviews/stage-1-closeout-2026-04-15.md` | Immutable retrospective; references the name in force at the time. |
| `docs/reviews/claude-review-round-9-2026-04-15.md` | Same — Round 9 plan doc. |
| `docs/reviews/round-8-change-log-2026-04-15.md` | Same. |
| `docs/reviews/round-7-change-log-2026-04-14.md` | Same. |
| `docs/reviews/codex-review-round-{2,3,4}-2026-04-09.md` | External reviewer's historical reports; do not mutate. |
| `docs/reviews/claude-review-2026-04-09.md` | Same. |
| `docs/reference-cn/snapshot-2026-04-14/**/*.zh.md` (all three matches) | Explicitly a time-stamped snapshot; identity change belongs in a future snapshot, not a retroactive edit. |

If the executor greps for `ansible-demo` after finishing and finds only matches in this table, the file-edit phase is correctly complete.

---

## 6. Docker volume migration (the only destructive step)

Docker Compose prefixes volumes with its project name, which defaults to the parent directory. Renaming `ansible-demo/` → `ansispire/` means new runs will create *new* volumes under the `ansispire_*` prefix and **ignore** the old `ansible-demo_*` volumes — your Semaphore DB, config, tmp, audit logs and relay cursor will all appear empty on first restart.

**Three volumes to consider:**

```
ansible-demo_semaphore-data     # Semaphore SQLite DB (users, projects, credentials)
ansible-demo_semaphore-config   # Semaphore config files
ansible-demo_semaphore-tmp      # ephemeral — can be abandoned
ansible-demo_audit-data         # audit JSONL log history
ansible-demo_audit-relay-state  # relay cursor (so relay doesn't re-forward old events)
```

### Option A — Preserve state (recommended for live demos)

Copy each old volume's contents into a new volume, then remove the old one. Run **one volume at a time**:

```bash
OLD=ansible-demo_semaphore-data
NEW=ansispire_semaphore-data
docker volume create "$NEW"
docker run --rm \
  -v "$OLD:/from:ro" -v "$NEW:/to" \
  alpine sh -c 'cd /from && tar cf - . | (cd /to && tar xf -)'
# only after verifying the new volume (see verification snippet below):
# docker volume rm "$OLD"
```

Verification between copy and removal:
```bash
docker run --rm -v "$NEW:/v" alpine ls -la /v   # expect the same files as OLD
```

Repeat for `semaphore-config`, `audit-data`, `audit-relay-state`. Skip `semaphore-tmp` — it's ephemeral.

### Option B — Accept fresh state (acceptable since Stage 1 is reproducible)

Skip the copy step. Run `make controller-bootstrap` after `make controller-up` to recreate the Semaphore project/inventory/template/users from scratch. Audit log history is lost; relay re-forwards from the start (one-time duplication). This is cleaner and matches how a brand-new operator would experience the repo.

**Default recommendation**: Option B if no one has valuable audit history; Option A otherwise.

After rename, the old `ansible-demo_*` volumes can be listed with `docker volume ls --filter name=ansible-demo` and removed **only after the new stack is verified healthy** (§8). This reclaim is destructive — hold until smokes pass.

---

## 7. Semaphore internal state (one edge case)

If Option A above is used (preserving state), the Semaphore DB still contains a project record literally named `ansible-demo`. Running the edited `bootstrap.yml` (file #7) will add a *second* project named `ansispire`, not rename the first.

Two ways to handle, pick one:

1. **Rename inside Semaphore UI** (manual, 30 seconds): log in, open project `ansible-demo`, rename to `ansispire`, save. Done.
2. **Delete + re-bootstrap** (idempotent): in the UI, delete the `ansible-demo` project; re-run `make controller-bootstrap` to create `ansispire` fresh.

If Option B was used at §6, this question doesn't arise — bootstrap creates the `ansispire` project against an empty DB.

---

## 8. Smoke sequence (mandatory post-rename)

Run in order; stop and roll back on first failure.

```bash
# 0. From the *new* directory (after §9)
cd /home/netcup/workspace/ansispire

# 1. Build image with new tag (only if EE is actually used)
# make ee-build         # optional — depends on whether the EE image is rebuilt this round

# 2. Bring the control plane up
make controller-net        # idempotent
make controller-up         # Semaphore on :3001 (or whatever SEMAPHORE_PORT is set to)

# Expect container named ansispire-semaphore, healthy within ~30s
docker ps --filter name=ansispire-semaphore --format '{{.Names}} {{.Status}}'

# 3. Bring the audit stack up
make controller-audit-up

# Expect two new containers
docker ps --filter name=ansispire-audit --format '{{.Names}} {{.Status}}'

# 4. Bootstrap (§7 handled as chosen)
make controller-bootstrap

# 5. RBAC smoke
make controller-rbac-smoke   # expect 6/6 PASS

# 6. End-to-end audit loop smoke
make controller-loop-smoke   # expect ALL GREEN; 1–2 s latency

# 7. Final grep — confirm no unexpected ansible-demo residue in authoritative files
git grep -nE 'ansible-demo|ansible_demo|ANSIBLE_DEMO' \
    -- ':!docs/reviews/*change-log*' \
       ':!docs/reviews/stage-1-closeout-*' \
       ':!docs/reviews/round-*' \
       ':!docs/reviews/codex-review-*' \
       ':!docs/reviews/claude-review-2026-04-09.md' \
       ':!docs/reference-cn/**'
# Expect: empty output.
```

All six smokes pass → rename is **done**. One smoke fails → go to §10 rollback.

---

## 9. Working-directory rename

Strict order:

1. Confirm `pwd` returns `/home/netcup/workspace/ansible-demo`.
2. Confirm all containers are down (§4 step 1).
3. Move up one level and rename:
   ```bash
   cd /home/netcup/workspace
   mv ansible-demo ansispire
   cd ansispire
   ```
4. Update any shell aliases, tmux session names, IDE bookmarks, or shell history references the operator personally cares about. **Not** in scope for this plan — operator's own environment.
5. Re-open the terminal / re-activate any venv / reload any direnv file at the new path.

**Note on CLAUDE.md memory path**: the Claude memory system stores files at `/home/netcup/.claude/projects/-home-netcup-workspace-ansible-demo/`. This is *Claude's* internal path, not a code dependency. It will keep working after the directory rename (Claude re-derives the path from the new cwd on the next session) but memory will effectively "reset" for future sessions under the new path unless the operator also renames `.claude/projects/-home-netcup-workspace-ansible-demo/` → `.claude/projects/-home-netcup-workspace-ansispire/`. Recommend doing the rename to preserve continuity. **Out of scope for the code executor** — this is a Claude-tooling concern, flag to the user.

---

## 10. Rollback plan

Because almost every change is a text edit with no data mutation, rollback is cheap up until step §6 (volume migration) is irreversible:

1. **Pre-volume-migration failure**: `git reset --hard HEAD` + `mv ansispire ansible-demo` → back to starting state. Containers can be brought back with `make controller-up && make controller-audit-up` (they read the original `container_name`).
2. **Post-volume-migration failure (Option A)**: the old `ansible-demo_*` volumes still exist (do NOT run `docker volume rm` until smokes pass). Stop the `ansispire-*` containers, revert the repo, restart the `ansible-demo-*` stack — original volumes untouched. Optionally delete the copy volumes.
3. **Post-`docker volume rm` failure (Option A, old volumes deleted)**: no rollback; any data loss is final. This is why §6 emphasizes deleting old volumes only after smokes pass.
4. **Post-smokes-pass failure discovered later**: treat as a bug on the new codebase; fix forward. Do not unwind the rename.

---

## 11. Changelog contract for the executor

Per CLAUDE.md §2.B, the executor MUST produce a paired changelog at:

```
docs/reviews/claude-rename-to-ansispire-YYYY-MM-DD.changelog.md
```

Required contents:
- `Reference:` link back to this review doc.
- File manifest (actual files touched, matching §5 or explaining deviations).
- Confirmation that each of the 6 smokes in §8 passed, with timestamps.
- Which §6 option (A or B) was chosen, and why.
- Which §7 approach was used, if §6 Option A.
- Any deviations from this plan (unexpected files, additional edits, skipped edits). **Deviations are allowed but must be explicit.**
- A "Not done (explicit boundaries)" section mirroring §2 of this plan.
- Follow-up / Next Steps section for the user.

---

## 12. Self-check (for this plan doc, before handoff)

- [x] Full file manifest enumerated via grep, not memory (25 files / 58 occurrences).
- [x] Each "semantic" entry explains *why* a blind s/// is unsafe.
- [x] Destructive step isolated (§6), with both safe-preserve and accept-fresh options.
- [x] Historical/frozen artifacts enumerated so executor knows what to skip.
- [x] Pre-flight captures container-shutdown ordering (new name conflicts with old).
- [x] Rollback plan distinguishes reversible / partial / irreversible phases.
- [x] CLAUDE.md §8 change is called out; other rules left intact.
- [x] R11 applied: `pyproject.toml` description also updated; CLAUDE.md §8 rewritten not just patched; suspicious `hatchling.backends` flagged for a *future* fix (not expanded into this round).
- [x] Claude's own memory-path rename is flagged as out-of-scope + reported to the user (§9 note).

---

## 13. Follow-up / Next steps

### Immediately doable (User or delegated executor)
1. Re-verify naming availability on execution day (§4.5). If a conflict has emerged, pause and return to the shortlist.
2. Execute §4 → §5 → §6 → §7 → §8 in order. One sitting is ideal (≈2 hours).
3. Write the paired changelog (§11).

### Blocked / decision-pending (User)
4. Decide §6 Option A vs B **before** execution — this is a data-preservation judgment the operator shouldn't make solo.
5. Decide whether to rename the Claude memory directory (§9 note) to preserve continuity.

### Deferrable (not this round)
6. Add a git remote and push (only when ready to make the rename public).
7. Re-build and re-tag the EE image (`ansispire-ee:latest`) if/when EE is actually in the daily loop.
8. Take a fresh Chinese snapshot reflecting the new name — do this when the *next* snapshot is naturally due, not reactively now.
9. Investigate `pyproject.toml` `[build-system].build-backend = "hatchling.backends"` — suspected wrong value (standard is `hatchling.build`); file separately.
