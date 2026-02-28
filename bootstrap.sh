#!/bin/bash
# ============================================================
# OpenClaw Multi-Agent Stack — One-Click Bootstrap
# ============================================================
# Usage:
#   1. cp .env.template .env && nano .env   (fill in your keys)
#   2. ./bootstrap.sh
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()  { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }
step() { echo -e "\n${CYAN}=== $1 ===${NC}"; }

# ============================================================
# Pre-flight checks
# ============================================================
step "Pre-flight Checks"

# macOS?
[[ "$(uname)" == "Darwin" ]] || err "This script only supports macOS."

# .env exists?
if [[ ! -f "$ENV_FILE" ]]; then
    err ".env not found. Please copy and fill in:\n  cp $SCRIPT_DIR/.env.template $SCRIPT_DIR/.env"
fi

set -a; source "$ENV_FILE"; set +a

# Check minimum required keys
if [[ -z "${ANTHROPIC_API_KEY:-}" && -z "${MINIMAX_API_KEY:-}" ]]; then
    warn "No AI model API key configured. You'll need at least one to use the system."
fi

log "macOS $(sw_vers -productVersion) detected"
log ".env loaded"

# ============================================================
# Step 1: Install Homebrew (if missing)
# ============================================================
step "Step 1/8: Homebrew"

if command -v brew &>/dev/null; then
    log "Homebrew already installed: $(brew --prefix)"
else
    echo "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    log "Homebrew installed"
fi

HOMEBREW_PREFIX="$(brew --prefix)"

# ============================================================
# Step 2: Install core dependencies
# ============================================================
step "Step 2/8: Core Dependencies"

deps=(node python3 git)
brew_deps=(node python@3.13 git)

for i in "${!deps[@]}"; do
    if command -v "${deps[$i]}" &>/dev/null; then
        log "${deps[$i]} already installed"
    else
        echo "Installing ${brew_deps[$i]}..."
        brew install "${brew_deps[$i]}"
        log "${brew_deps[$i]} installed"
    fi
done

# Optional: Tailscale
if command -v tailscale &>/dev/null; then
    log "Tailscale already installed"
else
    warn "Tailscale not installed. Install manually if you need remote access:"
    warn "  brew install tailscale"
fi

# ============================================================
# Step 3: Install OpenClaw
# ============================================================
step "Step 3/8: OpenClaw Framework"

if command -v openclaw &>/dev/null; then
    log "OpenClaw already installed: $(openclaw --version 2>/dev/null || echo 'installed')"
else
    echo "Installing OpenClaw..."
    npm install -g openclaw
    log "OpenClaw installed"
fi

# ============================================================
# Step 4: Initialize OpenClaw directory structure
# ============================================================
step "Step 4/8: Directory Structure"

OPENCLAW_HOME="$HOME/.openclaw"
mkdir -p "$OPENCLAW_HOME"/{logs,scripts,agents/main/agent,agents/observer/agent,workspace/memory,workspace-observer/memory,workspace-observer/archive,openviking-data,backups}

log "Directory structure created at $OPENCLAW_HOME"

# ============================================================
# Step 5: Deploy agent workspaces
# ============================================================
step "Step 5/8: Agent Workspaces"

# Nexus (main)
for f in SOUL.md IDENTITY.md TOOLS.md AGENTS.md HEARTBEAT.md USER.md; do
    src="$SCRIPT_DIR/agents/nexus/$f"
    dst="$OPENCLAW_HOME/workspace/$f"
    if [[ -f "$dst" ]]; then
        warn "Skipping $dst (already exists)"
    elif [[ -f "$src" ]]; then
        cp "$src" "$dst"
        log "Nexus: $f deployed"
    fi
done

# Observer
for f in SOUL.md IDENTITY.md TOOLS.md AGENTS.md; do
    src="$SCRIPT_DIR/agents/observer/$f"
    dst="$OPENCLAW_HOME/workspace-observer/$f"
    if [[ -f "$dst" ]]; then
        warn "Skipping $dst (already exists)"
    elif [[ -f "$src" ]]; then
        cp "$src" "$dst"
        log "Observer: $f deployed"
    fi
done

# Initialize git in workspaces for version control
for ws in workspace workspace-observer; do
    if [[ ! -d "$OPENCLAW_HOME/$ws/.git" ]]; then
        (cd "$OPENCLAW_HOME/$ws" && git init -q && git add -A && git commit -q -m "Initial workspace setup")
        log "$ws: git initialized"
    fi
done

# ============================================================
# Step 6: Generate openclaw.json
# ============================================================
step "Step 6/8: Configuration"

bash "$SCRIPT_DIR/config/generate-config.sh"

# ============================================================
# Step 7: Deploy scripts
# ============================================================
step "Step 7/8: Scripts & Services"

# Copy operational scripts
for script in healthcheck.py logrotate.sh; do
    src="$SCRIPT_DIR/scripts/$script"
    dst="$OPENCLAW_HOME/scripts/$script"
    if [[ -f "$src" ]]; then
        cp "$src" "$dst"
        chmod +x "$dst"
        log "Script: $script deployed"
    fi
done

# Install LaunchAgents
bash "$SCRIPT_DIR/launchd/install.sh"

# ============================================================
# Step 8: Verification
# ============================================================
step "Step 8/8: Verification"

echo "Running health checks..."

# Check Gateway
sleep 3
if pgrep -f "openclaw.*gateway" &>/dev/null; then
    log "Gateway is running"
else
    warn "Gateway may not have started yet. Check: launchctl list | grep openclaw"
fi

# Check config
if [[ -f "$OPENCLAW_HOME/openclaw.json" ]]; then
    log "openclaw.json exists ($(wc -c < "$OPENCLAW_HOME/openclaw.json") bytes)"
else
    err "openclaw.json not found!"
fi

# Check workspaces
for ws in workspace workspace-observer; do
    if [[ -f "$OPENCLAW_HOME/$ws/SOUL.md" ]]; then
        log "$ws: SOUL.md present"
    else
        warn "$ws: SOUL.md missing"
    fi
done

# ============================================================
# Summary
# ============================================================
step "Bootstrap Complete!"

echo ""
echo "Your multi-agent system is deployed:"
echo ""
echo "  Agents:"
echo "    ⚡ Nexus  — Central dispatcher (default)"
echo "    👁️ Observer — Intelligence analyst"
echo ""
echo "  Services:"
echo "    Gateway:     http://127.0.0.1:${GATEWAY_PORT:-18789}"
echo "    OpenViking:  port ${OPENVIKING_PORT:-2033} (if installed)"
echo ""
echo "  Next steps:"
echo "    1. Edit ~/.openclaw/workspace/USER.md with your profile"
echo "    2. Edit agents/observer/SOUL.md focus areas for your interests"
echo "    3. Add more agents: ./new-agent.sh <id> <name> <emoji>"
echo "    4. Check status: make status"
echo ""
echo "  Useful commands:"
echo "    openclaw chat                  # Chat with Nexus"
echo "    openclaw chat --agent observer # Chat with Observer"
echo "    make status                    # Check all services"
echo "    make logs                      # View recent logs"
echo ""
