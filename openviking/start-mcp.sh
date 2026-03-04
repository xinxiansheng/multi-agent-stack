#!/bin/bash
# ============================================================
# Start OpenViking MCP Server
# ============================================================
set -euo pipefail

OV_PROJECT="${HOME}/projects/openviking-local"
PORT="${OPENVIKING_PORT:-2033}"

cd "$OV_PROJECT"
source .venv/bin/activate
export NO_PROXY="*"
exec python server.py --port "$PORT"
