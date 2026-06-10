# Environment Truth

Use this before relying on any recorded claim about the execution environment
(tool installed/absent, daemon running, credentials present, service reachable).

## Core rule

Environment capability facts are **dated snapshots, not invariants**. They expire
silently when something is installed, removed, or reconfigured between sessions.

- Before an environment claim becomes **load-bearing** — a plan pre-condition, a
  delegation-to-operator model, a "blocked" verdict, a skipped verification gate —
  **re-probe it**. Probes are cheap (< 5 s):
  - `command -v <tool>` / `<tool> --version`
  - `docker version` / `docker ps`
  - `gh auth status` / `git ls-remote origin HEAD`
- A "cannot run here" verdict must cite a **fresh probe**, never a recollection.

## Sources that age

All of these carry an implicit date and must not be trusted without re-probing:

- agent memory files and session summaries
- prior round changelogs and plan pre-condition sections
- **user statements** ("X isn't installed yet") — true when said, not forever

## Same-round correction

When a probe contradicts a recorded fact:

1. Update the record (memory file / doc / plan §2) in the **same round**.
2. Stamp the fact with the probe date.
3. Never write "assume this, don't re-discover" environment claims — that wording
   is the anti-pattern that caused the 2026-06-10 incident (a "no Docker daemon"
   memory outlived the limitation and mis-shaped an [L2] plan's delegation model).

## Session-bootstrap hook

During session bootstrap for substantial work, if the task plan depends on
environment capabilities, run the relevant probes as part of the status scan and
report the results (see `.agents/rules/session-bootstrap.md`).
