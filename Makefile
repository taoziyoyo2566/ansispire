# Makefile — common command wrappers; reduces memorization overhead
# Usage: make <target>
# List all available commands: make help

.DEFAULT_GOAL := help

.PHONY: help setup install lint syntax test molecule-all dry-run \
        deploy-staging deploy-prod tags ping vault-edit vault-encrypt \
        ee-build navigator clean \
        controller-net \
        controller-up controller-down controller-logs controller-reset \
        controller-bootstrap \
        controller-audit-up controller-audit-down \
        controller-audit-tail controller-audit-stats \
        controller-rbac-smoke \
        controller-loop-smoke

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

# Round 8: audit sink (+ Round 9 relay)
AUDIT_DIR := controller/audit
# Relay reads SEMAPHORE_ADMIN_PASSWORD from the Semaphore .env so both stacks
# stay in sync without duplicating secrets.
AUDIT_COMPOSE := docker compose -f $(AUDIT_DIR)/docker-compose.yml --env-file $(CONTROLLER_ENV)
AUDIT_CONTAINER := ansispire-audit-sink
CONTROLLER_NET := controller-net

# ── Bootstrap ────────────────────────────────────────────────────────────────
setup: ## Bootstrap full dev environment (venv + Paths + Dependencies + Galaxy)
	@bash scripts/bootstrap.sh

install: ## Install Galaxy dependencies only (roles + collections)
	$(BIN)ansible-galaxy role install -r requirements.yml --force
	$(BIN)ansible-galaxy collection install -r requirements.yml --force

# ── Code quality ─────────────────────────────────────────────────────────────
lint: ## Run ansible-lint
	$(BIN)ansible-lint --profile production

syntax: ## Syntax check (does not execute)
	$(BIN)ansible-playbook playbooks/site.yml --syntax-check

verify: lint syntax dry-run ## Run all CI-equivalent checks (lint + syntax + dry-run)

# ── Tests ────────────────────────────────────────────────────────────────────
test: ## Run default Molecule scenario (common)
	$(BIN)molecule test -s common

molecule-all: ## Run all Molecule scenarios
	$(BIN)molecule test -s common
	$(BIN)molecule test -s webserver
	$(BIN)molecule test -s database

# ── Deploy ───────────────────────────────────────────────────────────────────
dry-run: ## Dry-run (--check mode, no actual changes)
	$(BIN)ansible-playbook playbooks/site.yml --check --diff

deploy-staging: ## Deploy to Staging
	ANSIBLE_HOST_KEY_CHECKING=False $(BIN)ansible-playbook playbooks/site.yml -i inventory/staging --diff

deploy-prod: ## Deploy to Production (requires confirmation)
	@read -p "Deploy to PRODUCTION? [y/N] " ans && [ $${ans:-N} = y ]
	$(BIN)ansible-playbook playbooks/site.yml -i inventory/production --diff

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
vault-edit: ## Edit an encrypted file, e.g. make vault-edit FILE=inventory/production/group_vars/all/vault.yml
	$(BIN)ansible-vault edit $(FILE)

vault-encrypt: ## Encrypt a single variable value
	$(BIN)ansible-vault encrypt_string --ask-vault-pass

# ── Control plane (Semaphore) ────────────────────────────────────────────────
controller-net: ## Ensure the shared control-plane docker network exists
	@docker network inspect $(CONTROLLER_NET) >/dev/null 2>&1 || \
		docker network create $(CONTROLLER_NET) >/dev/null

controller-up: controller-net ## Start Semaphore control plane (create controller/semaphore/.env first)
	@test -f $(CONTROLLER_ENV) || { echo "Missing $(CONTROLLER_ENV); run: cp $(CONTROLLER_DIR)/.env.example $(CONTROLLER_ENV) && vim $(CONTROLLER_ENV)"; exit 1; }
	$(CONTROLLER_COMPOSE) up -d
	@PORT=$$(grep '^SEMAPHORE_PORT=' $(CONTROLLER_ENV) | cut -d= -f2); echo "==> Semaphore starting at: http://localhost:$${PORT:-3000}"

controller-down: ## Stop Semaphore (keep data)
	$(CONTROLLER_COMPOSE) down

controller-logs: ## Tail Semaphore logs
	$(CONTROLLER_COMPOSE) logs -f semaphore

controller-reset: ## Stop and wipe Semaphore data (!! deletes all project/job history !!)
	@read -p "Really delete all control-plane data? [y/N] " ans && [ $${ans:-N} = y ]
	$(CONTROLLER_COMPOSE) down -v

controller-bootstrap: ## Bootstrap Semaphore project/inventory/template via API (incl. Round 8 RBAC)
	@test -f $(CONTROLLER_ENV) || { echo "Missing $(CONTROLLER_ENV)"; exit 1; }
	$(BIN)ansible-playbook $(CONTROLLER_DIR)/bootstrap.yml \
		-e semaphore_url=http://localhost:$$(grep '^SEMAPHORE_PORT' $(CONTROLLER_ENV) | cut -d= -f2 | grep -o '[0-9]*' || echo 3000) \
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
