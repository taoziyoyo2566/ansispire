# Codex Capability Discovery

Use this to reduce token cost, shorten elapsed time, and improve task completion accuracy by choosing the right Codex capability before doing work the slow way.

## When to check

Do a lightweight capability check:

- during session bootstrap when the user is resuming substantial work
- before writing a plan for a large, repeated, cross-surface, or high-risk task
- when a task looks like it could benefit from parallel review, tool discovery, generated assets, structured docs lookup, or specialized automation
- when recent failures suggest the current execution pattern is inefficient or error-prone

Do not spend more effort discovering tools than the task itself warrants.

## What to check

- Available local/deferred tools via `tool_search` when a capability may exist but is not already visible.
- Built-in tools already available in the current session, especially parallel command execution, planning, patching, and local verification.
- Official OpenAI / Codex documentation for Codex or OpenAI product capabilities when the task depends on current product behavior.
- Third-party tools or references only when they materially improve the task and the information is likely current enough to matter.

## Plan integration

For coding-related plans, include a **Capability fit** note:

- Which Codex/tooling capability will be used, if any.
- Why it is better than the basic manual path.
- What is deliberately not used and why.

Examples:

- Use parallel read-only inspections for independent file/diff checks.
- Use a sub-agent only when the user explicitly asked for sub-agents or parallel agent work and the subtask has an independent scope.
- Use tool discovery before assuming no specialized helper exists.
- Use official docs lookup before relying on memory for current Codex/OpenAI behavior.

## Learning loop

When a capability clearly improves a recurring task class, codify it:

- update `.agents/rules/*.md` or a path-local `AGENTS.md`
- mention the before/after reason in a changelog or closeout
- keep the rule scoped to the task class where it helps

The goal is not novelty. The goal is lower token cost, shorter elapsed time, and fewer incomplete or wrong task outcomes.
