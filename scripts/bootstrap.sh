#!/usr/bin/env bash
# Robust Bootstrap 2.1 — Dependency Guard & Venv Isolation
set -euo pipefail

VENV=".venv"
PROJECT_ROOT=$(pwd)

# Safety lock: ensure pip only runs inside venv
export PIP_REQUIRE_VIRTUALENV=true

echo "==> [1/4] Initializing Python Virtual Environment..."
if [ ! -d "$VENV" ]; then
    python3 -m venv "$VENV"
fi

# Inject paths into activate script (Idempotent)
ACTIVATE="$VENV/bin/activate"
if ! grep -q "ANSIBLE_COLLECTIONS_PATH" "$ACTIVATE"; then
    cat << EOF >> "$ACTIVATE"

# Ansispire SSOT Paths
export ANSIBLE_CONFIG="$PROJECT_ROOT/ansible.cfg"
export ANSIBLE_COLLECTIONS_PATH="$PROJECT_ROOT/collections"
export ANSIBLE_ROLES_PATH="$PROJECT_ROOT/roles"
export PATH="$PROJECT_ROOT/$VENV/bin:\$PATH"
EOF
fi

echo "==> [2/4] Installing Locked Dependencies from requirements.txt..."
"$VENV/bin/python" -m pip install --upgrade pip
"$VENV/bin/python" -m pip install -r requirements.txt

echo "==> [3/4] Installing Galaxy roles and collections..."
"$VENV/bin/ansible-galaxy" role install -r requirements.yml --force
"$VENV/bin/ansible-galaxy" collection install -r requirements.yml --force

echo "==> [4/4] Finalizing paths and self-check..."
# Ensure paths are set for the integrity check
export ANSIBLE_CONFIG="$PROJECT_ROOT/ansible.cfg"
export ANSIBLE_COLLECTIONS_PATH="$PROJECT_ROOT/collections"
export ANSIBLE_ROLES_PATH="$PROJECT_ROOT/roles"
export PATH="$PROJECT_ROOT/$VENV/bin:$PATH"

echo "==> Setup complete. Running integrity check..."

"$VENV/bin/ansible-playbook" playbooks/site.yml --syntax-check

echo "----------------------------------------------------------------"
echo " SUCCESS: Ansispire environment is ready (Venv-Locked)."
echo " Action: Run 'source .venv/bin/activate' to start."
echo "----------------------------------------------------------------"
