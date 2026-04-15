#!/usr/bin/env bash
# controller/rbac/smoke.sh — Round 8 RBAC smoke test
#
# Verifies least-privilege behavior of the 3 demo users without needing
# ansible-playbook on the host. Drives the Semaphore REST API directly.
#
# Requires:
#   - Semaphore running at http://localhost:3001 (or SEMAPHORE_URL env)
#   - The RBAC bootstrap has been run (controller-bootstrap target)
#   - controller/rbac/users.yml exists and holds the 3 generated passwords
#   - curl, python3, jq or (python3 -c 'json.load')
#
# Exits non-zero on any expectation miss.

set -euo pipefail

SEM="${SEMAPHORE_URL:-http://localhost:3001}"
USERS_FILE="$(dirname "$0")/users.yml"

if [[ ! -f "$USERS_FILE" ]]; then
  echo "FAIL: $USERS_FILE not found — run 'make controller-bootstrap' first" >&2
  exit 1
fi

pw_for() {
  python3 -c "
import sys, yaml
for u in yaml.safe_load(open('$USERS_FILE')):
    if u['username'] == '$1':
        print(u['password']); sys.exit(0)
sys.exit(1)
"
}

login() {
  local user="$1"
  local pw="$2"
  local cookie="/tmp/sm-$user.cookies"
  local code
  code=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "$SEM/api/auth/login" \
    -H 'Content-Type: application/json' \
    -d "{\"auth\":\"$user\",\"password\":\"$pw\"}" \
    -c "$cookie")
  if [[ "$code" != "204" && "$code" != "200" ]]; then
    echo "FAIL: login as $user returned HTTP $code" >&2
    return 1
  fi
  echo "$cookie"
}

expect_code() {
  local desc="$1" expected="$2" actual="$3"
  if [[ "$actual" == "$expected" ]]; then
    printf "  PASS  %-60s (HTTP %s)\n" "$desc" "$actual"
  else
    printf "  FAIL  %-60s (got HTTP %s, expected %s)\n" "$desc" "$actual" "$expected" >&2
    FAIL=1
  fi
}

admin_pw=$(grep '^SEMAPHORE_ADMIN_PASSWORD=' controller/semaphore/.env | cut -d= -f2-)
admin_cookie=$(login admin "$admin_pw")
demo_project_id=$(curl -s -b "$admin_cookie" "$SEM/api/projects" | \
  python3 -c "import sys,json; print(next(p['id'] for p in json.load(sys.stdin) if p['name']=='round8-rbac-demo'))")
echo "Demo project id: $demo_project_id"
echo

FAIL=0

echo "── demo_audit (guest) ──"
pw=$(pw_for demo_audit)
cookie=$(login demo_audit "$pw")
# Guest can read templates
code=$(curl -s -b "$cookie" -o /dev/null -w "%{http_code}" \
  "$SEM/api/project/$demo_project_id/templates")
expect_code "guest GET /templates" "200" "$code"
# Guest cannot create a template (expect 403)
code=$(curl -s -b "$cookie" -o /dev/null -w "%{http_code}" \
  -X POST "$SEM/api/project/$demo_project_id/templates" \
  -H 'Content-Type: application/json' -d '{"name":"x","playbook":"site.yml","app":"ansible"}')
expect_code "guest POST /templates (expect 403)" "403" "$code"
echo

echo "── demo_dev (task_runner) ──"
pw=$(pw_for demo_dev)
cookie=$(login demo_dev "$pw")
code=$(curl -s -b "$cookie" -o /dev/null -w "%{http_code}" \
  "$SEM/api/project/$demo_project_id/templates")
expect_code "task_runner GET /templates" "200" "$code"
code=$(curl -s -b "$cookie" -o /dev/null -w "%{http_code}" \
  -X POST "$SEM/api/project/$demo_project_id/templates" \
  -H 'Content-Type: application/json' -d '{"name":"x","playbook":"site.yml","app":"ansible"}')
expect_code "task_runner POST /templates (expect 403)" "403" "$code"
echo

echo "── demo_platform (owner) ──"
pw=$(pw_for demo_platform)
cookie=$(login demo_platform "$pw")
code=$(curl -s -b "$cookie" -o /dev/null -w "%{http_code}" \
  "$SEM/api/project/$demo_project_id/templates")
expect_code "owner GET /templates" "200" "$code"
# Owner can list keys
code=$(curl -s -b "$cookie" -o /dev/null -w "%{http_code}" \
  "$SEM/api/project/$demo_project_id/keys")
expect_code "owner GET /keys" "200" "$code"
echo

echo "── cross-project scoping ──"
# demo_audit should have NO access to the Round 7 ansible-demo project
r7_pid=$(curl -s -b "$admin_cookie" "$SEM/api/projects" | \
  python3 -c "import sys,json; \
print(next((p['id'] for p in json.load(sys.stdin) if p['name']=='ansible-demo'), ''))")
if [[ -n "$r7_pid" ]]; then
  pw=$(pw_for demo_audit)
  cookie=$(login demo_audit "$pw")
  code=$(curl -s -b "$cookie" -o /dev/null -w "%{http_code}" \
    "$SEM/api/project/$r7_pid/templates")
  expect_code "demo_audit cross-project (expect 403/404)" "403" "$code" || \
    expect_code "demo_audit cross-project (expect 404)" "404" "$code"
else
  echo "  SKIP  ansible-demo project not found (run controller-bootstrap first)"
fi
echo

if [[ "$FAIL" -eq 0 ]]; then
  echo "RBAC smoke test: ALL GREEN"
  exit 0
else
  echo "RBAC smoke test: FAILURES — see above" >&2
  exit 1
fi
