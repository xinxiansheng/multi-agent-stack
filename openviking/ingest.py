#!/usr/bin/env python3
"""
OpenViking Batch Ingest — One-time bulk indexing
=================================================
Usage: python ingest.py

Indexes all existing knowledge into OpenViking:
  - Agent MEMORY.md files
  - Agent memory/ session logs
  - Observer archive
  - USER.md profile
"""

import json
import os
import sys
from pathlib import Path

os.environ["NO_PROXY"] = "*"

import openviking as ov
from openviking_cli.utils.config.open_viking_config import OpenVikingConfig

OPENCLAW_HOME = Path(os.path.expanduser("~/.openclaw"))
OV_DATA = str(OPENCLAW_HOME / "openviking-data")
OV_CONF = os.path.expanduser("~/.openviking/ov.conf")


def main():
    with open(OV_CONF) as f:
        config = OpenVikingConfig.from_dict(json.load(f))

    client = ov.SyncOpenViking(path=OV_DATA, config=config)
    client.initialize()

    indexed = 0

    # 1. USER.md
    user_md = OPENCLAW_HOME / "workspace/USER.md"
    if user_md.exists():
        client.add_resource(path=str(user_md))
        indexed += 1
        print(f"  Indexed: USER.md")

    # 2. All agent MEMORY files
    for ws in OPENCLAW_HOME.iterdir():
        if ws.is_dir() and ws.name.startswith("workspace"):
            mem = ws / "MEMORY.md"
            if mem.exists():
                client.add_resource(path=str(mem))
                indexed += 1
                print(f"  Indexed: {ws.name}/MEMORY.md")

            # Memory directory
            mem_dir = ws / "memory"
            if mem_dir.exists():
                for f in mem_dir.glob("*.md"):
                    client.add_resource(path=str(f))
                    indexed += 1

    # 3. Observer archive
    archive = OPENCLAW_HOME / "workspace-observer/archive"
    if archive.exists():
        for md in archive.rglob("*.md"):
            client.add_resource(path=str(md))
            indexed += 1
        print(f"  Indexed: Observer archive ({indexed} total so far)")

    # Wait for indexing
    print(f"\nWaiting for {indexed} items to be indexed...")
    client.wait_processed(timeout=300)
    client.close()
    print(f"Done. Total indexed: {indexed}")


if __name__ == "__main__":
    main()
