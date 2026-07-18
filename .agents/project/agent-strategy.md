# Agent Strategy

This repo may use `AGENTS.md`, `CLAUDE.md`, and `GEMINI.md` together.
Do not assume any one of them is automatically the best or most current source for every task.

## Intended Split

- `AGENTS.md` and nested `AGENTS.md`
  - task routing
  - path-local guidance
  - minimal context loading

- `.agents/`
  - modular rule and scenario fragments used by `AGENTS.md`

- `CLAUDE.md`
  - Claude workflow baseline
  - task classification, sync discipline, branch lifecycle

- `GEMINI.md`
  - Gemini / cross-agent complement
  - context discipline, peer-audit correction, codification emphasis

- repo docs and code
  - current operational truth for architecture, testing, feature scope, and active plans

## Decision Order

When guidance conflicts or seems stale, use this order:

1. user instruction
2. deeper path-local `AGENTS.md`
3. current repo truth
   - `ARCHITECTURE.md`
   - `TODO.md`
   - `docs/governance/*`
   - `docs/reference/feature-map/*`
   - active plans/evidence in `docs/workstreams/`, with `docs/reviews/` as the
     legacy fallback for unmigrated topics
   - current code
4. `CLAUDE.md` and `GEMINI.md`
5. historical investigations, reviews, and archived docs

## Practical Rule

- Use `CLAUDE.md` and `GEMINI.md` as governance inputs, not blind law.
- If either file appears overfit, stale, or in tension with the current repo state, flag it and prefer current evidence.
- If both are useful, combine them:
  - let `AGENTS.md` handle routing and local context
  - let `CLAUDE.md` provide Claude-specific workflow guidance
  - let `GEMINI.md` provide complementary Gemini / cross-agent guidance

## What Not To Do

- Do not hard-code one AI config file as the sole source of truth unless the repo explicitly standardizes that.
- Do not copy rules from `CLAUDE.md` or `GEMINI.md` into `.agents/` unless they are still clearly useful and non-conflicting.
