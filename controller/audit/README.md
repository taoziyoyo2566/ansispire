# Round 8 — Audit Sink

A tiny loopback-bound HTTP sink that turns Semaphore webhooks into a
grep-able / `jq`-able JSONL event stream.

## Why this shape

- **Plan D1=a**: Python container, not Caddy access log. We need to
  keep the structured payload (role changes, user logins, job triggers),
  not just a request-line audit.
- **Plan D4=a**: persistent volume + `logrotate` (7-day retention).
  Container restarts do not lose audit trail.
- **Stdlib-only**: no Flask / FastAPI dep — one file, one runtime
  (`python:3.12-alpine`, ~50 MB image).
- **Loopback-only**: bound to `127.0.0.1:3010` on the host. This is a
  learning sink, not a production audit bus.

## Start / stop

```bash
make controller-audit-up       # docker compose up -d
make controller-audit-down     # docker compose down (volume persists)
make controller-audit-tail     # tail -F the events.jsonl
make controller-audit-stats    # event counts by path/type via jq
```

## Payload schema

Each line in `events.jsonl` is one JSON object:

```json
{
  "ts": "2026-04-14T23:59:59Z",
  "remote": "172.18.0.3",
  "path": "/event",
  "ua": "Go-http-client/1.1",
  "payload": { /* forwarded Semaphore webhook body */ }
}
```

Non-JSON bodies are kept as a string in `payload` so a misconfigured
sender cannot silently lose audit coverage.

## Wiring Semaphore → sink

Semaphore v2.10 exposes a **Runners / Integrations** webhook for task
events. In the demo project, configure the webhook URL to the sink.
Inside Docker, the sink is reachable at the host bridge:

- From Semaphore container (same compose network is not used — the
  sink runs in its own compose): use `http://host.docker.internal:3010/event`
  on Linux with `--add-host host.docker.internal:host-gateway`, or
  use the host IP directly.
- From the host: `http://127.0.0.1:3010/event`

An alternative (safer): configure Semaphore to POST to the sink
through a small `socat` relay, or run both in the same compose network.
For the learning round we keep it simple and document the wiring here.

## Verifying the sink works (smoke test)

```bash
# Start
make controller-audit-up

# Send a test event
curl -s -X POST http://127.0.0.1:3010/event \
  -H 'Content-Type: application/json' \
  -d '{"event":"smoke_test","note":"from README"}'

# Tail the log
make controller-audit-tail
# You should see a single JSON line with "event":"smoke_test"
```

## Where the data lives

- Inside the container: `/var/log/semaphore/events.jsonl` (+ rotated `.gz`)
- On the host: Docker-managed named volume `audit_audit-data`
- Not gitignored as a directory because there is nothing committed —
  the volume is ephemeral infra state, not repo content.

## Privacy / sensitivity

Semaphore webhooks can include job output snippets. If a template ever
echoes a secret (vault-decrypted value in `-vv` output), that snippet
lands in `events.jsonl`. Treat the audit volume as **sensitive-internal**:

- Do not mount it into other containers.
- Do not expose port 3010 beyond loopback.
- Rotate promptly if a secret leaked into the log.

## Not in scope this round

- Shipping events to Loki (Round 9).
- Signing the JSONL (tamper-evidence) — future.
- Querying by role/user without `jq` (requires a database) — future.
