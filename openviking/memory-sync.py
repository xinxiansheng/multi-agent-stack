#!/usr/bin/env python3
"""
Daily Memory Sync — Incremental sync of Agent memory to OpenViking
==================================================================
Runs daily at 23:30 via LaunchAgent.

Syncs:
  - MEMORY.md files from all agent workspaces
  - memory/ directories (daily session logs)
  - USER.md (user profile context)

Only syncs files modified since last run (tracks mtime in state file).
"""

import json
import os
import sys
import time
from pathlib import Path

os.environ["NO_PROXY"] = "*"

try:
    import openviking as ov
    from openviking_cli.utils.config.open_viking_config import OpenVikingConfig
except ImportError:
    print("ERROR: openviking not installed. Run: pip install openviking")
    sys.exit(1)

# ── Configuration ──────────────────────────────────────────────

OPENCLAW_HOME = Path(os.environ.get("OPENCLAW_HOME", os.path.expanduser("~/.openclaw")))
OV_DATA = str(OPENCLAW_HOME / "openviking-data")
OV_CONF = os.path.expanduser("~/.openviking/ov.conf")
STATE_FILE = Path(os.path.expanduser("~/.openviking/sync-state.json"))

# Static files to track
SYNC_TARGETS = {
    "user/profile": OPENCLAW_HOME / "workspace/USER.md",
}

# Directories to scan for new .md files
SYNC_DIRS = {}


def discover_workspaces():
    """Auto-discover all agent workspaces and populate sync targets."""
    for d in OPENCLAW_HOME.iterdir():
        if d.is_dir() and d.name.startswith("workspace"):
            agent = d.name.replace("workspace-", "").replace("workspace", "nexus")
            mem_file = d / "MEMORY.md"
            if mem_file.exists():
                SYNC_TARGETS[f"{agent}/MEMORY"] = mem_file
            mem_dir = d / "memory"
            if mem_dir.exists():
                SYNC_DIRS[f"{agent}/memory"] = mem_dir


def load_state() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"files": {}, "last_run": None}


def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state["last_run"] = time.time()
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def sync_file(client, filepath: Path, label: str, state: dict) -> bool:
    """Sync file if modified since last sync."""
    if not filepath.exists():
        return False
    mtime = filepath.stat().st_mtime
    key = str(filepath)
    if state["files"].get(key, {}).get("mtime", 0) >= mtime:
        return False  # Not modified

    try:
        result = client.add_resource(path=str(filepath))
        state["files"][key] = {
            "mtime": mtime,
            "synced_at": time.time(),
            "label": label
        }
        uri = result.get("root_uri", "ok") if isinstance(result, dict) else str(result)
        print(f"  SYNC {label} -> {uri}")
        return True
    except Exception as e:
        print(f"  ERROR {label}: {e}")
        return False


def main():
    print(f"Memory Sync — {time.strftime('%Y-%m-%d %H:%M:%S')}")

    # Load config
    if not os.path.exists(OV_CONF):
        print(f"ERROR: OpenViking config not found: {OV_CONF}")
        sys.exit(1)

    with open(OV_CONF) as f:
        config = OpenVikingConfig.from_dict(json.load(f))

    client = ov.SyncOpenViking(path=OV_DATA, config=config)
    client.initialize()

    # Discover workspaces
    discover_workspaces()

    state = load_state()
    synced = 0

    # Sync tracked files
    print("\nTracked files:")
    for label, path in SYNC_TARGETS.items():
        if sync_file(client, path, label, state):
            synced += 1

    # Scan directories
    print("\nMemory directories:")
    for label, dirpath in SYNC_DIRS.items():
        for f in sorted(dirpath.glob("*.md")):
            if sync_file(client, f, f"{label}/{f.name}", state):
                synced += 1

    # Wait for indexing
    if synced > 0:
        print(f"\nWaiting for {synced} items to be indexed...")
        try:
            client.wait_processed(timeout=120)
        except Exception:
            pass

    client.close()
    save_state(state)
    print(f"\nDone. Synced {synced} files.")


if __name__ == "__main__":
    main()
