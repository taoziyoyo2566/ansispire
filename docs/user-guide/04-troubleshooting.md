# Troubleshooting Guide

> **Audience**: anyone hitting an error message or unexpected behavior.
> **How to use**: search for an exact error string with Ctrl-F, find your row, follow the fix. If your case is not here, see the deeper context in [`02-quickstart-eda.md`](./02-quickstart-eda.md) §10 or [`operations/hub-deployment.md`](../operations/hub-deployment.md) §5.

---

## 1. Self-healing chain (audit → reactor → Semaphore)

| Symptom | Root cause | Fix |
|---|---|---|
| `Password must be provided via -e semaphore_password=` | You used `sem_pass=` (deprecated Gemini-158-line shorthand) | Run `make controller-bootstrap` (uses the canonical var), or pass `-e semaphore_password=...` explicitly |
| Reactor logs only show `SEMAPHORE_API_TOKEN not set` | Bootstrap has not run, or audit stack started before bootstrap minted the token | `make controller-bootstrap && make controller-audit-down && make controller-audit-up` |
| Reactor receives the event but never matches | Field name typo in `rules.json` `condition`, or `_contains` substring does not match the event text | Diff the event payload against `rules.json` line-by-line; run `make test-eda-contract` first |
| Reactor matches but `could not resolve template <name>` | `rules.json` references a `template_name` that bootstrap.yml never registers | `make test-eda-contract` should catch this; if it leaks past CI, add the template to the Register loop in `controller/semaphore/bootstrap.yml` |
| Reactor logs `JSON parse error: Expecting value` | Injected event has literal newlines or mismatched quote nesting | Use the single-line `printf` form from the §5.6 example in `02-quickstart-eda.md` |
| Web UI port unreachable after editing manifest | docker compose does not auto-restart on `.env` change | `make controller-down && make controller-up` |
| `make controller-bootstrap` fails with permission error / `.secrets` is owned by root | `ansible.cfg` global `become = True` is leaking into the bootstrap play | Already fixed via explicit `become: false` in `bootstrap.yml` and `playbooks/manifest_sync.yml`; re-check those headers |
| 401 Unauthorized after token mint, token in `.secrets` looks truncated | `cut -d= -f2` chops off base64 padding | Use `cut -d= -f2-` (the trailing `-` keeps everything after the first `=`) |

## 2. Path A (real hub deploy)

| Symptom | Root cause | Fix |
|---|---|---|
| `--check --diff` reports `cookies_string` undefined | In check mode the Login task is a no-op, so subsequent token-block tasks have no cookies | Already fixed: token block guarded with `when: not ansible_check_mode` |
| rsync uploads `.claude/` / `.env` / `.demo_*.pw` to remote | Old role had only 2 excludes (`.git`, `.venv`) | Already fixed: 21-pattern exclude list in `roles/ansispire_hub/tasks/main.yml`; if a leak recurs, audit that file first |
| `.eda_token` disappears on every deploy | Old token lived in `/opt/ansispire/.eda_token` (inside the rsync target dir; `--delete` wiped it) | Already fixed: token now in `/var/lib/ansispire/state/.eda_token`, outside the rsync target |
| `Host is using the discovered Python interpreter at /usr/bin/python3.13` warning | Auto-discovery; no explicit pin | Already fixed: `inventory/hosts.ini` pins `ansible_python_interpreter` per host |
| `ansible.posix.synchronize` raises a `to_text` deprecation warning | Collection's internal import path lags upstream Python | Suppress; ansible-core 2.24 will not break it. Tracked upstream |
| `infra_baseline` immediately fails with `NOT IMPLEMENTED` on Alpine / Rocky | Intentional Round-4 OS-family gate | Wait for the multi-OS expansion task (TASK-007); do not put Alpine/Rocky hosts in the hub deploy until then |

## 3. Toolchain / verify chain

| Symptom | Root cause | Fix |
|---|---|---|
| `ansible-lint --profile prod` argparse error | `prod` is not a valid profile name (legal: `min`, `basic`, `moderate`, `safety`, `shared`, `production`) | Already fixed in Makefile: use `--profile production` |
| `make lint` fails with `Attempting to decrypt but no vault secrets found` | `ansible-lint` does not auto-discover `.vault_pass` | Already fixed: `vault_password_file = .vault_pass` is set in `ansible.cfg`. If `.vault_pass` is missing, create one (`echo "<password>" > .vault_pass && chmod 600 .vault_pass`) |
| `Section [prod:children] includes undefined group 'targets_debian'` when running `-i inventory/prod` | Forward-referenced group not defined inline | Already fixed: `inventory/prod/hosts.ini` declares all referenced groups (empty placeholders if needed) |
| `make verify` dry-run fails with "Could not find the requested service nginx" | dry-run was running webserver role on the local control node where nginx is not installed | Already fixed: dry-run target re-scoped to `--limit hub_local` so only the common play runs |
| `ansible-rulebook` not found | EDA collection executable not on PATH | `pip install ansible-rulebook` in the project venv, or use `ansible-galaxy collection install ansible.eda` for the rulebook DSL |

## 4. Where to look beyond this guide

- The full long-form context (rationale + recovery paths): [`02-quickstart-eda.md`](./02-quickstart-eda.md) §10–§11
- Maintainer command-level ops: [`operations/eda-core.md`](../operations/eda-core.md), [`operations/hub-deployment.md`](../operations/hub-deployment.md)
- Past investigations / RCAs: [`reference/investigations/INDEX.md`](../reference/investigations/INDEX.md) — search by keyword; if a row is `Applied`, the fix is already in the linked location
