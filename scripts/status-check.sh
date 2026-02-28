#!/bin/bash
# ============================================================
# System Status Check — Quick overview of all services
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

# Gateway
echo -e "${CYAN}Services:${NC}"
gw=$(pgrep -f "openclaw.*gateway" &>/dev/null && echo "true" || echo "false")
check "Gateway Process" "$gw"

gw_port=$(lsof -i :18789 -sTCP:LISTEN &>/dev/null && echo "true" || echo "false")
check "Gateway Port 18789" "$gw_port"

ov_port=$(lsof -i :2033 -sTCP:LISTEN &>/dev/null && echo "true" || echo "false")
check "OpenViking Port 2033" "$ov_port"

# LaunchAgents
echo ""
echo -e "${CYAN}LaunchAgents:${NC}"
for label in ai.openclaw.gateway ai.openclaw.healthcheck ai.openclaw.logrotate \
             ai.openclaw.observer.collect ai.openclaw.observer.daily ai.openviking.mcp; do
    loaded=$(launchctl list "$label" &>/dev/null && echo "true" || echo "false")
    check "$label" "$loaded"
done

# Disk usage
echo ""
echo -e "${CYAN}Disk:${NC}"
log_size=$(du -sm "$HOME/.openclaw/logs" 2>/dev/null | cut -f1 || echo "?")
total_size=$(du -sm "$HOME/.openclaw" 2>/dev/null | cut -f1 || echo "?")
echo "  Logs:  ${log_size}MB"
echo "  Total: ${total_size}MB"

# Workspaces
echo ""
echo -e "${CYAN}Workspaces:${NC}"
for ws in workspace workspace-observer; do
    dir="$HOME/.openclaw/$ws"
    if [[ -f "$dir/SOUL.md" ]]; then
        check "$ws" "true"
    else
        check "$ws (SOUL.md missing)" "false"
    fi
done

echo ""
