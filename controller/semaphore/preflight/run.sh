#!/usr/bin/env bash
# controller/semaphore/preflight/run.sh — disposable Semaphore + full-mode
# API contract preflight. Used by `make test-api-contract` and CI matrix.
#
# Steps:
#   1. clean — tear down any prior preflight project
#   2. up — bare Semaphore container on an isolated host port
#   3. wait healthy (≤90 s)
#   4. run bootstrap_preflight.yml with -e preflight_mode=full
#   5. teardown (always — this is a hermetic test, no leave-running mode)
#
# Env:
#   SEMAPHORE_IMAGE_TAG       — image tag to test (default: pulled from
#                               config/manifest.yml ansispire_versions.semaphore_pinned)
#   SEMAPHORE_PREFLIGHT_PORT  — host port (default 3301; pick another if
#                               3301 is busy locally)
set -euo pipefail

PREFLIGHT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${PREFLIGHT_DIR}/../../.." && pwd)"

PROJECT="ansispire-apicontract"
COMPOSE_FILE="${PREFLIGHT_DIR}/compose.yml"
ENV_FILE="${PREFLIGHT_DIR}/.env"
ANSIBLE_PLAYBOOK="${REPO_ROOT}/.venv/bin/ansible-playbook"
PYBIN="${REPO_ROOT}/.venv/bin/python3"

# Resolve image tag: explicit env > manifest pinned > "latest"
if [ -z "${SEMAPHORE_IMAGE_TAG:-}" ]; then
  if [ -x "${PYBIN}" ]; then
    SEMAPHORE_IMAGE_TAG=$("${PYBIN}" -c '
import yaml, sys
with open("'"${REPO_ROOT}"'/config/manifest.yml") as f:
    m = yaml.safe_load(f)
v = m.get("ansispire_versions", {}) or {}
pinned = v.get("semaphore_pinned") or v.get("default_tag") or "latest"
print(pinned)
' 2>/dev/null || echo "latest")
  else
    SEMAPHORE_IMAGE_TAG="latest"
  fi
fi
export SEMAPHORE_IMAGE_TAG

SEMAPHORE_PREFLIGHT_PORT="${SEMAPHORE_PREFLIGHT_PORT:-3301}"
export SEMAPHORE_PREFLIGHT_PORT

# Generate ephemeral admin password each run; .env is gitignored.
SEMAPHORE_ADMIN="${SEMAPHORE_ADMIN:-admin}"
SEMAPHORE_ADMIN_PASSWORD="${SEMAPHORE_ADMIN_PASSWORD:-$(head -c18 /dev/urandom | base64 | tr -d '/+=' | head -c24)}"
umask 077
cat > "${ENV_FILE}" <<EOF
SEMAPHORE_IMAGE_TAG=${SEMAPHORE_IMAGE_TAG}
SEMAPHORE_PREFLIGHT_PORT=${SEMAPHORE_PREFLIGHT_PORT}
SEMAPHORE_ADMIN=${SEMAPHORE_ADMIN}
SEMAPHORE_ADMIN_PASSWORD=${SEMAPHORE_ADMIN_PASSWORD}
EOF

COMPOSE=(docker compose -f "${COMPOSE_FILE}" -p "${PROJECT}" --env-file "${ENV_FILE}")

cleanup() {
  echo "==> [teardown] removing ${PROJECT}"
  "${COMPOSE[@]}" down -v --remove-orphans 2>/dev/null || true
  rm -f "${ENV_FILE}"
}
trap cleanup EXIT INT TERM

echo "==> [1/4] clean (no leftover from prior run)"
"${COMPOSE[@]}" down -v --remove-orphans 2>/dev/null || true

echo "==> [2/4] up: image=semaphoreui/semaphore:${SEMAPHORE_IMAGE_TAG}, port=${SEMAPHORE_PREFLIGHT_PORT}"
"${COMPOSE[@]}" up -d

echo "==> [3/4] wait semaphore healthy (≤90 s)"
START_TS=$(date +%s)
HEALTHY=""
for _ in $(seq 1 90); do
  status=$(docker inspect --format='{{.State.Health.Status}}' \
    ansispire-apicontract-semaphore 2>/dev/null || echo "starting")
  if [ "${status}" = "healthy" ]; then HEALTHY=1; break; fi
  sleep 1
done
if [ -z "${HEALTHY}" ]; then
  echo "ERROR: semaphore never became healthy (last=${status})"
  "${COMPOSE[@]}" logs --tail=80 semaphore || true
  exit 2
fi
echo "    healthy after $(( $(date +%s) - START_TS ))s"

[ -f "${ANSIBLE_PLAYBOOK}" ] || { echo "ERROR: missing ${ANSIBLE_PLAYBOOK} — run \`make setup\` first"; exit 1; }

# Disposable inventory so the play has [test_group] localhost to target.
TEST_INVENTORY="${PREFLIGHT_DIR}/.hosts.ini"
cat > "${TEST_INVENTORY}" <<EOF
[all:vars]
ansible_connection=local
ansible_python_interpreter=${PYBIN}

[test_group]
localhost
EOF
trap 'cleanup; rm -f "${TEST_INVENTORY}"' EXIT INT TERM

echo "==> [4/4] run preflight (mode=full) against tag=${SEMAPHORE_IMAGE_TAG}"
"${ANSIBLE_PLAYBOOK}" "${REPO_ROOT}/controller/semaphore/bootstrap_preflight.yml" \
  -i "${TEST_INVENTORY}" \
  -e "semaphore_user=${SEMAPHORE_ADMIN}" \
  -e "semaphore_password=${SEMAPHORE_ADMIN_PASSWORD}" \
  -e "semaphore_url=http://localhost:${SEMAPHORE_PREFLIGHT_PORT}" \
  -e "preflight_mode=full"

echo "==> API contract preflight PASS (tag=${SEMAPHORE_IMAGE_TAG})"
