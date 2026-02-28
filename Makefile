# ============================================================
# OpenClaw Multi-Agent Stack — Makefile
# ============================================================

SHELL := /bin/bash
STACK_DIR := $(shell cd "$(dir $(lastword $(MAKEFILE_LIST)))" && pwd)
OPENCLAW_HOME := $(HOME)/.openclaw

.PHONY: help setup status logs teardown backup restore new-agent restart

# Default target
help:
	@echo "OpenClaw Multi-Agent Stack"
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@echo "  Deployment:"
	@echo "    setup            Full bootstrap (first-time install)"
	@echo "    setup-openviking Setup OpenViking separately"
	@echo "    config           Regenerate openclaw.json from .env"
	@echo "    teardown         Remove all services (keeps data)"
	@echo ""
	@echo "  Operations:"
	@echo "    status           Check all services & subsystems"
	@echo "    logs             Tail recent gateway logs"
	@echo "    logs-follow      Stream gateway logs in real-time"
	@echo "    restart          Restart gateway service"
	@echo "    backup           Backup config and workspaces"
	@echo "    restore          Restore from latest backup"
	@echo ""
	@echo "  Observer Pipeline:"
	@echo "    collect          Run collection (23% sampling)"
	@echo "    collect-full     Run collection (all sources)"
	@echo "    daily            Generate daily briefing"
	@echo "    briefing         Push morning briefing via Telegram"
	@echo ""
	@echo "  Knowledge Base:"
	@echo "    sync             Sync agent memory to OpenViking"
	@echo "    ingest           Batch index all knowledge"
	@echo "    search q=\"...\"   Semantic search in knowledge base"
	@echo ""
	@echo "  Agent Development:"
	@echo "    new-agent        Scaffold a new agent (interactive)"
	@echo ""

# Full bootstrap
setup:
	@chmod +x $(STACK_DIR)/bootstrap.sh
	@chmod +x $(STACK_DIR)/config/generate-config.sh
	@chmod +x $(STACK_DIR)/launchd/install.sh
	@chmod +x $(STACK_DIR)/launchd/uninstall.sh
	@chmod +x $(STACK_DIR)/new-agent.sh
	@chmod +x $(STACK_DIR)/scripts/*.sh $(STACK_DIR)/scripts/*.py 2>/dev/null || true
	@$(STACK_DIR)/bootstrap.sh

# Check all services
status:
	@bash $(STACK_DIR)/scripts/status-check.sh

# View logs
logs:
	@echo "=== Gateway (last 50 lines) ==="
	@tail -50 $(OPENCLAW_HOME)/logs/gateway.log 2>/dev/null || echo "(no log file)"
	@echo ""
	@echo "=== Gateway Errors (last 20 lines) ==="
	@tail -20 $(OPENCLAW_HOME)/logs/gateway.err.log 2>/dev/null || echo "(no error log)"

logs-follow:
	@tail -f $(OPENCLAW_HOME)/logs/gateway.log

# Restart gateway
restart:
	@echo "Restarting OpenClaw Gateway..."
	@launchctl kickstart -k gui/$$(id -u)/ai.openclaw.gateway 2>/dev/null || \
		(launchctl unload ~/Library/LaunchAgents/ai.openclaw.gateway.plist 2>/dev/null; \
		 launchctl load ~/Library/LaunchAgents/ai.openclaw.gateway.plist)
	@sleep 2
	@pgrep -f "openclaw.*gateway" > /dev/null && echo "OK: Gateway restarted" || echo "WARN: Gateway may not have started"

# Backup
backup:
	@BACKUP_DIR="$(OPENCLAW_HOME)/backups/$$(date '+%Y%m%d-%H%M%S')"; \
	mkdir -p "$$BACKUP_DIR"; \
	cp -p $(OPENCLAW_HOME)/openclaw.json "$$BACKUP_DIR/" 2>/dev/null || true; \
	for ws in workspace workspace-observer; do \
		if [[ -d "$(OPENCLAW_HOME)/$$ws" ]]; then \
			tar -czf "$$BACKUP_DIR/$$ws.tar.gz" -C "$(OPENCLAW_HOME)" "$$ws" 2>/dev/null; \
		fi; \
	done; \
	echo "Backup saved to: $$BACKUP_DIR"; \
	ls -lh "$$BACKUP_DIR/"

# Restore from latest backup
restore:
	@LATEST=$$(ls -d $(OPENCLAW_HOME)/backups/*/ 2>/dev/null | sort -r | head -1); \
	if [[ -z "$$LATEST" ]]; then \
		echo "No backup found."; \
		exit 1; \
	fi; \
	echo "Restoring from: $$LATEST"; \
	cp -p "$$LATEST/openclaw.json" $(OPENCLAW_HOME)/ 2>/dev/null || true; \
	for ws in workspace workspace-observer; do \
		if [[ -f "$$LATEST/$$ws.tar.gz" ]]; then \
			tar -xzf "$$LATEST/$$ws.tar.gz" -C "$(OPENCLAW_HOME)/"; \
			echo "  Restored: $$ws"; \
		fi; \
	done; \
	echo "Restore complete. Restart gateway: make restart"

# Teardown (remove services, keep data)
teardown:
	@echo "Removing all LaunchAgents..."
	@bash $(STACK_DIR)/launchd/uninstall.sh
	@echo ""
	@echo "Services removed. Data preserved at $(OPENCLAW_HOME)"
	@echo "To fully remove, run: rm -rf $(OPENCLAW_HOME)"

# Scaffold new agent (interactive)
new-agent:
	@read -p "Agent ID (lowercase, e.g. arbiter): " id; \
	read -p "Agent Name (e.g. Arbiter): " name; \
	read -p "Agent Emoji (e.g. ⚖️): " emoji; \
	read -p "Agent Theme (e.g. strategic advisor): " theme; \
	$(STACK_DIR)/new-agent.sh "$$id" "$$name" "$$emoji" "$$theme"

# Regenerate config from .env
config:
	@bash $(STACK_DIR)/config/generate-config.sh

# Run Observer collection manually
collect:
	@echo "Running Observer collection..."
	@cd $(OPENCLAW_HOME)/workspace-observer/scripts && python3 collect.py

# Run Observer collection (full, no sampling)
collect-full:
	@cd $(OPENCLAW_HOME)/workspace-observer/scripts && python3 collect.py --full

# Generate daily briefing
daily:
	@cd $(OPENCLAW_HOME)/workspace-observer/scripts && python3 daily.py

# Run morning briefing
briefing:
	@bash $(OPENCLAW_HOME)/scripts/morning-briefing.sh

# Run memory sync to OpenViking
sync:
	@cd $(HOME)/projects/openviking-local && source .venv/bin/activate && python memory-sync.py

# Run batch ingest to OpenViking
ingest:
	@cd $(HOME)/projects/openviking-local && source .venv/bin/activate && python ingest.py

# Search OpenViking (usage: make search q="AI Agent")
search:
	@$(HOME)/projects/openviking-local/ov-search.sh "$(q)"

# Setup OpenViking separately
setup-openviking:
	@bash $(STACK_DIR)/openviking/setup.sh
