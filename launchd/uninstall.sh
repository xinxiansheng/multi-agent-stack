#!/bin/bash
# ============================================================
# Uninstall all OpenClaw LaunchAgent plist files
# Usage: ./launchd/uninstall.sh
# ============================================================
set -euo pipefail

LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"

echo "Uninstalling OpenClaw LaunchAgents..."

removed=0
for plist in "$LAUNCH_AGENTS_DIR"/ai.openclaw.*.plist "$LAUNCH_AGENTS_DIR"/ai.openviking.*.plist; do
    [[ -f "$plist" ]] || continue

    filename="$(basename "$plist")"
    echo "  Removing: $filename"

    launchctl unload "$plist" 2>/dev/null || true
    rm -f "$plist"

    ((removed++))
done

if [[ $removed -eq 0 ]]; then
    echo "  No LaunchAgents found to remove."
else
    echo ""
    echo "OK: Removed $removed LaunchAgent(s)"
fi
