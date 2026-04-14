# Chinese Reference Snapshots

This directory holds **Chinese-language snapshots** of project runtime documents that have been rewritten in English to reduce Claude session token cost.

**These files are NOT loaded by Claude Code.** They exist for human reference only.

## Layout

```
reference-cn/
└── snapshot-YYYY-MM-DD/
    ├── CLAUDE.zh.md                    # mirrors ../../CLAUDE.md (Chinese)
    ├── memory/                         # mirrors the memory/ directory
    └── docs/reviews/                   # mirrors docs/reviews/*.md
```

## Snapshots

- `snapshot-2026-04-14/` — state immediately before refactor-i18n-a

## How to update

When English runtime files change and you want the Chinese snapshot to reflect the new semantics, either:

1. **Create a new dated snapshot** (recommended for major rewrites): `cp -r` the current English runtime files to a new `snapshot-YYYY-MM-DD/` and translate them.
2. **Abandon sync** (pragmatic): treat Chinese snapshots as frozen historical references. Use them to recall the original intent when reviewing English versions.

Option 2 is the default — avoid the maintenance cost of dual maintenance.
