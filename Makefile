# Makefile — common command wrappers; reduces memorization overhead
# Usage: make <target>
# List all available commands: make help

.DEFAULT_GOAL := help

.PHONY: help setup install lint yamllint ansible-lint syntax test molecule-all dry-run \
        deploy-dev deploy-stag deploy-prod tags ping vault-edit vault-encrypt \
        ee-build navigator clean \
        controller-net manifest-sync ports-sync \
        controller-up controller-down controller-logs controller-reset \
        controller-bootstrap \
        controller-audit-up controller-audit-down \
        controller-audit-tail controller-audit-stats \
        controller-rbac-smoke \
        controller-loop-smoke \
        test-eda test-eda-unit test-eda-contract test-eda-component \
        test-eda-relay-unit test-eda-sink-unit test-eda-e2e \
        test-filters test-vps-manager detect-secrets \
        vps-manager-syntax \
        vps-new vps-recover vps-submit vps-tasks \
        vps-manager-init vps-manager-process vps-manager-validate \
        hub-deploy hub-deploy-check

# Control-plane compose command wrapper
CONTROLLER_DIR := controller/semaphore
CONTROLLER_ENV := $(CONTROLLER_DIR)/.env
CONTROLLER_COMPOSE := docker compose -f $(CONTROLLER_DIR)/docker-compose.yml --env-file $(CONTROLLER_ENV)

# Virtual environment handling
VENV_NAME := .venv
PROJECT_PATH := $(shell pwd)
VENV_BIN := $(PROJECT_PATH)/$(VENV_NAME)/bin
BIN := $(VENV_BIN)/

# Force PATH to prioritize VENV and set SSOT paths
export PATH := $(VENV_BIN):$(PATH)
export ANSIBLE_CONFIG := $(PROJECT_PATH)/ansible.cfg
export ANSIBLE_ROLES_PATH := $(PROJECT_PATH)/roles
export ANSIBLE_COLLECTIONS_PATH := $(PROJECT_PATH)/collections
export ANSIBLE_LOCAL_TEMP ?= $(PROJECT_PATH)/.ansible/tmp
export ANSIBLE_REMOTE_TEMP ?= /tmp/ansispire-ansible-tmp

$(shell mkdir -p $(ANSIBLE_LOCAL_TEMP))

# Operator convenience: `make vps-recover hk-d13` and `make vps-submit hk-d13`
# treat the second goal as the alias/selector. Prefer explicit ALIAS=... or FILE=...
VPS_EXTRA_GOAL := $(if $(filter vps-recover vps-submit,$(firstword $(MAKECMDGOALS))),$(word 2,$(MAKECMDGOALS)))
VPS_RECOVER_ALIAS := $(strip $(or $(ALIAS),$(if $(filter vps-recover,$(firstword $(MAKECMDGOALS))),$(VPS_EXTRA_GOAL))))
VPS_SUBMIT_SELECTOR := $(strip $(or $(FILE),$(ALIAS),$(if $(filter vps-submit,$(firstword $(MAKECMDGOALS))),$(VPS_EXTRA_GOAL))))
ifneq ($(VPS_EXTRA_GOAL),)
$(VPS_EXTRA_GOAL):
	@:
endif

# Molecule runner wrapper (ensure it finds ansible-config in VENV)
MOLECULE := PATH=$(PATH) $(BIN)molecule

# Round 8: audit sink (+ Round 9 relay)
AUDIT_DIR := controller/audit
# Two env files: .env carries ports/versions/admin metadata; .secrets carries
# the machine-generated SEMAPHORE_API_TOKEN written by bootstrap.yml. Both
# are gitignored. manifest-sync ensures .secrets exists as a stub before any
# compose action touches it.
CONTROLLER_SECRETS := $(CONTROLLER_DIR)/.secrets
AUDIT_COMPOSE := docker compose -f $(AUDIT_DIR)/docker-compose.yml --env-file $(CONTROLLER_ENV) --env-file $(CONTROLLER_SECRETS)
AUDIT_CONTAINER := ansispire-audit-sink
CONTROLLER_NET := controller-net

# ── Help ─────────────────────────────────────────────────────────────────────
help: ## Show this help (auto-generated from each target's doc comment)
	@awk 'BEGIN {FS = ":.*?## "; printf "Available targets:\n\n"} \
	  /^[a-zA-Z][a-zA-Z0-9_-]*:.*?## / {printf "  \033[36m%-26s\033[0m %s\n", $$1, $$2}' \
	  $(MAKEFILE_LIST)

# ── Bootstrap ────────────────────────────────────────────────────────────────
setup: ## Bootstrap full dev environment (venv + Paths + Dependencies + Galaxy)
	@bash scripts/bootstrap.sh

install: ## Install Galaxy dependencies only (roles + collections)
	$(BIN)ansible-galaxy role install -r requirements.yml --force
	$(BIN)ansible-galaxy collection install -r requirements.yml --force

# ── Code quality ─────────────────────────────────────────────────────────────
lint: yamllint ansible-lint ## Run YAML + Ansible lint

yamllint: ## Run yamllint
	$(BIN)yamllint .

ansible-lint: ## Run ansible-lint
	$(BIN)ansible-lint --profile production

syntax: ## Syntax check both stag and prod
	@echo "==> Syntax checking Stag..."
	$(BIN)ansible-playbook playbooks/site.yml --syntax-check -i inventory/stag
	@echo "==> Syntax checking Prod..."
	$(BIN)ansible-playbook playbooks/site.yml --syntax-check -i inventory/prod

verify: lint syntax vps-manager-syntax detect-secrets test-eda test-filters test-vps-manager dry-run ## Push gate — lint + syntax + secrets + Python tests + dry-run (~30–60 s)

verify-quick: syntax ## Save-point gate — syntax only (~3 s, before commit)

verify-full: verify molecule-all ## Release gate — verify + all 4 molecule scenarios serial (~10–20 min)

# ── Tests ────────────────────────────────────────────────────────────────────
test: ## Run default Molecule scenario (common)
	$(MOLECULE) test -s common

molecule-all: ## Run all Molecule scenarios
	$(MOLECULE) test -s common
	$(MOLECULE) test -s webserver
	$(MOLECULE) test -s database
	$(MOLECULE) test -s full-stack

# ── EDA test pyramid (no docker, no external deps) ───────────────────────────
# Specs in docs/reference/test-specs/eda-{reactor-unit,rules-contract,reactor-component}.md
test-eda-unit: ## L1 — reactor pure-Python (match_rule, cooldown, process_event)
	$(BIN)python3 controller/audit/test_reactor.py

test-eda-contract: ## L2 — rules.json ↔ bootstrap.yml template-name contract (PyYAML)
	$(BIN)python3 controller/audit/test_rules_contract.py

test-eda-component: ## L3 — reactor → mock Semaphore HTTP request contract
	$(BIN)python3 controller/audit/test_reactor_component.py

test-eda-relay-unit: ## L1 — relay.py cursor/fetch/tick (urllib mocked)
	$(BIN)python3 controller/audit/test_relay.py

test-eda-sink-unit: ## L1 — sink.py HTTP handler (socket/wfile mocked)
	$(BIN)python3 controller/audit/test_sink.py

test-eda: test-eda-unit test-eda-contract test-eda-component test-eda-relay-unit test-eda-sink-unit ## All EDA tests (L1+L2+L3); no docker

test-eda-e2e: ## L4 — disposable end-to-end (real docker; ~60–90s; NOT in `make verify`)
	@bash controller/audit/e2e/run.sh

test-filters: ## L1 — filter_plugins/custom_filters.py (pure functions, no Ansible)
	$(BIN)python3 controller/audit/test_filters.py

test-vps-manager: ## L1 — plugins/vps_manager local lifecycle tests
	$(BIN)python3 plugins/vps_manager/tests/test_vps_manager.py

vps-manager-syntax: ## Ansible syntax-check for VPS Manager action playbooks
	$(BIN)ansible-playbook plugins/vps_manager/playbooks/onboard.yml --syntax-check -i plugins/vps_manager/tests/syntax_inventory.yml
	$(BIN)ansible-playbook plugins/vps_manager/playbooks/modify.yml --syntax-check -i plugins/vps_manager/tests/syntax_inventory.yml
	$(BIN)ansible-playbook plugins/vps_manager/playbooks/audit.yml --syntax-check -i plugins/vps_manager/tests/syntax_inventory.yml
	$(BIN)ansible-playbook plugins/vps_manager/playbooks/remove.yml --syntax-check -i plugins/vps_manager/tests/syntax_inventory.yml
	$(BIN)ansible-playbook plugins/vps_manager/playbooks/docker_host.yml --syntax-check -i plugins/vps_manager/tests/syntax_inventory.yml
	$(BIN)ansible-playbook plugins/vps_manager/playbooks/deploy_compose.yml --syntax-check -i plugins/vps_manager/tests/syntax_inventory.yml

detect-secrets: ## Scan tracked + unignored files; fail on findings not present in .secrets.baseline
	@PATH="$(VENV_BIN):$$PATH" $(BIN)python3 scripts/detect_secrets_gate.py

# ── VPS Manager plugin ──────────────────────────────────────────────────────
vps-new: ## Interactively create a VPS onboarding task draft
	$(BIN)python3 -m plugins.vps_manager.cli new

vps-recover: ## Interactively create a VPS recovery task draft for an existing alias: make vps-recover ALIAS=...
	$(BIN)python3 -m plugins.vps_manager.cli recover $(if $(VPS_RECOVER_ALIAS),--alias '$(VPS_RECOVER_ALIAS)')

vps-submit: ## Submit a VPS Manager draft: make vps-submit ALIAS=... or FILE=...
	@test -n "$(VPS_SUBMIT_SELECTOR)" || { echo "Usage: make vps-submit ALIAS=<alias> | make vps-submit FILE=runtime/inbox/vps/drafts/<draft>.yml" >&2; exit 2; }
	$(BIN)python3 -m plugins.vps_manager.cli submit '$(VPS_SUBMIT_SELECTOR)'

vps-tasks: ## List VPS Manager task files by state
	$(BIN)python3 -m plugins.vps_manager.cli tasks

vps-manager-init: ## Create VPS Manager runtime directories
	$(BIN)python3 plugins/vps_manager/vps_manager.py init

vps-manager-process: ## Process stable VPS task YAML files from runtime/inbox/vps/pending
	$(BIN)python3 plugins/vps_manager/vps_manager.py process

vps-manager-validate: ## Validate a VPS Manager task file: make vps-manager-validate FILE=...
	@test -n "$(FILE)" || { echo "Usage: make vps-manager-validate FILE=<task.yml>" >&2; exit 2; }
	$(BIN)python3 plugins/vps_manager/vps_manager.py validate $(FILE)

# ── Deploy ───────────────────────────────────────────────────────────────────
dry-run: ## Dry-run (--check; common baseline against hub_local — layered hosts.ini + dev vars)
	# Layered inventory:
	#   - inventory/hosts.ini provides the [hub_local] group (control_node)
	#   - inventory/dev provides the [all] group_vars (system_timezone, etc.)
	# --limit hub_local scopes to control_node only. The webservers/dbservers
	# plays match no hosts (control_node is in neither) and skip cleanly,
	# avoiding "service not installed locally" failures.
	$(BIN)ansible-playbook playbooks/site.yml --check --diff --connection=local \
	  -i inventory/hosts.ini -i inventory/dev --limit hub_local \
	  -e "ansible_python_interpreter=$(shell which python3)"

# Hub deploy — Path A (Ansible role-based). HUB_NODE selects scope:
#   make hub-deploy HUB_NODE=local      → only the workstation (hub_local)
#   make hub-deploy HUB_NODE=remote     → only the remote VPS (hub_remote)
#   make hub-deploy HUB_NODE=all        → both
# VAULT_PASSWORD_FILE overridable; defaults to .vault_pass (gitignored).
HUB_INVENTORY := inventory/hosts.ini
HUB_PLAYBOOK  := playbooks/deploy_hub.yml
HUB_NODE      ?= local
VAULT_PASSWORD_FILE ?= .vault_pass
ifeq ($(HUB_NODE),local)
  HUB_LIMIT := --limit hub_local
else ifeq ($(HUB_NODE),remote)
  HUB_LIMIT := --limit hub_remote
else ifeq ($(HUB_NODE),all)
  HUB_LIMIT :=
else
  $(error HUB_NODE must be one of: local, remote, all (got: $(HUB_NODE)))
endif
HUB_ANSIBLE := $(BIN)ansible-playbook $(HUB_PLAYBOOK) -i $(HUB_INVENTORY) $(HUB_LIMIT) --vault-password-file $(VAULT_PASSWORD_FILE)

hub-deploy: ## Deploy hub via Path A (HUB_NODE=local|remote|all; default local)
	@test -f $(VAULT_PASSWORD_FILE) || { echo "Missing $(VAULT_PASSWORD_FILE); create it (chmod 600) or pass VAULT_PASSWORD_FILE=..."; exit 1; }
	$(HUB_ANSIBLE) --diff

hub-deploy-check: ## Dry-run hub deploy (--check --diff; same HUB_NODE= selection)
	@test -f $(VAULT_PASSWORD_FILE) || { echo "Missing $(VAULT_PASSWORD_FILE); create it (chmod 600) or pass VAULT_PASSWORD_FILE=..."; exit 1; }
	$(HUB_ANSIBLE) --check --diff

# ── Target deploy — apply infra_baseline to managed VPS (TASK-007). ───────────
#   make target-deploy TARGET_NODE=debian          → --limit targets_debian
#   make target-deploy TARGET_NODE=rhel            → --limit targets_rhel
#   make target-deploy TARGET_NODE=all             → no --limit (entire targets group)
#   make target-deploy TARGET_NODE=rocky9          → --limit rocky9 (single alias)
#   make target-deploy TARGET_NODE=rocky9 ANSIBLE_USER=root   → fresh-host bootstrap
#                                                              before role creates
#                                                              the `ansible` user

TARGET_INVENTORY := inventory/hosts.ini
TARGET_PLAYBOOK  := playbooks/deploy_target.yml
TARGET_NODE      ?= all
ANSIBLE_USER     ?=

ifeq ($(TARGET_NODE),debian)
  TARGET_LIMIT := --limit targets_debian
else ifeq ($(TARGET_NODE),rhel)
  TARGET_LIMIT := --limit targets_rhel
else ifeq ($(TARGET_NODE),all)
  TARGET_LIMIT :=
else
  # Treat anything else as a single-host alias; ansible will fail clearly
  # if the alias doesn't exist in inventory.
  TARGET_LIMIT := --limit $(TARGET_NODE)
endif

ifneq ($(ANSIBLE_USER),)
  TARGET_USER_OVERRIDE := -e ansible_user=$(ANSIBLE_USER)
else
  TARGET_USER_OVERRIDE :=
endif

TARGET_ANSIBLE := $(BIN)ansible-playbook $(TARGET_PLAYBOOK) -i $(TARGET_INVENTORY) $(TARGET_LIMIT) $(TARGET_USER_OVERRIDE)

target-deploy: ## Apply infra_baseline to managed targets (TARGET_NODE=debian|rhel|all|<alias>; ANSIBLE_USER=root for fresh-host bootstrap)
	$(TARGET_ANSIBLE) --diff

target-deploy-check: ## Dry-run target deploy (--check --diff; same TARGET_NODE= + ANSIBLE_USER= selection)
	$(TARGET_ANSIBLE) --check --diff

target-ping: ## Quick connectivity check to all managed targets (no role applied)
	$(BIN)ansible-playbook playbooks/ping_targets.yml -i $(TARGET_INVENTORY)

deploy-dev-check: ## Dry-run Dev deploy (--check --diff)
	$(BIN)ansible-playbook playbooks/site.yml -i inventory/dev --check --diff

deploy-dev: ## Deploy to Dev (local machine, full stack)
	$(BIN)ansible-playbook playbooks/site.yml -i inventory/dev --diff

deploy-stag: ## Deploy to Stag
	ANSIBLE_HOST_KEY_CHECKING=False $(BIN)ansible-playbook playbooks/site.yml -i inventory/stag --diff

deploy-prod: ## Deploy to Prod (requires confirmation)
	@read -p "Deploy to PROD? [y/N] " ans && [ $${ans:-N} = y ]
	$(BIN)ansible-playbook playbooks/site.yml -i inventory/prod --diff

tags: ## Run only tasks with the given tag, e.g. make tags TAGS=nginx
	$(BIN)ansible-playbook playbooks/site.yml --tags "$(TAGS)"

# ── Execution Environment ────────────────────────────────────────────────────
ee-build: ## Build the Execution Environment container image
	$(BIN)ansible-builder build -t ansispire-ee:latest -f execution-environment.yml -v3

navigator: ## Run via ansible-navigator (EE mode)
	$(BIN)ansible-navigator run playbooks/site.yml

navigator-local: ## Run via ansible-navigator (local mode, no EE)
	$(BIN)ansible-navigator run playbooks/site.yml --ee false

# ── Vault ────────────────────────────────────────────────────────────────────
vault-edit: ## Edit an encrypted file, e.g. make vault-edit FILE=inventory/local/vault.yml
	$(BIN)ansible-vault edit $(FILE)

vault-encrypt: ## Encrypt a single variable value
	$(BIN)ansible-vault encrypt_string --ask-vault-pass

# ── Control plane (Semaphore) ────────────────────────────────────────────────
controller-net: ## Ensure the shared control-plane docker network exists
	@docker network inspect $(CONTROLLER_NET) >/dev/null 2>&1 || \
		docker network create $(CONTROLLER_NET) >/dev/null

manifest-sync: ## Render config/manifest.yml (ports + image tags) into controller/semaphore/.env (managed block only)
	$(BIN)ansible-playbook playbooks/manifest_sync.yml

ports-sync: manifest-sync ## (deprecated alias for manifest-sync; will be removed next round)

controller-up: controller-net manifest-sync ## Start Semaphore control plane (auto-renders manifest into .env)
	@test -f $(CONTROLLER_ENV) || { echo "Missing $(CONTROLLER_ENV); run: cp $(CONTROLLER_DIR)/.env.example $(CONTROLLER_ENV) && vim $(CONTROLLER_ENV)"; exit 1; }
	$(CONTROLLER_COMPOSE) up -d
	@PORT=$$(grep '^SEMAPHORE_PORT=' $(CONTROLLER_ENV) | cut -d= -f2); echo "==> Semaphore starting at: http://localhost:$${PORT:-3300}"

controller-down: ## Stop Semaphore (keep data)
	$(CONTROLLER_COMPOSE) down

controller-logs: ## Tail Semaphore logs
	$(CONTROLLER_COMPOSE) logs -f semaphore

controller-reset: ## Stop and wipe Semaphore data (!! deletes all project/job history !!)
	@read -p "Really delete all control-plane data? [y/N] " ans && [ $${ans:-N} = y ]
	$(CONTROLLER_COMPOSE) down -v

controller-bootstrap: manifest-sync ## Bootstrap Semaphore project/inventory/template + mint API token (incl. Round 8 RBAC)
	@test -f $(CONTROLLER_ENV) || { echo "Missing $(CONTROLLER_ENV)"; exit 1; }
	$(BIN)ansible-playbook $(CONTROLLER_DIR)/bootstrap.yml \
		-e semaphore_user=$$(grep '^SEMAPHORE_ADMIN=' $(CONTROLLER_ENV) | cut -d= -f2) \
		-e semaphore_password=$$(grep '^SEMAPHORE_ADMIN_PASSWORD=' $(CONTROLLER_ENV) | cut -d= -f2)

# ── Round 8: audit sink ──────────────────────────────────────────────────────
controller-audit-up: controller-net ## Start audit sink + Round 9 polling relay
	$(AUDIT_COMPOSE) up -d
	@echo "==> audit-sink listening at http://127.0.0.1:3010/event"
	@echo "==> audit-relay polling Semaphore /api/events → sink"

controller-audit-down: ## Stop the audit sink (volume preserved)
	$(AUDIT_COMPOSE) down

controller-audit-tail: ## Tail the audit JSONL stream
	docker exec -it $(AUDIT_CONTAINER) tail -F /var/log/semaphore/events.jsonl

controller-audit-stats: ## Count audit events by path (requires jq in the container)
	@docker exec $(AUDIT_CONTAINER) sh -c '\
		which jq >/dev/null 2>&1 || apk add --no-cache jq >/dev/null; \
		jq -r ".path" /var/log/semaphore/events.jsonl 2>/dev/null | sort | uniq -c'

# ── Round 8: RBAC smoke test (no ansible-playbook needed) ────────────────────
controller-rbac-smoke: ## Verify RBAC demo: guest-403, task_runner can run but not edit, owner can do both
	@bash controller/rbac/smoke.sh

# ── Round 9: control-plane loop smoke ────────────────────────────────────────
controller-loop-smoke: ## Verify Semaphore action → relay → audit JSONL (≤20s)
	@bash controller/audit/loop-smoke.sh

# ── Utilities ────────────────────────────────────────────────────────────────
ping: ## Test connectivity to all hosts
	$(BIN)ansible all -m ansible.builtin.ping

clean: ## Clean temp files and caches
	rm -rf $(VENV_NAME) .cache/ .molecule/ __pycache__/ *.egg-info/
	find . -name "*.pyc" -delete
	find . -name "*.retry" -delete
	@echo "Cleanup done"
