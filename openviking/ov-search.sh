#!/bin/bash
# ============================================================
# OpenViking CLI Search
# Usage: ./ov-search.sh <query>
# Example: ./ov-search.sh "AI Agent architecture"
# ============================================================

OV_PROJECT="${HOME}/projects/openviking-local"
OV_VENV="${OV_PROJECT}/.venv/bin/python3"
OV_DATA="${HOME}/.openclaw/openviking-data"
OV_CONF="${HOME}/.openviking/ov.conf"

if [[ $# -eq 0 ]]; then
    echo "Usage: ov-search <query>"
    exit 1
fi

NO_PROXY='*' "$OV_VENV" -c "
import sys, json, openviking as ov
from openviking_cli.utils.config.open_viking_config import OpenVikingConfig

q = ' '.join(sys.argv[1:])
with open('${OV_CONF}') as f:
    config = OpenVikingConfig.from_dict(json.load(f))
client = ov.SyncOpenViking(path='${OV_DATA}', config=config)
client.initialize()
results = client.search(q)
for r in results.resources[:5]:
    print(f'[{r.score:.3f}] {r.uri}')
client.close()
" "$@"
