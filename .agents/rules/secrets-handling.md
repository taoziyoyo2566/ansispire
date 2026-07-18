# Secrets Handling

Use this when a change creates, moves, or consumes secret material
(SSH keys, API tokens, passwords, vault content).

## Hard floor (non-negotiable)

- Real secret material **must not be committed or pushed**. If it appears in the
  working tree, index, history, logs, or tool output, stop further exposure,
  redact reports, inspect its state without printing the value, and follow
  `.agents/rules/authorization.md` plus `.agents/rules/git.md` for remediation.
  Do not treat `git rm --cached`, history rewriting, or credential rotation as
  unconditionally authorized.
- `make detect-secrets` gates `verify`; new findings must be resolved, not baselined
  away without reason.

## Placement conventions (follow existing patterns)

| Kind | Location | Pattern |
|---|---|---|
| Controller M2M token | `controller/semaphore/.secrets` | gitignored; written by `bootstrap.yml`; consumed via `--env-file` |
| Vault password | `.vault_pass` | gitignored; consumed via `ansible.cfg vault_password_file` |
| Encrypted vars | `inventory/local/vault.yml` | ansible-vault encrypted; safe to track |
| Operator-entered env secrets | `.env` manual block | NOT rendered by manifest-sync; `.env.example` carries placeholder + "set before first boot" comment (see `SEMAPHORE_ADMIN_PASSWORD`) |
| Mounted key material | gitignored dir next to consumer (e.g. `controller/semaphore/secrets/`) | mounted `:ro` into the container at a fixed path; never baked into images |
| Semaphore Key Store entries | created by `bootstrap.yml` as placeholders | `REPLACE-VIA-UI` placeholder text; operator injects the real value in the UI; IaC never carries the real key |

## Rules of use

- Secrets are **not** rendered through `manifest-sync` — that chain is for ports
  and image tags only.
- Playbook tasks that handle secret values set `no_log: true`.
- Evidence and changelogs: redact secret-adjacent strings (keys, real IPs,
  hostnames) to placeholders before committing (`plan-structure.md §5`).
- A new secret location requires: gitignore entry + `.env.example`/README note +
  this table updated — in the same change.
- A plan that stores or consumes the same secret in multiple places must record
  why duplication is necessary, who can access each copy, how rotation works,
  and what future change can remove the duplication.
- When execution creates or changes secret-backed external resources, record only
  ids/names/lifecycle metadata per `.agents/rules/execution-reflection.md`; never
  record secret values.
