#!/bin/bash
# ============================================================
# Install LaunchAgent plist files from templates
# Usage: ./launchd/install.sh
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
STACK_DIR="$(dirname "$SCRIPT_DIR")"
TEMPLATE_DIR="$SCRIPT_DIR/templates"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
ENV_FILE="$STACK_DIR/.env"

if [[ ! -f "$ENV_FILE" ]]; then
    echo "ERROR: .env not found. Run setup first."
    exit 1
fi

set -a; source "$ENV_FILE"; set +a

# Detect homebrew prefix
HOMEBREW_PREFIX="$(brew --prefix 2>/dev/null || echo '/opt/homebrew')"

# Auto-detect
MACHINE_USER="${MACHINE_USER:-$(whoami)}"
HOME_DIR="${HOME_DIR:-$HOME}"

echo "Installing LaunchAgent plist files..."
echo "  Home: $HOME_DIR"
echo "  Homebrew: $HOMEBREW_PREFIX"
echo "  Target: $LAUNCH_AGENTS_DIR"

mkdir -p "$LAUNCH_AGENTS_DIR"

installed=0
for template in "$TEMPLATE_DIR"/*.template; do
    [[ -f "$template" ]] || continue

    # Strip .template extension
    filename="$(basename "$template" .template)"
    target="$LAUNCH_AGENTS_DIR/$filename"

    echo "  Installing: $filename"

    # Replace placeholders
    sed \
        -e "s|__HOME__|$HOME_DIR|g" \
        -e "s|__HOMEBREW_PREFIX__|$HOMEBREW_PREFIX|g" \
        -e "s|__GATEWAY_PORT__|${GATEWAY_PORT:-18789}|g" \
        -e "s|__HTTP_PROXY__|${HTTP_PROXY:-}|g" \
        -e "s|__OPENVIKING_PORT__|${OPENVIKING_PORT:-2033}|g" \
        -e "s|__RSSHUB_PORT__|${RSSHUB_PORT:-2035}|g" \
        "$template" > "$target"

    # Load the agent
    launchctl unload "$target" 2>/dev/null || true
    launchctl load "$target"

    ((installed++))
done

echo ""
echo "OK: Installed $installed LaunchAgent(s)"
echo ""
echo "Verify with:"
echo "  launchctl list | grep -E 'openclaw|openviking'"
