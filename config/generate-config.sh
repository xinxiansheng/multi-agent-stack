#!/bin/bash
# ============================================================
# Generate openclaw.json from template + .env
# Usage: ./config/generate-config.sh
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
STACK_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$STACK_DIR/.env"
TEMPLATE="$SCRIPT_DIR/openclaw.template.json"
OUTPUT="$HOME/.openclaw/openclaw.json"

if [[ ! -f "$ENV_FILE" ]]; then
    echo "ERROR: .env file not found. Copy .env.template to .env first."
    echo "  cp $STACK_DIR/.env.template $STACK_DIR/.env"
    exit 1
fi

# Load .env
set -a
source "$ENV_FILE"
set +a

# Auto-detect machine user and home if not set
MACHINE_USER="${MACHINE_USER:-$(whoami)}"
HOME_DIR="${HOME_DIR:-$HOME}"

# Generate gateway auth token if placeholder
if [[ "$GATEWAY_AUTH_TOKEN" == "__GENERATE_ME__" ]]; then
    GATEWAY_AUTH_TOKEN=$(openssl rand -hex 24)
    echo "INFO: Generated gateway auth token: ${GATEWAY_AUTH_TOKEN:0:8}..."
    # Write back to .env
    sed -i '' "s|GATEWAY_AUTH_TOKEN=__GENERATE_ME__|GATEWAY_AUTH_TOKEN=$GATEWAY_AUTH_TOKEN|" "$ENV_FILE"
fi

echo "Generating openclaw.json..."
echo "  User: $MACHINE_USER"
echo "  Home: $HOME_DIR"
echo "  Gateway port: $GATEWAY_PORT"
echo "  Primary model: $PRIMARY_MODEL"

# Check envsubst is available
if ! command -v envsubst &>/dev/null; then
    echo "ERROR: envsubst not found. Install gettext:"
    echo "  brew install gettext"
    exit 1
fi

# Required vars check
for var in GATEWAY_PORT GATEWAY_AUTH_TOKEN PRIMARY_MODEL; do
    if [[ -z "${!var:-}" ]]; then
        echo "ERROR: $var is not set in .env"
        exit 1
    fi
done

# Process template with envsubst
export MACHINE_USER HOME_DIR GATEWAY_PORT GATEWAY_AUTH_TOKEN \
       PRIMARY_MODEL FALLBACK_MODEL_1 FALLBACK_MODEL_2 \
       OBSERVER_PRIMARY_MODEL OBSERVER_FALLBACK_MODEL \
       HTTP_PROXY \
       TG_NEXUS_BOT_TOKEN TG_OBSERVER_BOT_TOKEN TG_OWNER_USER_ID \
       MINIMAX_API_KEY NEWAPI_BASE_URL NEWAPI_API_KEY \
       OPENVIKING_PORT RSSHUB_PORT \
       WHISPER_MODEL WHISPER_LANGUAGE \
       DINGTALK_ENABLED DINGTALK_APP_KEY DINGTALK_APP_SECRET DINGTALK_AGENT_ID

envsubst < "$TEMPLATE" > "$OUTPUT"

# Verify no unsubstituted placeholders remain
if grep -q '${[A-Z_]*}' "$OUTPUT" 2>/dev/null; then
    echo "WARN: Some variables may not have been substituted:"
    grep -o '\${[A-Z_]*}' "$OUTPUT" | sort -u | head -10
fi

# Validate JSON
if python3 -c "import json; json.load(open('$OUTPUT'))" 2>/dev/null; then
    echo "OK: openclaw.json generated at $OUTPUT"
else
    echo "ERROR: Generated JSON is invalid. Check template syntax."
    exit 1
fi

chmod 600 "$OUTPUT"
echo "OK: Permissions set to 600 (owner-only read/write)"
