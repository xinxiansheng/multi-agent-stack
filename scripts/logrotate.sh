#!/bin/bash
# ============================================================
# Log Rotation for OpenClaw
# Rotates logs > 5MB, keeps 7 days of rotated logs
# Runs daily at 03:00 via LaunchAgent
# ============================================================
set -euo pipefail

LOG_DIR="$HOME/.openclaw/logs"
MAX_SIZE_KB=5120     # 5MB
KEEP_DAYS=7

if [[ ! -d "$LOG_DIR" ]]; then
    echo "Log directory not found: $LOG_DIR"
    exit 0
fi

echo "$(date '+%Y-%m-%d %H:%M:%S') - Log rotation started"

# Rotate large log files
rotated=0
while IFS= read -r logfile; do
    size_kb=$(du -k "$logfile" | cut -f1)
    if [[ $size_kb -gt $MAX_SIZE_KB ]]; then
        timestamp=$(date '+%Y%m%d-%H%M%S')
        rotated_name="${logfile}.${timestamp}"
        mv "$logfile" "$rotated_name"
        touch "$logfile"
        gzip "$rotated_name" 2>/dev/null || true
        echo "  Rotated: $(basename "$logfile") (${size_kb}KB)"
        ((rotated++))
    fi
done < <(find "$LOG_DIR" -maxdepth 1 -name "*.log" -type f)

# Clean old rotated logs
cleaned=0
while IFS= read -r oldlog; do
    rm -f "$oldlog"
    echo "  Cleaned: $(basename "$oldlog")"
    ((cleaned++))
done < <(find "$LOG_DIR" -maxdepth 1 -name "*.log.*.gz" -mtime +${KEEP_DAYS} -type f)

echo "  Rotated: $rotated, Cleaned: $cleaned"
echo "$(date '+%Y-%m-%d %H:%M:%S') - Log rotation complete"
