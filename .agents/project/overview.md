# Project Overview

`ansispire` is a multi-server management control system built around Ansible, Semaphore, and event-driven remediation.

Source-of-truth order:

1. `ARCHITECTURE.md`
2. `TODO.md`
3. `docs/reference/investigations/INDEX.md`
4. `docs/reference/feature-map/INDEX.md`
5. code and task-local docs

AI guidance inputs:

- `AGENTS.md` and `.agents/` for Codex routing and modular rules
- `CLAUDE.md` for the Claude workflow baseline
- `GEMINI.md` for Gemini / cross-agent complement
- if they conflict with current repo truth, prefer current repo truth

Main surfaces:

- `controller/`: control plane and audit plane
- `roles/` and `playbooks/`: data-plane automation
- `plugins/`: local extension surface
- `inventory/`: environment and fleet definitions
- `docs/`: governance, feature maps, investigations, plans, reviews

Old plans are not active truth unless they still match `TODO.md` and current feature maps.
