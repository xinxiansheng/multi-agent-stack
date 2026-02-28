#!/bin/bash
# ============================================================
# Morning Briefing — Daily summary via Telegram
# ============================================================
# Collects: pending todos + system status + Observer highlights
# Pushes via Nexus Telegram Bot
#
# Schedule: manual or via LaunchAgent (recommended 08:30)
# ============================================================
set -euo pipefail

OPENCLAW_HOME="$HOME/.openclaw"
WORKSPACE="$OPENCLAW_HOME/workspace"
OBS_WORKSPACE="$OPENCLAW_HOME/workspace-observer"
TODAY=$(date +%Y-%m-%d)
YESTERDAY=$(date -v-1d +%Y-%m-%d 2>/dev/null || date -d "yesterday" +%Y-%m-%d)
WEEKDAY=$(date +%u)

# ── 1. Collect pending todos ──────────────────────────────────
TODOS=""
for ws in "$OPENCLAW_HOME"/workspace*; do
    if [[ -d "$ws/memory" ]]; then
        found=$(grep -rh '\- \[ \]' "$ws/memory/" 2>/dev/null | head -5 || true)
        if [[ -n "$found" ]]; then
            agent_name=$(basename "$ws" | sed 's/workspace-//' | sed 's/^workspace$/nexus/')
            TODOS="${TODOS}\n  ${agent_name}: ${found}\n"
        fi
    fi
done

# ── 2. System status ─────────────────────────────────────────
SERVICES=""
for svc in ai.openclaw.gateway ai.openclaw.healthcheck ai.openclaw.observer.collect ai.openviking.mcp; do
    if launchctl list "$svc" &>/dev/null; then
        SERVICES="${SERVICES}  OK  ${svc}\n"
    else
        SERVICES="${SERVICES}  FAIL ${svc}\n"
    fi
done

# ── 3. Observer highlights ────────────────────────────────────
OBS_SUMMARY="No data"
OBS_DAILY="$OBS_WORKSPACE/archive/daily/${YESTERDAY}.md"
if [[ -f "$OBS_DAILY" ]]; then
    OBS_SUMMARY=$(head -20 "$OBS_DAILY")
fi

# ── 4. Assemble briefing ─────────────────────────────────────
BRIEFING="Morning Briefing — ${TODAY}\n\n"
BRIEFING="${BRIEFING}Pending Todos:\n${TODOS:-  (none)}\n\n"
BRIEFING="${BRIEFING}System Status:\n${SERVICES}\n"
BRIEFING="${BRIEFING}Observer (yesterday):\n${OBS_SUMMARY}\n"

if [[ "$WEEKDAY" == "1" ]]; then
    BRIEFING="${BRIEFING}\nMonday: Consider weekly review + memory consolidation.\n"
fi

# ── 5. Push to Telegram ──────────────────────────────────────
CONFIG="$OPENCLAW_HOME/openclaw.json"
if [[ -f "$CONFIG" ]]; then
    TG_TOKEN=$(python3 -c "
import json
with open('$CONFIG') as f:
    c = json.load(f)
print(c.get('channels',{}).get('telegram',{}).get('botToken',''))
" 2>/dev/null || true)

    TG_PROXY=$(python3 -c "
import json
with open('$CONFIG') as f:
    c = json.load(f)
print(c.get('channels',{}).get('telegram',{}).get('proxy',''))
" 2>/dev/null || true)

    TG_CHAT_ID=$(python3 -c "
import json
with open('$CONFIG') as f:
    c = json.load(f)
accts = c.get('channels',{}).get('telegram',{}).get('accounts',{})
for a in accts.values():
    if isinstance(a, dict) and 'allowFrom' in a:
        print(a['allowFrom'][0])
        break
" 2>/dev/null || true)

    if [[ -n "$TG_TOKEN" && -n "$TG_CHAT_ID" ]]; then
        MSG=$(echo -e "$BRIEFING")
        PROXY_ARG=""
        if [[ -n "$TG_PROXY" ]]; then
            PROXY_ARG="-x $TG_PROXY"
        fi
        curl -s $PROXY_ARG \
            -X POST "https://api.telegram.org/bot${TG_TOKEN}/sendMessage" \
            -d chat_id="$TG_CHAT_ID" \
            --data-urlencode text="$MSG" \
            > /dev/null 2>&1
        echo "Briefing pushed to Telegram"
    else
        echo -e "$BRIEFING" > "$WORKSPACE/memory/morning-briefing-${TODAY}.md"
        echo "TG push failed, saved to file"
    fi
else
    echo -e "$BRIEFING"
fi
