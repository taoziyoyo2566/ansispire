#!/usr/bin/env bash
# controller/audit/e2e/run.sh — disposable end-to-end harness for TASK-001.
# Spec: docs/test-specs/eda-reactor-e2e.md (TEST-EDA-004, L4).
#
# Steps:
#   1. up — semaphore + audit-sink + audit-relay + audit-reactor on isolated network
#   2. wait healthy
#   3. bootstrap (mints API token to ./.secrets, registers remediation templates)
#   4. recreate audit-relay + audit-reactor so they pick up the token
#   5. inject Disk Full event via the sink HTTP endpoint
#   6. poll Semaphore /api/project/1/tasks until status == success (or error)
#   7. teardown (down -v) — unless E2E_KEEP=1
#
# Override teardown for debugging: E2E_KEEP=1 ./run.sh
set -euo pipefail

E2E_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${E2E_DIR}/../../.." && pwd)"
PROJECT="ansispire-e2e"

ENV_FILE="${E2E_DIR}/.env"
SECRETS_FILE="${E2E_DIR}/.secrets"
COMPOSE_FILE="${E2E_DIR}/compose.e2e.yml"
PYBIN="${REPO_ROOT}/.venv/bin/python3"
ANSIBLE_PLAYBOOK="${REPO_ROOT}/.venv/bin/ansible-playbook"

# Bootstrap .env from .env.example on first run (no real secret in the stack)
if [ ! -f "${ENV_FILE}" ]; then
  echo "==> [pre] ${ENV_FILE} missing — copying from .env.example"
  cp "${E2E_DIR}/.env.example" "${ENV_FILE}"
fi
[ -f "${ANSIBLE_PLAYBOOK}" ] || { echo "ERROR: missing ${ANSIBLE_PLAYBOOK} — run \`make setup\` first"; exit 1; }

# Empty stub so docker compose --env-file can be combined with .secrets even
# before bootstrap has populated it. The real token lands here in step 3.
: > "${SECRETS_FILE}"

COMPOSE=(docker compose -f "${COMPOSE_FILE}" -p "${PROJECT}" --env-file "${ENV_FILE}" --env-file "${SECRETS_FILE}")

START_TS=$(date +%s)
HOST_SEM_PORT=$(grep '^SEMAPHORE_PORT=' "${ENV_FILE}" | cut -d= -f2-)
HOST_AUDIT_PORT=$(grep '^AUDIT_PORT=' "${ENV_FILE}" | cut -d= -f2-)
ADMIN_USER=$(grep '^SEMAPHORE_ADMIN=' "${ENV_FILE}" | cut -d= -f2-)
ADMIN_PW=$(grep '^SEMAPHORE_ADMIN_PASSWORD=' "${ENV_FILE}" | cut -d= -f2-)
SEMAPHORE_URL_HOST="http://localhost:${HOST_SEM_PORT}"
SINK_URL_HOST="http://127.0.0.1:${HOST_AUDIT_PORT}/event"

cleanup() {
  rc=$?
  if [ "${E2E_KEEP:-0}" = "1" ]; then
    echo "==> [teardown] E2E_KEEP=1 — leaving stack up. Inspect with:"
    echo "    ${COMPOSE[*]} ps"
    echo "    ${COMPOSE[*]} logs audit-reactor"
    echo "    Tear down manually: ${COMPOSE[*]} down -v"
    return $rc
  fi
  echo "==> [teardown] docker compose down -v"
  "${COMPOSE[@]}" down -v --remove-orphans 2>/dev/null || true
  rm -f "${SECRETS_FILE}" 2>/dev/null || true
  return $rc
}
trap cleanup EXIT

echo "==> [1/7] up: project=${PROJECT}, semaphore=${SEMAPHORE_URL_HOST}, sink=${SINK_URL_HOST}"
"${COMPOSE[@]}" up -d

echo "==> [2/7] wait semaphore healthy (≤90s)"
HEALTHY=""
for _ in $(seq 1 90); do
  status=$(docker inspect --format='{{.State.Health.Status}}' ansispire-semaphore-e2e 2>/dev/null || echo "starting")
  if [ "$status" = "healthy" ]; then HEALTHY=1; break; fi
  sleep 1
done
if [ -z "$HEALTHY" ]; then
  echo "ERROR: semaphore-e2e never became healthy (last=$status)"
  "${COMPOSE[@]}" logs --tail=50 semaphore || true
  exit 2
fi
echo "    healthy after $(( $(date +%s) - START_TS ))s"

echo "==> [3/7] bootstrap (mint token, register remediation templates)"
"${ANSIBLE_PLAYBOOK}" "${REPO_ROOT}/controller/semaphore/bootstrap.yml" \
  -e "semaphore_user=${ADMIN_USER}" \
  -e "semaphore_password=${ADMIN_PW}" \
  -e "semaphore_url=${SEMAPHORE_URL_HOST}" \
  -e "secrets_path=${SECRETS_FILE}"

[ -s "${SECRETS_FILE}" ] || { echo "ERROR: ${SECRETS_FILE} empty — bootstrap did not mint token"; exit 3; }
TOKEN=$(grep '^SEMAPHORE_API_TOKEN=' "${SECRETS_FILE}" | cut -d= -f2-)
[ -n "${TOKEN}" ] || { echo "ERROR: SEMAPHORE_API_TOKEN missing"; exit 3; }
echo "    token persisted to ${SECRETS_FILE}"

echo "==> [4/7] recreate audit-relay + audit-reactor (pick up token)"
"${COMPOSE[@]}" up -d --force-recreate audit-relay audit-reactor
sleep 4  # let reactor log "loaded N rules"

echo "==> [5/7] inject Disk Full event into the sink"
curl -fsS -X POST "${SINK_URL_HOST}" \
  -H 'Content-Type: application/json' \
  -d '{"source":"e2e-inject","event":{"id":99999,"object_type":"task","type":"task","status":"running","description":"E2E injection: Disk Full at /var/log"}}' \
  >/dev/null
echo "    injected"

echo "==> [6/7] poll Semaphore tasks until status=success (≤60s)"
POLL_START=$(date +%s)
FINAL_STATUS=""
FINAL_ID=""
for _ in $(seq 1 30); do
  resp=$(curl -fsS "${SEMAPHORE_URL_HOST}/api/project/1/tasks?limit=5" \
            -H "Authorization: Bearer ${TOKEN}" 2>/dev/null || echo "[]")
  read -r FINAL_STATUS FINAL_ID < <(printf '%s' "$resp" | "${PYBIN}" -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    d = []
if d:
    print(d[0].get("status",""), d[0].get("id",""))
else:
    print("", "")
' 2>/dev/null || echo "")
  case "${FINAL_STATUS}" in
    success|error) break ;;
  esac
  sleep 2
done
POLL_ELAPSED=$(( $(date +%s) - POLL_START ))
TOTAL_ELAPSED=$(( $(date +%s) - START_TS ))

if [ "${FINAL_STATUS}" = "success" ]; then
  echo "==> E2E PASS — task ${FINAL_ID} status=success in ${POLL_ELAPSED}s (total ${TOTAL_ELAPSED}s)"
  exit 0
fi

echo "    last status='${FINAL_STATUS:-<none>}' task='${FINAL_ID:-<none>}' poll=${POLL_ELAPSED}s"
echo "==> [diag] reactor logs (last 60):"
"${COMPOSE[@]}" logs --tail=60 audit-reactor || true
echo "==> [diag] semaphore logs (last 40):"
"${COMPOSE[@]}" logs --tail=40 semaphore || true
echo "==> E2E FAIL"
exit 4
