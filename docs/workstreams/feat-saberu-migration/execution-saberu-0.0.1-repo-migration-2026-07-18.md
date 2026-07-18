> **Status**: APPROVED
> **Approved**: 2026-07-18 — with the three §3 open decisions resolved to their defaults (private; host global gitconfig identity; LICENSE untouched unless it names the old account)
> **Updated**: 2026-07-18 — user amendment at approval: the new repo's `master` (and `dev`) accept no direct content commits; the import lands on a feature branch and reaches `dev`/`master` via PR (Phase 4 rewritten accordingly)
> **Created**: 2026-07-18
> **Branch**: feat/saberu-migration
> **Classification**: [L2] Architecture
> **Plan type**: Execution plan
> **Approval scope**: implementation approach
> **Blocks implementation**: yes
> **Does not supersede**: `docs/reviews/feat-product-redesign/plan-saberu-new-project-2026-06-23.md` §"thin layer" design content — only its "do not copy the old repository" premise is overridden by the user decision of 2026-07-18

# Execution — Migrate ansispire working tree to saberu-ops/saberu as v0.0.1

## §1 Why this plan exists

1. **What is missing**: the project is hosted under the personal
   `taoziyoyo2566` account; the confirmed product identity is **Saberu** and a
   `saberu-ops` GitHub account already holds credentials on this host, but no
   repository exists there.
2. **Why it matters**: continuing development under the old account deepens the
   split between product identity and hosting; 272 commits of exploratory
   history are noise for the new project baseline.
3. **Trigger**: user decision on 2026-07-18 — migrate the current working tree
   (not any single committed branch) to `saberu-ops/saberu`, pruned, as a
   single `v0.0.1` initial commit with no prior history.

Best-practice pre-check (workspace W-R18): history-preserving migrations would
use mirror-push or `git filter-repo`; the user explicitly wants history
dropped, for which the standard approach is exactly what this plan does —
commit-then-`git archive` export into a fresh `git init`. No framework-native
alternative applies. Sources: git-scm docs for `git archive` / `init`;
`gh repo create` for repo provisioning (both routine, no open research items).

## §2 Current state (confirmed by in-session probes, 2026-07-18)

- `origin` = `https://github.com/taoziyoyo2566/ansispire.git`; `gh` is logged
  in to both `taoziyoyo2566` (active) and `saberu-ops` (inactive).
- Branch topology: `master` (2026-04-26) ← `dev` (+96) ←
  `feat/target-architecture` (+51) ← current `feat/vps-software-catalog` (+2).
  `feat/vps-profile-catalog` and `feat/governance-artifact-routing` are checked
  out in `/tmp` worktrees.
- **The consolidated latest state is the uncommitted working tree** on
  `feat/vps-software-catalog`: 31 changed files (+731/−1020) that fold in the
  governance-rules refactor and the profile-catalog workstream migration,
  newer than either committed branch.
- No tracked secrets (`git ls-files` sweep clean; `.vault_pass`, `.venv`
  gitignored). Repo pack is 2.24 MiB.
- `plugins/vps_manager` was already removed on this line (legacy cutover
  commit `bce0f75`); only `plugins/AGENTS.md` remains.
- ~530 files total; `taoziyoyo` appears in 5 files (2 inside the prune set);
  `ansispire` appears in 191 files (internal naming — untouched by decision).
- **Assumption (verify at Phase 1)**: host global gitconfig identity is the
  operator's; the `.venv` carries the lint toolchain per
  `.agents/env/README.md`.

## §3 Scope

**In scope**

- Consolidation commit of the working tree on a new `feat/saberu-migration`
  branch in ansispire (archive evidence).
- Pruning per the approved list (§4 Phase 2), content adaptations (TODO trim,
  CHANGELOG reset, `taoziyoyo` reference fixes, README identity header,
  blueprint status note, `.secrets.baseline` regeneration).
- Creation of `saberu-ops/saberu`, single initial commit, tag `v0.0.1`,
  branches `master` (default) + `dev` (per Ansispire branching model).
- Push of `feat/saberu-migration` to the old origin as archived evidence.

**Out of scope**

- Internal `ansispire`→`saberu` renaming (191 files) — deferred to 0.0.2.
- Archiving/privatizing the old repository; deleting the `/tmp` worktrees;
  reconciling the superseded `feat/vps-profile-catalog` /
  `feat/governance-artifact-routing` branch tips.
- Any change on managed VPS hosts.

**Open decisions (each has a default; resolved no later than the Phase 4 gate)**

| Decision | Default | Owner |
|---|---|---|
| New repo visibility | `private` | user |
| Commit identity for the new repo | host global gitconfig (operator identity, no AI trailers — W-R25) | user |
| LICENSE copyright holder update | keep as-is unless it names the old account | user |

## §4 Implementation plan

#### Phase 1 — Consolidation commit (in ansispire)

**Goal**: turn the uncommitted working tree into reviewable, archived history.
**Pre-condition**: this plan APPROVED; `git config user.name/email` verified
against the host global gitconfig (W-R25).
**Steps**:
1. `git checkout -b feat/saberu-migration` from `feat/vps-software-catalog`
   (deliberately drags the uncommitted changes — they are the payload).
2. Commit the full working tree (including this workstream bundle) as
   `feat(saberu-migration): consolidate working tree as migration baseline`.
**Gate**: `git status --porcelain` empty; `git log -1` author/message match.
**Deliverables**: consolidation commit on `feat/saberu-migration`.

#### Phase 2 — Prune and adapt (commits on the migration branch)

**Goal**: make the tree byte-identical to the intended 0.0.1 content.
**Pre-condition**: Phase 1 gate passed.
**Steps** (each group one commit):
1. Delete: `docs/reviews/_archive/` (40), `docs/reviews/**/round*.changelog.md`
   (48; `docs/workstreams/**` changelogs are kept), `docs/reference-cn/` (11),
   `plugins/` (orphan `AGENTS.md`), `package.list`, `GEMINI.md`,
   `.geminiignore`.
2. Sweep dangling references: `git grep -l 'reference-cn\|GEMINI\|_archive'`
   plus a link pass over routing docs (`docs/AGENTS.md`,
   `docs/reviews/AGENTS.md`, `Makefile`); fix or drop each hit.
3. Fix `taoziyoyo` references in the 3 surviving files (`SECURITY.md`,
   `docs/reference/feature-map/INDEX.md`,
   `docs/reviews/refactor-docs-enterprise/plan-2026-05-10.md`) →
   `saberu-ops/saberu`.
4. `TODO.md`: remove completed entries, keep active/blocked ones.
5. `CHANGELOG.md`: reset to a single `[0.0.1]` entry summarizing the import
   and pointing to the archived ansispire repo for pre-history.
6. `README.md`: rewrite the identity/status header for Saberu; note the
   migration provenance. Check LICENSE holder line (open decision).
7. Add a dated status note to
   `docs/reviews/feat-product-redesign/plan-saberu-new-project-2026-06-23.md`:
   the "do not copy the old repo" premise is overridden by the 2026-07-18 user
   decision; design content remains reference.
8. Regenerate `.secrets.baseline` (`scripts/detect_secrets_gate.py` /
   detect-secrets scan) against the pruned tree; review any new finding.
**Gate**: automated — reference sweep returns zero hits; secrets gate clean.
**Deliverables**: prune/adapt commits; final tree = 0.0.1 content.

#### Phase 3 — Verification of the export candidate

**Goal**: 3-gate pass on the final tree before anything leaves this machine.
**Pre-condition**: Phase 2 gate passed.
**Steps**:
1. Gate 2 (static): `pre-commit run --all-files` (yamllint, ansible-lint,
   secrets) via the project venv; record output.
2. Gate 3 (functional, docs-heavy round): `scripts/check_claude_md_links.sh`;
   `ansible-playbook --syntax-check` on the entry playbooks;
   `make -n` smoke of Makefile targets that referenced pruned paths. Tools
   unavailable in this env are recorded as **blocked, not passed** (W-R24),
   from fresh probes.
**Gate**: all three gates clean in the same iteration (fix → restart from
gate 1; cap 3 iterations then stop and surface).
**Deliverables**: verification log excerpts for the round changelog.

#### Phase 4 — Create saberu-ops/saberu and push v0.0.1  ⛔ user gate

**Goal**: publish the pruned tree as the new repository's initial state.
**Pre-condition**: Phase 3 passed; **explicit user go** confirming the three
open decisions (visibility, identity, LICENSE) — this is the outward-facing
action gate.
**Steps** (no direct content commits to `master` or `dev` — the import travels
by PR, per the Ansispire branch model carried into the new repo):
1. `gh auth switch -u saberu-ops`; verify with `gh api user` (login must be
   `saberu-ops`) before any write.
2. Export: `git archive HEAD | tar -x -C <scratch>/saberu-export` (tracked
   files only — `.vault_pass`/`.venv` can never leak).
3. In the export dir: `git init -b master`; one **content-free** bootstrap
   root commit on `master` (`git commit --allow-empty -m "chore: initialize
   repository"`) so PR base branches exist — the sole, empty exception to the
   no-direct-commit rule; branch `dev` from it; branch
   `feat/saberu-0.0.1-import` from `dev` and commit the full exported tree
   there: `feat: Saberu 0.0.1 — initial import from ansispire (history
   archived upstream)`.
4. `gh repo create saberu-ops/saberu --private`; push `master`, `dev`,
   `feat/saberu-0.0.1-import`.
5. PR `feat/saberu-0.0.1-import` → `dev`; after merge, PR `dev` → `master`;
   after that merge, annotated tag `v0.0.1` on the `master` merge commit and
   push the tag. Merges are performed via `gh pr merge --merge` under the
   Phase-4 user go (or by the user directly if preferred).
6. Fresh-clone spot check: file count matches export manifest; re-run the
   link/secrets checks in the clone.

  | Probe result (`gh api user`) | Next action |
  |---|---|
  | login == `saberu-ops` | proceed |
  | any other login / error | stop; fix `gh auth switch` before any write |

**Gate**: `git ls-remote` shows `master`, `dev`, `v0.0.1`; both PRs merged;
clone checks pass.
**Deliverables**: live `saberu-ops/saberu` at v0.0.1.

#### Phase 5 — Closeout (in ansispire)

**Goal**: archive the evidence and sync truth sources.
**Pre-condition**: Phase 4 gate passed.
**Steps**:
1. `gh auth switch -u taoziyoyo2566`; push `feat/saberu-migration` to origin.
2. Write `round1-<date>.changelog.md` in this bundle (manifest, NOT-done list,
   gate evidence); update `TODO.md`; update this plan to COMPLETED.
**Gate**: Sync Guard pass (README/ARCHITECTURE/CHANGELOG/feature-map INDEX —
in the *new* repo where applicable, noted in the changelog).
**Deliverables**: round changelog; archived migration branch on old origin.

## §5 Verification

| Phase | Method | Pass condition | Evidence |
|---|---|---|---|
| 1 | `git status --porcelain`; `git log -1 --format='%an %ae %s'` | empty; operator identity + drafted message | changelog excerpt |
| 2 | reference grep sweep; secrets gate script | zero dangling refs; gate exit 0 | command output |
| 3 | `pre-commit run --all-files`; link check; playbook `--syntax-check` | all exit 0 in same iteration | logs (redacted if needed) |
| 4 | `gh api user`; `git ls-remote`; `gh pr list --state merged`; fresh clone re-checks | correct login; `master`+`dev`+`v0.0.1` present; both PRs merged; clone checks exit 0 | command output |
| 5 | round changelog exists; TODO/plan status updated | files committed | commit hash |

## §6 Risks and fallbacks

| Risk | Likelihood | Impact | Mitigation | Fallback |
|---|---|---|---|---|
| Pruning breaks doc routing/Makefile targets | med | low | Phase 2 step 2 sweep + Phase 3 link check | restore the individual file from the consolidation commit |
| Push uses cached `taoziyoyo2566` credential | med | med | `gh auth switch` + `gh api user` probe before write; HTTPS remote created by `gh` under the active account | delete the mis-pushed repo state is not needed — probe blocks before push |
| Regenerated secrets baseline surfaces new findings | low | med | review each finding at Phase 2 step 8; block export until clean | remove/redact offending content; restart from gate 1 |
| Working tree consolidation commits half-finished reorg from other branches | med | low | old repo keeps all branches + worktrees for reference; NOT-done list in changelog names the divergence | reconcile later in the archived repo if ever needed |
| LICENSE/identity legalities under new org | low | low | open decision resolved at Phase 4 gate | amend in a follow-up commit (0.0.1 tag content is additive-fixable via 0.0.2) |

## §7 Post-completion checklist

- Docs: new-repo `README.md` header verified live; this plan → COMPLETED with
  date; bundle `README.md` state table updated.
- `TODO.md`: add 0.0.2 follow-ups — internal `ansispire`→`saberu` rename
  (191 files, L2); old-repo archive/private switch; `/tmp` worktree cleanup;
  superseded branch-tip reconciliation.
- Changelog: `round1-<date>.changelog.md` with file-change manifest, explicit
  NOT-done, 3-gate results.
- Next work unlocked: 0.0.2 rename workstream; development continues in
  `saberu-ops/saberu` under the Ansispire branching model (`dev` trunk).
- Reflection: record any rules gap per
  `.agents/rules/execution-reflection.md` if execution deviates.
