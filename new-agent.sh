#!/bin/bash
# ============================================================
# Scaffold a New Agent
# Usage: ./new-agent.sh <agent-id> <agent-name> <emoji> [theme]
#
# Example:
#   ./new-agent.sh arbiter Arbiter "⚖️" "strategic advisor"
#   ./new-agent.sh prism Prism "✨" "content editor"
#   ./new-agent.sh forge Forge "🔨" "engineering partner"
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TEMPLATE_DIR="$SCRIPT_DIR/agents/_template"
OPENCLAW_HOME="$HOME/.openclaw"

if [[ $# -lt 3 ]]; then
    echo "Usage: $0 <agent-id> <agent-name> <emoji> [theme]"
    echo ""
    echo "Examples:"
    echo "  $0 arbiter Arbiter '⚖️' 'strategic advisor'"
    echo "  $0 prism Prism '✨' 'content editor'"
    echo "  $0 forge Forge '🔨' 'engineering partner'"
    echo "  $0 vitals Vitals '💚' 'health companion'"
    exit 1
fi

AGENT_ID="$1"
AGENT_NAME="$2"
AGENT_EMOJI="$3"
AGENT_THEME="${4:-specialized agent}"

WORKSPACE_DIR="$OPENCLAW_HOME/workspace-${AGENT_ID}"
AGENT_DIR="$OPENCLAW_HOME/agents/${AGENT_ID}/agent"

# Check if already exists
if [[ -d "$WORKSPACE_DIR" ]]; then
    echo "ERROR: Workspace already exists: $WORKSPACE_DIR"
    echo "  Remove it first if you want to re-scaffold."
    exit 1
fi

echo "Scaffolding new agent: $AGENT_NAME ($AGENT_EMOJI)"
echo "  ID:        $AGENT_ID"
echo "  Theme:     $AGENT_THEME"
echo "  Workspace: $WORKSPACE_DIR"
echo "  Agent dir: $AGENT_DIR"
echo ""

# Create directories
mkdir -p "$WORKSPACE_DIR/memory"
mkdir -p "$AGENT_DIR"

# Copy and fill templates
for f in SOUL.md IDENTITY.md TOOLS.md AGENTS.md; do
    if [[ -f "$TEMPLATE_DIR/$f" ]]; then
        sed \
            -e "s|{{AGENT_NAME}}|$AGENT_NAME|g" \
            -e "s|{{AGENT_EMOJI}}|$AGENT_EMOJI|g" \
            -e "s|{{AGENT_THEME}}|$AGENT_THEME|g" \
            "$TEMPLATE_DIR/$f" > "$WORKSPACE_DIR/$f"
        echo "  Created: $f"
    fi
done

# Initialize git
(cd "$WORKSPACE_DIR" && git init -q && git add -A && git commit -q -m "Initial workspace: $AGENT_NAME")
echo "  Git initialized"

# Print next steps
echo ""
echo "Agent scaffolded! Next steps:"
echo ""
echo "  1. Edit the workspace files to define ${AGENT_NAME}'s personality:"
echo "     nano $WORKSPACE_DIR/SOUL.md"
echo "     nano $WORKSPACE_DIR/IDENTITY.md"
echo ""
echo "  2. Register in openclaw.json — add to agents.list:"
echo '     {'
echo "       \"id\": \"${AGENT_ID}\","
echo "       \"name\": \"${AGENT_NAME}\","
echo "       \"workspace\": \"${WORKSPACE_DIR}\","
echo "       \"agentDir\": \"${AGENT_DIR}\","
echo '       "model": {'
echo '         "primary": "anthropic/claude-opus-4-6",'
echo '         "fallbacks": ["openai-codex/gpt-5.2", "minimax/MiniMax-M2.5"]'
echo '       },'
echo '       "identity": {'
echo "         \"name\": \"${AGENT_NAME}\","
echo "         \"theme\": \"${AGENT_THEME}\","
echo "         \"emoji\": \"${AGENT_EMOJI}\""
echo '       },'
echo '       "subagents": {'
echo '         "allowAgents": ["main"]'
echo '       }'
echo '     }'
echo ""
echo "  3. Update Nexus's subagents.allowAgents to include \"${AGENT_ID}\""
echo ""
echo "  4. (Optional) Create a Telegram bot via @BotFather and add to channels.telegram.accounts"
echo ""
echo "  5. (Optional) Add LaunchAgent for scheduled tasks:"
echo "     cp launchd/templates/ai.openclaw.observer.collect.plist.template \\"
echo "        launchd/templates/ai.openclaw.${AGENT_ID}.plist.template"
echo "     # Edit the template, then run: ./launchd/install.sh"
echo ""
echo "  6. Restart gateway: launchctl kickstart -k gui/\$(id -u)/ai.openclaw.gateway"
echo ""
