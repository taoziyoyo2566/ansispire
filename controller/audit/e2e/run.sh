#!/usr/bin/env bash
# controller/audit/e2e/run.sh — disposable end-to-end harness for TASK-001.
# Spec: docs/reference/test-specs/eda-reactor-e2e.md (TEST-EDA-004, L4).
#
# Steps:
#   1. clean — ensure no leftover from previous runs
#   2. up — semaphore + audit-sink + audit-relay + audit-reactor on isolated network
#   3. wait healthy
#   4. bootstrap (mints API token to .secrets.<project>, registers remediation templates)
#   5. recreate audit-relay + audit-reactor so they pick up the token
#   6. inject Disk Full event via the sink HTTP endpoint
#   7. poll Semaphore /api/project/1/tasks until status == success (or error)
#
# Retention: this script leaves the stack running at the end so you can
# inspect the WebUI at http://localhost:3320.
# Pass "down" as the first argument to tear it down and remove the
# project-specific env / secrets / inventory files.
set -euo pipefail

E2E_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${E2E_DIR}/../../.." && pwd)"

# Isolation: allow overriding project name (default to ansispire-e2e)
PROJECT="${E2E_PROJECT:-ansispire-e2e}"
# Use a safe suffix for project-specific files
PROJECT_SAFE=$(echo "${PROJECT}" | sed 's/[^a-zA-Z0-9_-]/_/g')

ENV_FILE="${E2E_DIR}/.env.${PROJECT_SAFE}"
SECRETS_FILE="${E2E_DIR}/.secrets.${PROJECT_SAFE}"
TEST_INVENTORY="${E2E_DIR}/hosts.${PROJECT_SAFE}.ini"
COMPOSE_FILE="${E2E_DIR}/compose.e2e.yml"
PYBIN="${REPO_ROOT}/.venv/bin/python3"
ANSIBLE_PLAYBOOK="${REPO_ROOT}/.venv/bin/ansible-playbook"

# Export container names so compose.e2e.yml uses them for isolation
export SEMAPHORE_CONTAINER_NAME="${PROJECT}-semaphore"
export AUDIT_SINK_CONTAINER_NAME="${PROJECT}-sink"
export AUDIT_RELAY_CONTAINER_NAME="${PROJECT}-relay"
export AUDIT_REACTOR_CONTAINER_NAME="${PROJECT}-reactor"
export CONTROLLER_NET_NAME="${PROJECT}-net"

# Keep the project-specific env file deterministic while allowing callers
# such as loopback_test_runner.sh to allocate collision-free host ports.
set_env_value() {
  local key="$1" value="$2" tmp
  tmp="${ENV_FILE}.tmp"
  if grep -q "^${key}=" "${ENV_FILE}"; then
    sed "s|^${key}=.*|${key}=${value}|" "${ENV_FILE}" >"${tmp}"
  else
    cp "${ENV_FILE}" "${tmp}"
    printf '%s=%s\n' "${key}" "${value}" >>"${tmp}"
  fi
  mv "${tmp}" "${ENV_FILE}"
}

# Bootstrap .env from .env.example if missing. Down mode also needs an env
# file because compose interpolates required variables before it can remove
# resources.
if [ ! -f "${ENV_FILE}" ]; then
  echo "==> [pre] ${ENV_FILE} missing — copying from .env.example"
  cp "${E2E_DIR}/.env.example" "${ENV_FILE}"
fi
if [ -n "${E2E_SEMAPHORE_PORT:-}" ]; then
  set_env_value SEMAPHORE_PORT "${E2E_SEMAPHORE_PORT}"
fi
if [ -n "${E2E_AUDIT_PORT:-}" ]; then
  set_env_value AUDIT_PORT "${E2E_AUDIT_PORT}"
fi

# Empty stub so docker compose --env-file can be combined with .secrets even
# before bootstrap has populated it. The real token lands here in step 4.
: > "${SECRETS_FILE}"

# Define common compose command after env/secrets exist so first-time
# project-specific runs also pass SEMAPHORE_API_TOKEN on service recreate.
COMPOSE=(docker compose -f "${COMPOSE_FILE}" -p "${PROJECT}" --env-file "${ENV_FILE}" --env-file "${SECRETS_FILE}")

if [[ "${1:-}" == "down" ]]; then
  echo "==> [clean] tearing down ${PROJECT}"
  "${COMPOSE[@]}" down -v --remove-orphans
  rm -f "${ENV_FILE}" "${SECRETS_FILE}" "${TEST_INVENTORY}"
  exit 0
fi

[ -f "${ANSIBLE_PLAYBOOK}" ] || { echo "ERROR: missing ${ANSIBLE_PLAYBOOK} — run \`make setup\` first"; exit 1; }

# Create a disposable inventory for the E2E container to use
cat >"${TEST_INVENTORY}" <<EOF
[all:vars]
ansible_connection=local
ansible_python_interpreter=/usr/bin/python3

[test_group]
localhost
EOF

START_TS=$(date +%s)
HOST_SEM_PORT=$(grep '^SEMAPHORE_PORT=' "${ENV_FILE}" | cut -d= -f2-)
HOST_AUDIT_PORT=$(grep '^AUDIT_PORT=' "${ENV_FILE}" | cut -d= -f2-)
ADMIN_USER=$(grep '^SEMAPHORE_ADMIN=' "${ENV_FILE}" | cut -d= -f2-)
ADMIN_PW=$(grep '^SEMAPHORE_ADMIN_PASSWORD=' "${ENV_FILE}" | cut -d= -f2-)
SEMAPHORE_URL_HOST="http://localhost:${HOST_SEM_PORT}"
SINK_URL_HOST="http://127.0.0.1:${HOST_AUDIT_PORT}/event"

echo "==> [1/7] clean: ensure fresh start for ${PROJECT}"
"${COMPOSE[@]}" down -v --remove-orphans 2>/dev/null || true

echo "==> [2/7] up: project=${PROJECT}, semaphore=${SEMAPHORE_URL_HOST}, sink=${SINK_URL_HOST}"
"${COMPOSE[@]}" up -d

echo "==> [3/7] wait semaphore healthy (≤90s)"
HEALTHY=""
for _ in $(seq 1 90); do
  status=$(docker inspect --format='{{.State.Health.Status}}' "${SEMAPHORE_CONTAINER_NAME}" 2>/dev/null || echo "starting")
  if [ "$status" = "healthy" ]; then HEALTHY=1; break; fi
  sleep 1
done
if [ -z "$HEALTHY" ]; then
  echo "ERROR: ${SEMAPHORE_CONTAINER_NAME} never became healthy (last=$status)"
  "${COMPOSE[@]}" logs --tail=50 semaphore || true
  exit 2
fi
echo "    healthy after $(( $(date +%s) - START_TS ))s"

echo "==> [4/7] bootstrap (mint token, register remediation templates)"
"${ANSIBLE_PLAYBOOK}" "${REPO_ROOT}/controller/semaphore/bootstrap.yml" \
  -i "${TEST_INVENTORY}" \
  -e "semaphore_user=${ADMIN_USER}" \
  -e "semaphore_password=${ADMIN_PW}" \
  -e "semaphore_url=${SEMAPHORE_URL_HOST}" \
  -e "secrets_path=${SECRETS_FILE}" \
  -e "semaphore_inventory_path=controller/audit/e2e/hosts.${PROJECT_SAFE}.ini"

[ -s "${SECRETS_FILE}" ] || { echo "ERROR: ${SECRETS_FILE} empty — bootstrap did not mint token"; exit 3; }
TOKEN=$(grep '^SEMAPHORE_API_TOKEN=' "${SECRETS_FILE}" | cut -d= -f2-)
[ -n "${TOKEN}" ] || { echo "ERROR: SEMAPHORE_API_TOKEN missing"; exit 3; }
echo "    token persisted to ${SECRETS_FILE}"

echo "==> [5/7] recreate audit-relay + audit-reactor (pick up token)"
"${COMPOSE[@]}" up -d --force-recreate audit-relay audit-reactor
sleep 4  # let reactor log "loaded N rules"

echo "==> [6/7] inject Disk Full event into the sink"
curl -fsS -X POST "${SINK_URL_HOST}" \
  -H 'Content-Type: application/json' \
  -d '{"source":"e2e-inject","event":{"id":99999,"object_type":"task","type":"task","status":"running","description":"E2E injection: Disk Full at /var/log"}}' \
  >/dev/null
echo "    injected"

echo "==> [7/7] poll Semaphore tasks until status=success (≤60s)"
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
  echo "    Stack is still RUNNING for manual inspection."
  echo "    URL: ${SEMAPHORE_URL_HOST} (${ADMIN_USER} / ${ADMIN_PW})"
  echo "    Manual cleanup: E2E_PROJECT=${PROJECT} ${0} down"
  exit 0
fi

echo "    last status='${FINAL_STATUS:-<none>}' task='${FINAL_ID:-<none>}' poll=${POLL_ELAPSED}s"
echo "==> [diag] reactor logs (last 60):"
"${COMPOSE[@]}" logs --tail=60 audit-reactor || true
echo "==> [diag] semaphore logs (last 40):"
"${COMPOSE[@]}" logs --tail=40 semaphore || true
echo "==> E2E FAIL (Stack left running for diagnosis)"
exit 4
