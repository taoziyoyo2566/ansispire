# Makefile — 常用命令封装，降低记忆负担
# 使用方式: make <target>

.PHONY: help install lint test deploy-staging deploy-prod check dry-run

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## 安装所有依赖 (roles + collections)
	ansible-galaxy role install -r requirements.yml --force
	ansible-galaxy collection install -r requirements.yml --force

lint: ## 运行 ansible-lint 检查
	ansible-lint playbooks/site.yml

syntax: ## 语法检查（不执行）
	ansible-playbook playbooks/site.yml --syntax-check

dry-run: ## Dry-run（--check 模式，不实际变更）
	ansible-playbook playbooks/site.yml --check --diff

deploy-staging: ## 部署到 Staging 环境
	ansible-playbook playbooks/site.yml -i inventory/staging --diff

deploy-prod: ## 部署到 Production（需二次确认）
	@read -p "Deploy to PRODUCTION? [y/N] " ans && [ $${ans:-N} = y ]
	ansible-playbook playbooks/site.yml -i inventory/production --diff

tags: ## 仅运行带指定标签的任务，例: make tags TAGS=nginx
	ansible-playbook playbooks/site.yml --tags "$(TAGS)"

vault-edit: ## 编辑加密文件，例: make vault-edit FILE=inventory/production/group_vars/all/vault.yml
	ansible-vault edit $(FILE)

vault-encrypt: ## 加密一个变量值
	ansible-vault encrypt_string --ask-vault-pass

ping: ## 测试所有主机连通性
	ansible all -m ansible.builtin.ping
