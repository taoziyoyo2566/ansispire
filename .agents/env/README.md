# Environment registry — project override layer (ansispire)

The **host capability registry moved to the workspace layer** on 2026-07-11
(IVG-TOOLENV-REGISTRY §4.2 three-layer model; hoisted so every project under
`~/workspace` shares one probe instead of duplicating it per repo).

- **Host registry + mechanism**: `~/workspace/.agents/env/<host>.yml`,
  `~/workspace/scripts/env_probe.sh`, `make -C ~/workspace env-probe[-check]`.
- **Behavior rule**: `~/workspace/.agents/rules/environment-truth.md` (probe, don't recall).
- **Freshness**: a per-host SessionStart hook (`~/.claude/settings.json`) nudges when stale.

## Project override — tools ansispire provides via its venv

The shared host probe runs against the **bare host PATH**, so the host registry
reports these as `available: false` even though **this project provides them via
`.venv/bin/`** (the `$(BIN)` prefix in the `Makefile`):

| Tool | Host registry | ansispire reality |
|---|---|---|
| `ansible-playbook` / `ansible` (core) | `available: false` | present via `.venv/bin/` — use `make` targets or `$(BIN)ansible-playbook` |
| `ansible-lint` | `available: false` | present via `.venv/bin/` — `make ansible-lint` |
| `yamllint` | `available: false` | present via `.venv/bin/` — `make yamllint` |

**Do not read the host-level `false` as "cannot lint / syntax-check here."** It
means the host PATH lacks them; ansispire runs them from its venv. The
task→command SSOT (which command for which gate) is
`docs/governance/testing-governance.md §3–§4`. Docker / gh / make / jq / python3
capability facts are host-wide — read them from the host registry above.
