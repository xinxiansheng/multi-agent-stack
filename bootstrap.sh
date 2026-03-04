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
step "Step 1/12: Homebrew"

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
step "Step 2/12: Core Dependencies"

deps=(node python3 git envsubst)
brew_deps=(node python@3.13 git gettext)

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
step "Step 3/12: OpenClaw Framework"

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
step "Step 4/12: Directory Structure"

OPENCLAW_HOME="$HOME/.openclaw"
mkdir -p "$OPENCLAW_HOME"/{logs,scripts,shared,agents/main/agent,agents/observer/agent,agents/arbiter/agent}
mkdir -p "$OPENCLAW_HOME"/{workspace/memory,workspace-observer/memory,workspace-observer/archive/daily}
mkdir -p "$OPENCLAW_HOME"/{workspace-arbiter/memory,workspace-arbiter/decisions}
mkdir -p "$OPENCLAW_HOME"/{workspace-observer/scripts,workspace-observer/config}
mkdir -p "$OPENCLAW_HOME"/{openviking-data/viking,backups}
mkdir -p "$HOME"/{projects/openviking-local,.openviking}

log "Directory structure created at $OPENCLAW_HOME"

# ============================================================
# Step 5: Deploy agent workspaces
# ============================================================
step "Step 5/12: Agent Workspaces"

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

# Arbiter
for f in SOUL.md IDENTITY.md TOOLS.md AGENTS.md; do
    src="$SCRIPT_DIR/agents/arbiter/$f"
    dst="$OPENCLAW_HOME/workspace-arbiter/$f"
    if [[ -f "$dst" ]]; then
        warn "Skipping $dst (already exists)"
    elif [[ -f "$src" ]]; then
        cp "$src" "$dst"
        log "Arbiter: $f deployed"
    fi
done

# Initialize git in workspaces for version control
for ws in workspace workspace-observer workspace-arbiter; do
    if [[ ! -d "$OPENCLAW_HOME/$ws/.git" ]]; then
        (cd "$OPENCLAW_HOME/$ws" && git init -q && git add -A && git commit -q -m "Initial workspace setup")
        log "$ws: git initialized"
    fi
done

# ============================================================
# Step 6: Generate openclaw.json
# ============================================================
step "Step 6/12: Configuration"

bash "$SCRIPT_DIR/config/generate-config.sh"

# ============================================================
# Step 7: Deploy Observer Pipeline
# ============================================================
step "Step 7/12: Observer Pipeline"

# Deploy collection scripts
for script in collect.py daily.py requirements.txt; do
    src="$SCRIPT_DIR/observer/scripts/$script"
    dst="$OPENCLAW_HOME/workspace-observer/scripts/$script"
    if [[ -f "$src" ]]; then
        cp "$src" "$dst"
        chmod +x "$dst" 2>/dev/null || true
        log "Observer script: $script"
    fi
done

# Deploy config files
for cfg in sources.yaml web_sources.yaml interests.md scoring.md; do
    src="$SCRIPT_DIR/observer/config/$cfg"
    dst="$OPENCLAW_HOME/workspace-observer/config/$cfg"
    if [[ -f "$dst" ]]; then
        warn "Skipping $cfg (already exists)"
    elif [[ -f "$src" ]]; then
        cp "$src" "$dst"
        log "Observer config: $cfg"
    fi
done

# Install Python dependencies for Observer
if [[ -f "$OPENCLAW_HOME/workspace-observer/scripts/requirements.txt" ]]; then
    pip3 install -q -r "$OPENCLAW_HOME/workspace-observer/scripts/requirements.txt" 2>/dev/null || \
        warn "Failed to install Observer Python deps. Run manually: pip3 install feedparser pyyaml beautifulsoup4 requests"
    log "Observer Python dependencies"
fi

# ============================================================
# Step 8: Deploy OpenViking Knowledge Base
# ============================================================
step "Step 8/12: OpenViking Knowledge Base"

bash "$SCRIPT_DIR/openviking/setup.sh" || warn "OpenViking setup had issues. Run manually: ./openviking/setup.sh"

# ============================================================
# Step 9: DingTalk Bridge (Optional)
# ============================================================
step "Step 9/12: DingTalk Bridge (Optional)"

if [[ "${DINGTALK_ENABLED:-false}" == "true" ]]; then
    bash "$SCRIPT_DIR/dingtalk/setup.sh" || warn "DingTalk setup had issues."
else
    log "DingTalk bridge not enabled (set DINGTALK_ENABLED=true in .env)"
fi

# ============================================================
# Step 10: Deploy Shared State & Signal Loop
# ============================================================
step "Step 10/12: Shared State & Signal Loop"

# Shared STATE.yaml
if [[ ! -f "$OPENCLAW_HOME/shared/STATE.yaml" ]]; then
    cp "$SCRIPT_DIR/shared/STATE.yaml" "$OPENCLAW_HOME/shared/STATE.yaml"
    log "STATE.yaml deployed"
else
    warn "STATE.yaml already exists"
fi

# ============================================================
# Step 11: Deploy Scripts & Services
# ============================================================
step "Step 11/12: Scripts & Services"

# Copy operational scripts
for script in healthcheck.py logrotate.sh status-check.sh morning-briefing.sh; do
    src="$SCRIPT_DIR/scripts/$script"
    dst="$OPENCLAW_HOME/scripts/$script"
    if [[ -f "$src" ]]; then
        cp "$src" "$dst"
        chmod +x "$dst"
        log "Script: $script"
    fi
done

# Install LaunchAgents
bash "$SCRIPT_DIR/launchd/install.sh"

# ============================================================
# Step 11: Verification
# ============================================================
step "Step 11/11: Verification"

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
for ws in workspace workspace-arbiter workspace-observer; do
    if [[ -f "$OPENCLAW_HOME/$ws/SOUL.md" ]]; then
        log "$ws: SOUL.md present"
    else
        warn "$ws: SOUL.md missing"
    fi
done

# Check Observer pipeline
if [[ -f "$OPENCLAW_HOME/workspace-observer/scripts/collect.py" ]]; then
    log "Observer pipeline deployed"
fi

# Check OpenViking
if [[ -f "$HOME/projects/openviking-local/server.py" ]]; then
    log "OpenViking MCP server deployed"
fi

# Check shared state
if [[ -f "$OPENCLAW_HOME/shared/STATE.yaml" ]]; then
    log "Shared STATE.yaml deployed"
fi

# ============================================================
# Summary
# ============================================================
step "Bootstrap Complete!"

echo ""
echo "Your multi-agent system is deployed:"
echo ""
echo "  Agents:"
echo "    ⚡ Nexus    — Central dispatcher (default)"
echo "    ⚖️ Arbiter  — Strategic advisor + decision analysis"
echo "    👁️ Observer  — Intelligence analyst + collection pipeline"
echo ""
echo "  Infrastructure:"
echo "    Gateway:       http://127.0.0.1:${GATEWAY_PORT:-18789}"
echo "    OpenViking:    http://127.0.0.1:${OPENVIKING_PORT:-2033} (knowledge base)"
echo "    Dashboard:     http://127.0.0.1:${OPENVIKING_DASHBOARD_PORT:-2034}"
echo "    RSSHub:        http://127.0.0.1:${RSSHUB_PORT:-2035}"
echo ""
echo "  Subsystems:"
echo "    Collection:    Observer pipeline (every 4h)"
echo "    Daily Report:  Observer daily (21:00)"
echo "    Memory Sync:   OpenViking sync (23:30)"
echo "    Morning Brief: Nexus briefing (08:30)"
echo "    Health Check:  Every 30min"
echo "    Log Rotation:  Daily 03:00"
echo "    Shared State:  ~/.openclaw/shared/STATE.yaml"
echo ""
echo "  Next steps:"
echo "    1. Edit ~/.openclaw/workspace/USER.md with your profile"
echo "    2. Edit ~/.openclaw/workspace-observer/config/interests.md for your focus areas"
echo "    3. Edit ~/.openclaw/workspace-observer/config/sources.yaml for your RSS feeds"
echo "    4. Add more agents: ./new-agent.sh <id> <name> <emoji>"
echo "    5. Run initial knowledge index: cd ~/projects/openviking-local && python ingest.py"
echo ""
echo "  Useful commands:"
echo "    make status                    # Check all services"
echo "    make logs                      # View recent logs"
echo "    openclaw chat                  # Chat with Nexus"
echo "    openclaw chat --agent observer # Chat with Observer"
echo ""
