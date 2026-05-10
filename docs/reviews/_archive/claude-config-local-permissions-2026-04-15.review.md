# Config Review / Plan — Claude Local Permissions (Scheme B)

**Date**: 2026-04-15  
**Type**: configuration-only maintenance note (not a system “round”)  
**Level**: Engineering — local tooling/config hygiene  
**Cost estimate**: small

---

## Purpose

Reduce permission-prompt friction for local development while keeping basic guardrails and improving maintainability of `@.claude/settings.local.json`.

## Scope / Out of Scope

- **In scope**: only `@.claude/settings.local.json` edits + review/changelog docs for this config change.
- **Out of scope**: controller compose/Makefile changes, host configuration, system package installs, adding outbound network egress permissions.

## Proposed changes (Scheme B)

- **Local curl, generic**: allow `curl` with arbitrary arguments as long as the URL targets local HTTP loopback:
  - `http://localhost:*/*`
  - `http://127.0.0.1:*/*`
- **Repo scripts only**: remove `bash *` and allow only explicit in-repo scripts used by this project.
- **Isolated toolchain**: allow executing anything under `/tmp/ansible-lint-env/bin/*`.
- **Deduplicate + regroup**: remove redundant `yamllint` variants; group/sort allow entries for readability.
- **Remove malformed rule**: drop the nonfunctional compound `head/echo/ls` entry.

## Judgment criteria

- Day-to-day local `curl` against loopback services does not prompt.
- In-repo smoke scripts can run without prompts; arbitrary external `bash` execution is not blanket-allowed.
- Isolated `/tmp/ansible-lint-env/bin/*` tooling does not prompt.
- `@.claude/settings.local.json` remains valid JSON and is easier to maintain.

