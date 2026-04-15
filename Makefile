# Makefile — common command wrappers; reduces memorization overhead
# Usage: make <target>
# List all available commands: make help

.DEFAULT_GOAL := help

.PHONY: help setup install lint syntax test molecule-all dry-run \
        deploy-staging deploy-prod tags ping vault-edit vault-encrypt \
        ee-build navigator clean \
        controller-up controller-down controller-logs controller-reset \
        controller-bootstrap \
        controller-audit-up controller-audit-down \
        controller-audit-tail controller-audit-stats \
        controller-rbac-smoke

# Control-plane compose command wrapper
CONTROLLER_DIR := controller/semaphore
CONTROLLER_ENV := $(CONTROLLER_DIR)/.env
CONTROLLER_COMPOSE := docker compose -f $(CONTROLLER_DIR)/docker-compose.yml --env-file $(CONTROLLER_ENV)

# Round 8: audit sink
AUDIT_DIR := controller/audit
AUDIT_COMPOSE := docker compose -f $(AUDIT_DIR)/docker-compose.yml
AUDIT_CONTAINER := ansible-demo-audit-sink

# ── Help ─────────────────────────────────────────────────────────────────────
help: ## Show all available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Bootstrap ────────────────────────────────────────────────────────────────
setup: ## Bootstrap full dev environment (Python deps + Galaxy + pre-commit)
	@echo "==> Installing Python dependencies..."
	@if command -v uv > /dev/null 2>&1; then \
		uv sync --extra all; \
	else \
		pip install -e ".[all]"; \
	fi
	@echo "==> Installing Ansible Galaxy dependencies..."
	ansible-galaxy role install -r requirements.yml --force
	ansible-galaxy collection install -r requirements.yml --force
	@echo "==> Configuring pre-commit hooks..."
	pre-commit install
	@echo "==> Dev environment ready"

install: ## Install Galaxy dependencies only (roles + collections)
	ansible-galaxy role install -r requirements.yml --force
	ansible-galaxy collection install -r requirements.yml --force

# ── Code quality ─────────────────────────────────────────────────────────────
lint: ## Run ansible-lint
	ansible-lint --profile production

syntax: ## Syntax check (does not execute)
	ansible-playbook playbooks/site.yml --syntax-check

# ── Tests ────────────────────────────────────────────────────────────────────
test: ## Run default Molecule scenario (common)
	molecule test -s common

molecule-all: ## Run all Molecule scenarios
	molecule test -s common
	molecule test -s webserver
	molecule test -s database

# ── Deploy ───────────────────────────────────────────────────────────────────
dry-run: ## Dry-run (--check mode, no actual changes)
	ansible-playbook playbooks/site.yml --check --diff

deploy-staging: ## Deploy to Staging
	ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook playbooks/site.yml -i inventory/staging --diff

deploy-prod: ## Deploy to Production (requires confirmation)
	@read -p "Deploy to PRODUCTION? [y/N] " ans && [ $${ans:-N} = y ]
	ansible-playbook playbooks/site.yml -i inventory/production --diff

tags: ## Run only tasks with the given tag, e.g. make tags TAGS=nginx
	ansible-playbook playbooks/site.yml --tags "$(TAGS)"

# ── Execution Environment ────────────────────────────────────────────────────
ee-build: ## Build the Execution Environment container image
	ansible-builder build -t ansible-demo-ee:latest -f execution-environment.yml -v3

navigator: ## Run via ansible-navigator (EE mode)
	ansible-navigator run playbooks/site.yml

navigator-local: ## Run via ansible-navigator (local mode, no EE)
	ansible-navigator run playbooks/site.yml --ee false

# ── Vault ────────────────────────────────────────────────────────────────────
vault-edit: ## Edit an encrypted file, e.g. make vault-edit FILE=inventory/production/group_vars/all/vault.yml
	ansible-vault edit $(FILE)

vault-encrypt: ## Encrypt a single variable value
	ansible-vault encrypt_string --ask-vault-pass

# ── Control plane (Semaphore) ────────────────────────────────────────────────
controller-up: ## Start Semaphore control plane (create controller/semaphore/.env first)
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
	ansible-playbook $(CONTROLLER_DIR)/bootstrap.yml \
		-e semaphore_url=http://localhost:$$(grep '^SEMAPHORE_PORT' $(CONTROLLER_ENV) | cut -d= -f2 | grep -o '[0-9]*' || echo 3000) \
		-e semaphore_user=$$(grep '^SEMAPHORE_ADMIN=' $(CONTROLLER_ENV) | cut -d= -f2) \
		-e semaphore_password=$$(grep '^SEMAPHORE_ADMIN_PASSWORD=' $(CONTROLLER_ENV) | cut -d= -f2)

# ── Round 8: audit sink ──────────────────────────────────────────────────────
controller-audit-up: ## Start the Round 8 audit sink (loopback port 3010)
	$(AUDIT_COMPOSE) up -d
	@echo "==> audit-sink listening at http://127.0.0.1:3010/event"

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

# ── Utilities ────────────────────────────────────────────────────────────────
ping: ## Test connectivity to all hosts
	ansible all -m ansible.builtin.ping

clean: ## Clean temp files and caches
	rm -rf .cache/ .molecule/ __pycache__/ *.egg-info/
	find . -name "*.pyc" -delete
	find . -name "*.retry" -delete
	@echo "Cleanup done"
