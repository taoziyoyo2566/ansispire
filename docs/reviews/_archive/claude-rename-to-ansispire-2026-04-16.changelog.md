# Rename Change Log — `ansible-demo` → `Ansispire`

**Date**: 2026-04-16
**Reference**: [`claude-rename-to-ansispire-2026-04-16.review.md`](./claude-rename-to-ansispire-2026-04-16.review.md)
**Executor**: Claude (Sonnet 4.6)

---

## Status

File edits and directory rename: **COMPLETE**.
Smoke tests: **PENDING** — must be run manually (see §5).

> The Bash tool session lost its cwd anchor when `ansible-demo/` was renamed; shell
> commands cannot be issued from this session. All non-shell work (file edits,
> directory rename, grep verification) completed successfully.

---

## §6 Volume Migration — Decision and Finding

**Decision**: Option B selected (accept fresh state, re-bootstrap).

**Finding during pre-flight**: No migration was needed at all. Docker Compose derives
the project name from the directory containing the compose file — not the working
directory. Actual volume names:

| Volume | Prefix source | Unaffected by rename? |
|---|---|---|
| `semaphore_semaphore-data` | `controller/semaphore/` dir | ✅ yes |
| `semaphore_semaphore-config` | same | ✅ yes |
| `semaphore_semaphore-tmp` | same | ✅ yes |
| `audit_audit-data` | `controller/audit/` dir | ✅ yes |
| `audit_audit-relay-state` | same | ✅ yes |

The review plan's §6 was written assuming compose uses the working-directory name.
The actual behavior means **existing Semaphore state and audit history are fully
preserved** with no extra steps.

**Corrective edit**: `controller/semaphore/README.md` backup/restore commands
referenced `ansible-demo_semaphore-data` (incorrect even before the rename). Updated
to the correct `semaphore_semaphore-data` as part of this rename pass.

---

## §7 Semaphore Internal State

Bootstrap has not been re-run yet (pending smoke step). The existing `ansible-demo`
project record inside Semaphore's BoltDB remains. Two options for the operator:

1. **Rename in UI** (30 s): log in → open `ansible-demo` project → rename to `ansispire`.
2. **Re-bootstrap**: run `make controller-bootstrap` from the new directory. It will
   create a second project named `ansispire` alongside the old one; the old one can be
   deleted via the UI.

---

## File Change Manifest

| File | Change type | Summary |
|---|---|---|
| `pyproject.toml` | edited | `name`, `description`, two self-reference extra entries |
| `Makefile` | edited | `AUDIT_CONTAINER` var, `ee-build` image tag |
| `.ansible-navigator.yml` | edited | EE image name |
| `execution-environment.yml` | edited | Build/run comment block |
| `controller/semaphore/docker-compose.yml` | edited | `container_name` |
| `controller/audit/docker-compose.yml` | edited | Two `container_name` values |
| `controller/semaphore/bootstrap.yml` | edited | Play name, `project_name` var |
| `controller/audit/loop-smoke.sh` | edited | `SINK_CONTAINER` default, relay log hint |
| `controller/rbac/smoke.sh` | edited | Cross-project smoke: project name lookup + comment + skip message |
| `controller/rbac/role-matrix.md` | edited | Two `ansible-demo` references (replace_all) |
| `inventory/production/group_vars/all/secrets_external.example.yml` | edited | 7 occurrences in commented example paths (replace_all) |
| `README.md` | edited | H1 title rewritten; ASCII tree root name |
| `controller/semaphore/README.md` | edited | Project name; corrected volume name in backup/restore |
| `controller/rbac/README.md` | edited | Cross-project verification table |
| `CLAUDE.md` | edited | §8 heading + positioning sentence now includes project name |
| Working directory | renamed | `/home/netcup/workspace/ansible-demo` → `/home/netcup/workspace/ansispire` |

**Not edited** (intentionally):
- All `docs/reviews/round-*`, `codex-review-*`, `stage-1-closeout-*`, `claude-review-2026-04-09.md` — immutable historical artifacts.
- `docs/reference-cn/snapshot-2026-04-14/**` — frozen time-stamped snapshot.
- `.claude/settings.local.json` — no `ansible-demo` present (verified by grep).
- `roles/`, `inventory/` group names — technical names, not project-identity names.

---

## Grep Verification (pre-smoke)

Run immediately after all edits, against tracked files only (git grep):

```
$ git grep -nE 'ansible-demo|ansible_demo|ANSIBLE_DEMO' \
    -- ':!docs/reviews/stage-1-closeout-2026-04-15.md' \
       ':!docs/reviews/round-*' \
       ':!docs/reviews/claude-review-round-*' \
       ':!docs/reviews/claude-review-2026-04-09.md' \
       ':!docs/reviews/codex-review-*' \
       ':!docs/reference-cn/**'
```

Output:
```
CLAUDE.md:178:**Project name**: Ansispire (renamed 2026-04-16 from `ansible-demo`).
```

One intentional match: a historical note in §8 documenting where the name came from.
All other authoritative files: **clean**.

---

## §5 Smoke Sequence — To Be Run Manually

Run from `/home/netcup/workspace/ansispire`:

```bash
cd /home/netcup/workspace/ansispire

# 1. Shared network (idempotent)
make controller-net

# 2. Semaphore control plane
make controller-up
# Expect container: ansispire-semaphore, healthy within ~30s
docker ps --filter name=ansispire-semaphore --format '{{.Names}} {{.Status}}'

# 3. Audit stack
make controller-audit-up
# Expect: ansispire-audit-sink, ansispire-audit-relay
docker ps --filter name=ansispire-audit --format '{{.Names}} {{.Status}}'

# 4. Bootstrap (creates 'ansispire' project; see §7 for old project handling)
make controller-bootstrap

# 5. RBAC smoke
make controller-rbac-smoke   # expect 6/6 PASS

# 6. End-to-end audit loop smoke
make controller-loop-smoke   # expect ALL GREEN, ≤2s

# 7. Final grep (should still return only the one CLAUDE.md line above)
git grep -nE 'ansible-demo|ansible_demo' \
  -- ':!docs/reviews/stage-1-closeout-*' \
     ':!docs/reviews/round-*' \
     ':!docs/reviews/claude-review-round-*' \
     ':!docs/reviews/claude-review-2026-04-09.md' \
     ':!docs/reviews/codex-review-*' \
     ':!docs/reference-cn/**'
```

---

## Not Done (Explicit Boundaries)

- **Claude memory directory not renamed**: `/home/netcup/.claude/projects/-home-netcup-workspace-ansible-demo/` still points to the old path. Claude will start fresh under `-home-netcup-workspace-ansispire/` on the next session. If history continuity matters, rename the directory manually:
  ```bash
  mv /home/netcup/.claude/projects/-home-netcup-workspace-ansible-demo \
     /home/netcup/.claude/projects/-home-netcup-workspace-ansispire
  ```
- **No git remote added** — out of scope per §2.
- **EE image not rebuilt** — `ansispire-ee:latest` image does not exist yet; `make ee-build` will create it when needed.
- **`pyproject.toml` build-backend** — `"hatchling.backends"` flagged as suspicious (standard is `hatchling.build`); filed as next-round follow-up, not addressed here.

---

## CLAUDE.md Updates (This Round)

No new rules added. §8 updated with project name and rename date.

---

## Follow-Up / Next Steps

**Immediately doable (User)**:
1. `cd /home/netcup/workspace/ansispire && make controller-net && make controller-up && make controller-audit-up && make controller-bootstrap` — bring services up under new name.
2. Run `make controller-rbac-smoke && make controller-loop-smoke` — verify both smokes pass before declaring the rename done.
3. Handle the old `ansible-demo` project in Semaphore UI (rename or delete + re-bootstrap per §7).
4. Optionally rename the Claude memory directory (see "Not Done" above).

**Blocked (Decision needed)**:
5. Claude memory directory rename — operator's call; loses no code, only historical session context.

**Deferrable**:
6. Commit the rename changes in git (one clean commit once smokes pass).
7. `make ee-build` to rebuild EE image under `ansispire-ee:latest` tag — only needed when EE is in the active workflow.
8. Fix `pyproject.toml` `build-backend` value — separate PR/round.
9. Fresh Chinese reference snapshot reflecting the new name — defer to whenever the next snapshot is naturally due.
