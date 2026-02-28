#!/bin/bash
# ============================================================
# OpenViking Knowledge Base — Setup Script
# ============================================================
# Installs OpenViking (RAG semantic search) and configures
# MCP server, memory sync, dashboard, and CLI search.
#
# Prerequisites:
#   - Python 3.13+
#   - Volcengine API key (for embeddings)
#   - OpenClaw deployed
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
STACK_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$STACK_DIR/.env"

if [[ ! -f "$ENV_FILE" ]]; then
    echo "ERROR: .env not found. Run 'make setup' first."
    exit 1
fi

set -a; source "$ENV_FILE"; set +a

OPENCLAW_HOME="$HOME/.openclaw"
OV_PROJECT="$HOME/projects/openviking-local"
OV_DATA="$OPENCLAW_HOME/openviking-data"
OV_CONF="$HOME/.openviking"

GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'
log() { echo -e "${GREEN}[OK]${NC} $1"; }
step() { echo -e "\n${CYAN}=== $1 ===${NC}"; }

# ── Step 1: Create directories ────────────────────────────────
step "Step 1: Directories"
mkdir -p "$OV_PROJECT" "$OV_DATA" "$OV_CONF"
log "Directories created"

# ── Step 2: Create Python venv & install deps ─────────────────
step "Step 2: Python Environment"
if [[ ! -d "$OV_PROJECT/.venv" ]]; then
    python3 -m venv "$OV_PROJECT/.venv"
    log "Virtual environment created"
fi

source "$OV_PROJECT/.venv/bin/activate"
pip install -q openviking fastmcp uvicorn pyyaml
log "Dependencies installed"
deactivate

# ── Step 3: Generate config ───────────────────────────────────
step "Step 3: Configuration"

VOLCENGINE_API_KEY="${VOLCENGINE_API_KEY:-}"
VOLCENGINE_EMBED_MODEL="${VOLCENGINE_EMBED_MODEL:-}"
VOLCENGINE_VLM_MODEL="${VOLCENGINE_VLM_MODEL:-}"

if [[ -z "$VOLCENGINE_API_KEY" ]]; then
    echo "WARN: VOLCENGINE_API_KEY not set in .env"
    echo "  OpenViking needs Volcengine (ByteDance) for embeddings."
    echo "  Get an API key at: https://console.volcengine.com/"
    echo "  Then add to .env: VOLCENGINE_API_KEY=xxx"
fi

cat > "$OV_CONF/ov.conf" <<CONF
{
  "embedding": {
    "dense": {
      "api_base": "https://ark.cn-beijing.volces.com/api/v3",
      "api_key": "${VOLCENGINE_API_KEY}",
      "provider": "volcengine",
      "dimension": 1024,
      "model": "${VOLCENGINE_EMBED_MODEL}"
    }
  },
  "vlm": {
    "api_base": "https://ark.cn-beijing.volces.com/api/v3",
    "api_key": "${VOLCENGINE_API_KEY}",
    "provider": "volcengine",
    "model": "${VOLCENGINE_VLM_MODEL}"
  }
}
CONF
chmod 600 "$OV_CONF/ov.conf"
log "OpenViking config generated at $OV_CONF/ov.conf"

# ── Step 4: Deploy scripts ────────────────────────────────────
step "Step 4: Deploy Scripts"

for script in server.py memory-sync.py ingest.py ov-search.sh start-mcp.sh; do
    src="$SCRIPT_DIR/$script"
    dst="$OV_PROJECT/$script"
    if [[ -f "$src" ]]; then
        cp "$src" "$dst"
        chmod +x "$dst"
        log "$script deployed"
    fi
done

# ── Step 5: AGFS config ──────────────────────────────────────
step "Step 5: AGFS Config"
mkdir -p "$OV_DATA/.agfs"
cat > "$OV_DATA/.agfs/config.yaml" <<YAML
plugins:
  localfs:
    enabled: true
    path: /local
    config:
      local_dir: ${OV_DATA}/viking
  queuefs:
    enabled: true
    path: /queue
  serverinfofs:
    enabled: true
    path: /serverinfo
server:
  address: :1833
  log_level: warn
YAML
mkdir -p "$OV_DATA/viking"
log "AGFS config created"

# ── Step 6: Summary ──────────────────────────────────────────
step "OpenViking Setup Complete"
echo ""
echo "  MCP Server:  $OV_PROJECT/start-mcp.sh (port ${OPENVIKING_PORT:-2033})"
echo "  CLI Search:  $OV_PROJECT/ov-search.sh <query>"
echo "  Memory Sync: $OV_PROJECT/memory-sync.py (daily 23:30)"
echo "  Ingest:      $OV_PROJECT/ingest.py (one-time batch index)"
echo ""
echo "  To start MCP server: $OV_PROJECT/start-mcp.sh"
echo "  Or install LaunchAgent: make setup (includes auto-start)"
echo ""
