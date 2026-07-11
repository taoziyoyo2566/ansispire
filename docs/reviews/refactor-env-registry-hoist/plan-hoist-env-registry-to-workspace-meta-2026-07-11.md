# Plan — Hoist the env-capability registry from ansispire to the workspace layer

**Date**: 2026-07-11 · **Level**: 🔴 [L2] Architecture (cross-project) · **Cost**: Medium
**Branch**: `refactor/env-registry-hoist` stacked on **`feat/target-architecture`** (merges back to it) · spans **3 locations**: ansispire repo · workspace-meta repo (`~/workspace`) · host (`~/.claude/`)

> **Branch-base correction (2026-07-11)**: prerequisite check (W-R21 §b) shows `scripts/env_probe.sh`, `.agents/env/`, and commit `c816c09` do **not** exist on `dev` — they live only on `feat/target-architecture` (29 commits ahead of dev). So the refactor branch **must** stack on `feat/target-architecture`, not branch from `dev`. This also matches ansispire §4 (refactor ← parent feat/, → parent feat/).

## 0. Best-practice pre-check (W-R18)

- **Native mechanisms**: Claude Code loads skills from `~/.claude/skills/` (all sessions on the host) and hooks from `~/.claude/settings.json` (host-wide). Cross-project governance/tooling files sync via the **workspace-meta whitelist repo** (`~/workspace`, W-R26). So the host-probe machinery has native homes — it does not need to live inside a single product repo.
- **This matches the IVG's OWN original design**: `IVG-TOOLENV-REGISTRY §4.2` specified a three-layer model (user/host · workspace · project, lookup priority project > workspace > user). The 2026-06-10 implementation collapsed it into project-level `.agents/env/<host>.yml` for expediency; `OQ-1` (workspace vs `~/.claude` as the primary registry) was left **open**. This plan resolves OQ-1 and restores the intended layering.
- **OQ-1 resolution (user decision 2026-07-11)**: the mechanism is managed in **workspace-meta**, not `~/.claude`.

## 1. Purpose

The env-capability registry records **host** facts (docker/ansible/gh/linters present, daemon up, TTL). These are cross-project — duplicating the whole mechanism inside every product repo is wrong. Hoist the portable mechanism + host data to the workspace layer so all projects share one registry; leave only project-specific execution overrides in ansispire.

## 2. Scope (what moves)

| Artifact (now in ansispire) | Target | Type |
|---|---|---|
| `scripts/env_probe.sh` | `~/workspace/scripts/env_probe.sh` (whitelist) | portable mechanism |
| `make env-probe` / `env-probe-check` targets | `~/workspace/Makefile` | portable mechanism |
| `.agents/rules/environment-truth.md` (generic methodology) | `~/workspace/.agents/rules/environment-truth.md` (whitelist) | portable rule |
| `.agents/env/README.md` + `.agents/env/<host>.yml` data | `~/workspace/.agents/env/` (whitelist) | host data |
| `.claude/skills/env-sync/` | `~/.claude/skills/env-sync/` (host, all sessions) | harness — see §6 OQ-A |
| `.claude/settings.json` SessionStart hook (env-probe-check) | `~/.claude/settings.json` (host) | harness — see §6 OQ-A |

## 3. Out of scope (stays in ansispire)

- **Project execution overrides**: `host_overrides` ("use container-side ansible / semaphore image"), `command_truth` → `docs/governance/testing-governance.md §3–§4` (the task→command SSOT was always project-local; "关注点分离" holds).
- The `IVG-TOOLENV-REGISTRY.md` record stays as ansispire history (append a "hoisted 2026-07-11" note).
- No change to what the probe detects or the audit/onboard/controller runtime.

## 4. Success criteria

1. `make env-probe` / `env-probe-check` work from **any** workspace project (via workspace-level target or a thin project shim).
2. A fresh session in ansispire still gets the stale-registry SessionStart nudge.
3. workspace-meta pre-commit whitelist guard passes with the new `!` entries; nothing force-added.
4. ansispire no longer carries the portable mechanism; only the override tail + updated references remain.
5. 3-gate green: `bash -n env_probe.sh`, `--check`/`--probe` run, hook pipe-test fresh+stale.

## 5. Current-state gap / reference surface

~15 ansispire files reference the mechanism. Beyond the moved files, these need **reference updates** (path re-point, not move):
`.agents/rules/{coding-plan,evidence-backed-planning,execution-reflection,session-bootstrap}.md`, `docs/reference/feature-map/INDEX.md`, `docs/reference/investigations/{INDEX.md,IVG-TOOLENV-REGISTRY.md}`, `CHANGELOG.md`, `TODO.md`. Plan docs under `docs/reviews/` are historical — leave as-is.

## 6. Sub-decisions — RESOLVED 2026-07-11

- **OQ-A → host `~/.claude/`.** The env-sync skill + SessionStart hook live in `~/.claude/skills/env-sync/` and `~/.claude/settings.json` (host-wide, every session on the machine; not synced by workspace-meta by design — W-R26). Per-machine setup step documented in the workspace README. Rationale: host probe = host config.
- **OQ-B → workspace-meta.** Host data `<host>.yml` is committed to `~/workspace/.agents/env/` (shared across machines, matches the "clones see caps" rationale). Accepted tradeoff: periodic auto-generated churn in the governance repo.
- **OQ-C → fold in.** Converge the probe's `running:` field (currently dumps ALL container names) to a count + relevant-prefix filter **before** the data enters the governance repo. Part of Phase 1.

## 7. Phased roadmap (sign-off gates)

- **Phase 0** — resolve OQ-A/B/C (done); branch = `refactor/env-registry-hoist` **stacked on `feat/target-architecture`** (the only base holding the env-probe prerequisites; W-R21 §b), merges back to that parent feat.
- **Phase 1 — workspace-meta side (additive)**: add `env_probe.sh` (with OQ-C fix), Makefile targets, `.agents/rules/environment-truth.md`, `.agents/env/README.md` + data; add `!` whitelist entries to `~/workspace/.gitignore`; verify pre-commit guard; commit + push workspace-meta.
- **Phase 2 — host side (OQ-A=a)**: place env-sync skill + SessionStart hook into `~/.claude/`; pipe-test fresh/stale.
- **Phase 3 — ansispire side (removal + re-point)**: `git rm` the moved files; update the ~10 reference files to point at the workspace path; leave the override tail; append IVG "hoisted" note; sync INDEX/CHANGELOG/TODO; 3-gate.
- **Phase 4 — closeout**: round changelog in this topic dir; Next-Steps.

## 8. Rollback

Each phase is a separate commit in its own repo. Rollback = revert that repo's commit(s); ansispire removal (Phase 3) lands last, so until then both copies coexist and nothing breaks. No destructive sink beyond the workspace-meta push (revertible).

## 9. NOT done by this plan

- No change to probe detection logic (except OQ-C `running:` shaping).
- No move of the project-specific override tail or the task→command SSOT.
- No rewrite of workspace `CLAUDE.md` W-R24 (it already carries the methodology; the moved rule file is its elaboration).
