#!/usr/bin/env bash
# controller/audit/loop-smoke.sh — Round 9 control-plane loop smoke test
#
# Asserts the end-to-end audit trail: an action taken in Semaphore via the
# REST API lands as a structured JSONL line in the audit sink within N
# seconds. Verifies the Round 9 wiring (polling relay + unified compose
# network) without requiring a UI click-through.
#
# Requires:
#   - make controller-up        (Semaphore on port 3001/host, 3000/container)
#   - make controller-audit-up  (sink + relay on controller-net)
#   - controller-bootstrap       has run (round8-rbac-demo project exists)
#
# Exits 0 on success, non-zero on miss.

set -euo pipefail

SEM_HOST_URL="${SEMAPHORE_URL:-http://localhost:3001}"
ENV_FILE="$(dirname "$0")/../semaphore/.env"
SINK_CONTAINER="${SINK_CONTAINER:-ansispire-audit-sink}"
JSONL="${JSONL:-/var/log/semaphore/events.jsonl}"
TIMEOUT="${SMOKE_TIMEOUT:-20}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "FAIL: $ENV_FILE not found — run 'make setup' then configure .env" >&2
  exit 1
fi

admin_pw=$(grep '^SEMAPHORE_ADMIN_PASSWORD=' "$ENV_FILE" | cut -d= -f2-)
cookie=/tmp/sm-loop-smoke.cookies

echo "── 1. log in as admin ──"
# Pre-check: is Semaphore reachable?
if ! curl -s --connect-timeout 2 "$SEM_HOST_URL" > /dev/null; then
  echo "FAIL: Semaphore not reachable at $SEM_HOST_URL" >&2
  exit 1
fi

code=$(curl -s -o /dev/null -w "%{http_code}" -c "$cookie" \
  -X POST "$SEM_HOST_URL/api/auth/login" \
  -H 'Content-Type: application/json' \
  -d "{\"auth\":\"admin\",\"password\":\"$admin_pw\"}")
[[ "$code" == "204" || "$code" == "200" ]] || { echo "FAIL: login HTTP $code" >&2; exit 1; }
echo "  OK login"

echo "── 2. resolve round8-rbac-demo project id ──"
pid=$(curl -s -b "$cookie" "$SEM_HOST_URL/api/projects" | \
  python3 -c "import sys,json; p_list=json.load(sys.stdin); print(next((p['id'] for p in p_list if p['name']=='round8-rbac-demo'), ''))")
[[ -n "$pid" ]] || { echo "FAIL: round8-rbac-demo project missing — run 'make controller-bootstrap'" >&2; exit 1; }
echo "  OK project id=$pid"

echo "── 3. trigger a detectable action (create dummy key) ──"
marker="loop_smoke_$$_$(date +%s)"

# Register cleanup handler
cleanup() {
  local exit_code=$?
  echo "── 5. clean up marker key ──"
  local key_id
  key_id=$(curl -s -b "$cookie" "$SEM_HOST_URL/api/project/$pid/keys" | \
    python3 -c "import sys,json; \
p_list=json.load(sys.stdin); \
print(next((k['id'] for k in p_list if k['name']=='$marker'), ''))")
  
  if [[ -n "$key_id" ]]; then
    curl -s -b "$cookie" -X DELETE "$SEM_HOST_URL/api/project/$pid/keys/$key_id" \
      -o /dev/null -w "  delete marker key: HTTP %{http_code}\n"
  else
    echo "  (marker key already gone or never created)"
  fi
  rm -f "$cookie"
  exit $exit_code
}
trap cleanup EXIT

code=$(curl -s -o /dev/null -w "%{http_code}" -b "$cookie" \
  -X POST "$SEM_HOST_URL/api/project/$pid/keys" \
  -H 'Content-Type: application/json' \
  -d "{\"name\":\"$marker\",\"type\":\"none\",\"project_id\":$pid}")
[[ "$code" == "204" || "$code" == "201" ]] || { echo "FAIL: key create HTTP $code" >&2; exit 1; }
echo "  OK action fired (marker=$marker)"

echo "── 4. wait for relay delivery (≤ ${TIMEOUT}s) ──"
start=$SECONDS
found=""
while (( SECONDS - start < TIMEOUT )); do
  # Check sink logs or file directly
  if docker exec "$SINK_CONTAINER" grep -q "$marker" "$JSONL" 2>/dev/null; then
    found=$((SECONDS - start))
    break
  fi
  echo -n "."
  sleep 2
done

if [[ -n "$found" ]]; then
  echo
  echo "Loop smoke: ALL GREEN — Semaphore → relay → sink delivered in ${found}s"
  exit 0
else
  echo
  echo "Loop smoke: FAIL — marker '$marker' not in JSONL after ${TIMEOUT}s" >&2
  echo "  inspect: docker logs $SINK_CONTAINER | tail; docker logs ansispire-audit-relay | tail" >&2
  exit 1
fi
