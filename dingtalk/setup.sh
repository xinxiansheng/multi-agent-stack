#!/bin/bash
# ============================================================
# DingTalk Bridge — Setup Script
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
STACK_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$STACK_DIR/.env"
BRIDGE_DIR="$HOME/.openclaw/dingtalk-bridge"

GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'
log() { echo -e "${GREEN}[OK]${NC} $1"; }
step() { echo -e "\n${CYAN}=== $1 ===${NC}"; }

step "DingTalk Bridge Setup"

# Load .env
if [[ -f "$ENV_FILE" ]]; then
    set -a; source "$ENV_FILE"; set +a
fi

# Check if DingTalk is enabled
if [[ "${DINGTALK_ENABLED:-false}" != "true" ]]; then
    echo "DingTalk bridge is not enabled."
    echo "Set DINGTALK_ENABLED=true in .env to enable."
    exit 0
fi

# Create directory
mkdir -p "$BRIDGE_DIR"
log "Directory: $BRIDGE_DIR"

# Create venv
if [[ ! -d "$BRIDGE_DIR/.venv" ]]; then
    python3 -m venv "$BRIDGE_DIR/.venv"
    log "Virtual environment created"
fi

# Install deps
source "$BRIDGE_DIR/.venv/bin/activate"
pip install -q -r "$SCRIPT_DIR/requirements.txt"
log "Dependencies installed"
deactivate

# Copy bridge script
cp "$SCRIPT_DIR/bridge.py" "$BRIDGE_DIR/bridge.py"
chmod +x "$BRIDGE_DIR/bridge.py"
log "bridge.py deployed"

step "DingTalk Bridge Setup Complete"
echo ""
echo "  Bridge: $BRIDGE_DIR/bridge.py"
echo ""
echo "  Required environment variables:"
echo "    DINGTALK_APP_KEY     — DingTalk enterprise app key"
echo "    DINGTALK_APP_SECRET  — DingTalk enterprise app secret"
echo "    GATEWAY_AUTH_TOKEN   — OpenClaw Gateway auth token"
echo ""
echo "  To start manually:"
echo "    source $BRIDGE_DIR/.venv/bin/activate"
echo "    python $BRIDGE_DIR/bridge.py"
echo ""
echo "  Or install LaunchAgent for auto-start."
echo ""
