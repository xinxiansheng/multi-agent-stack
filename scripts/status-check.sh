#!/bin/bash
# ============================================================
# System Status Check — Full overview of all services
# Usage: ./scripts/status-check.sh  (or: make status)
# ============================================================
set -uo pipefail

CYAN='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

check() {
    local name="$1"
    local ok="$2"
    if [[ "$ok" == "true" ]]; then
        echo -e "  ${GREEN}[OK]${NC}   $name"
    else
        echo -e "  ${RED}[FAIL]${NC} $name"
    fi
}

echo -e "${CYAN}=== OpenClaw System Status ===${NC}"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# ── Services ──────────────────────────────────────────────────
echo -e "${CYAN}Services:${NC}"
gw=$(pgrep -f "openclaw.*gateway" &>/dev/null && echo "true" || echo "false")
check "Gateway Process" "$gw"

gw_port=$(lsof -i :18789 -sTCP:LISTEN &>/dev/null && echo "true" || echo "false")
check "Gateway Port 18789" "$gw_port"

ov_port=$(lsof -i :2033 -sTCP:LISTEN &>/dev/null && echo "true" || echo "false")
check "OpenViking MCP (2033)" "$ov_port"

dash_port=$(lsof -i :2034 -sTCP:LISTEN &>/dev/null && echo "true" || echo "false")
check "OpenViking Dashboard (2034)" "$dash_port"

rss_port=$(lsof -i :2035 -sTCP:LISTEN &>/dev/null && echo "true" || echo "false")
check "RSSHub (2035)" "$rss_port"

# ── LaunchAgents ──────────────────────────────────────────────
echo ""
echo -e "${CYAN}LaunchAgents:${NC}"
for label in ai.openclaw.gateway ai.openclaw.healthcheck ai.openclaw.logrotate \
             ai.openclaw.observer.collect ai.openclaw.observer.daily \
             ai.openclaw.morning-briefing \
             ai.openviking.mcp ai.openviking.dashboard ai.openviking.rsshub \
             ai.openviking.memory-sync; do
    loaded=$(launchctl list "$label" &>/dev/null && echo "true" || echo "false")
    check "$label" "$loaded"
done

# ── Observer Pipeline ─────────────────────────────────────────
echo ""
echo -e "${CYAN}Observer Pipeline:${NC}"
OBS_WS="$HOME/.openclaw/workspace-observer"
if [[ -f "$OBS_WS/scripts/collect.py" ]]; then
    check "collect.py present" "true"
else
    check "collect.py present" "false"
fi

state_file="$OBS_WS/scripts/state.json"
if [[ -f "$state_file" ]]; then
    run_count=$(python3 -c "import json; print(json.load(open('$state_file')).get('run_count',0))" 2>/dev/null || echo "?")
    seen=$(python3 -c "import json; print(len(json.load(open('$state_file')).get('seen',{})))" 2>/dev/null || echo "?")
    last_run=$(python3 -c "import json; print(json.load(open('$state_file')).get('last_run','never')[:19])" 2>/dev/null || echo "?")
    echo "  Runs: $run_count | Seen: $seen items | Last: $last_run"
else
    echo "  (no collection runs yet)"
fi

archive_count=$(find "$OBS_WS/archive" -name "*.md" -not -path "*/daily/*" 2>/dev/null | wc -l | tr -d ' ')
echo "  Archive: $archive_count knowledge cards"

# ── OpenViking ────────────────────────────────────────────────
echo ""
echo -e "${CYAN}Knowledge Base (OpenViking):${NC}"
if [[ -f "$HOME/.openviking/ov.conf" ]]; then
    check "Config (ov.conf)" "true"
else
    check "Config (ov.conf)" "false"
fi

sync_state="$HOME/.openviking/sync-state.json"
if [[ -f "$sync_state" ]]; then
    synced=$(python3 -c "import json; print(len(json.load(open('$sync_state')).get('files',{})))" 2>/dev/null || echo "?")
    echo "  Synced files: $synced"
else
    echo "  (no sync runs yet)"
fi

# ── Shared State ──────────────────────────────────────────────
echo ""
echo -e "${CYAN}Shared State:${NC}"
state_yaml="$HOME/.openclaw/shared/STATE.yaml"
if [[ -f "$state_yaml" ]]; then
    check "STATE.yaml" "true"
else
    check "STATE.yaml" "false"
fi

# ── Disk ──────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}Disk:${NC}"
log_size=$(du -sm "$HOME/.openclaw/logs" 2>/dev/null | cut -f1 || echo "?")
total_size=$(du -sm "$HOME/.openclaw" 2>/dev/null | cut -f1 || echo "?")
ov_size=$(du -sm "$HOME/.openclaw/openviking-data" 2>/dev/null | cut -f1 || echo "?")
echo "  Logs:       ${log_size}MB"
echo "  OpenViking: ${ov_size}MB"
echo "  Total:      ${total_size}MB"

# ── Workspaces ────────────────────────────────────────────────
echo ""
echo -e "${CYAN}Workspaces:${NC}"
for ws in "$HOME/.openclaw"/workspace*; do
    [[ -d "$ws" ]] || continue
    name=$(basename "$ws")
    if [[ -f "$ws/SOUL.md" ]]; then
        check "$name" "true"
    else
        check "$name (SOUL.md missing)" "false"
    fi
done

echo ""
