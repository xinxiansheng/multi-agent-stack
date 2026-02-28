#!/usr/bin/env python3
"""
OpenClaw Health Check Script
Checks all critical services and sends alerts via Telegram on failure.
Runs every 30 minutes via LaunchAgent.
"""

import json
import os
import subprocess
import sys
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

# --- Configuration ---
OPENCLAW_HOME = Path.home() / ".openclaw"
CONFIG_FILE = OPENCLAW_HOME / "openclaw.json"
LOG_DIR = OPENCLAW_HOME / "logs"

def load_config():
    """Load openclaw.json for Telegram token and gateway port."""
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except Exception as e:
        print(f"WARN: Cannot load config: {e}")
        return {}

def check_process(name, pattern):
    """Check if a process matching pattern is running."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", pattern],
            capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False

def check_port(port):
    """Check if a port is listening."""
    try:
        result = subprocess.run(
            ["lsof", "-i", f":{port}", "-sTCP:LISTEN"],
            capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False

def check_http(url, timeout=10):
    """Check if an HTTP endpoint responds."""
    try:
        proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY")
        if proxy:
            proxy_handler = urllib.request.ProxyHandler({
                "http": proxy, "https": proxy
            })
            opener = urllib.request.build_opener(proxy_handler)
        else:
            opener = urllib.request.build_opener()

        req = urllib.request.Request(url, method="GET")
        resp = opener.open(req, timeout=timeout)
        return resp.status < 500
    except Exception:
        return False

def send_telegram_alert(config, message):
    """Send alert via Telegram bot."""
    try:
        channels = config.get("channels", {}).get("telegram", {})
        bot_token = channels.get("botToken", "")
        if not bot_token:
            print("WARN: No Telegram bot token configured, skipping alert")
            return

        # Find owner user ID from first account's allowFrom
        owner_id = None
        for acc in channels.get("accounts", {}).values():
            if isinstance(acc, dict) and "allowFrom" in acc:
                owner_id = acc["allowFrom"][0]
                break

        if not owner_id:
            print("WARN: No owner user ID found, skipping alert")
            return

        proxy = channels.get("proxy", "")
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = json.dumps({
            "chat_id": owner_id,
            "text": message,
            "parse_mode": "Markdown"
        }).encode()

        if proxy:
            proxy_handler = urllib.request.ProxyHandler({
                "http": proxy, "https": proxy
            })
            opener = urllib.request.build_opener(proxy_handler)
        else:
            opener = urllib.request.build_opener()

        req = urllib.request.Request(url, data=data, headers={
            "Content-Type": "application/json"
        })
        opener.open(req, timeout=15)
        print("Alert sent via Telegram")
    except Exception as e:
        print(f"WARN: Failed to send Telegram alert: {e}")

def main():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n--- Health Check: {now} ---")

    config = load_config()
    gateway_port = config.get("gateway", {}).get("port", 18789)

    checks = []
    failures = []

    # 1. Gateway process
    gw_alive = check_process("gateway", "openclaw.*gateway")
    checks.append(("Gateway Process", gw_alive))
    if not gw_alive:
        failures.append("Gateway process not running")

    # 2. Gateway port
    gw_port = check_port(gateway_port)
    checks.append((f"Gateway Port {gateway_port}", gw_port))
    if not gw_port:
        failures.append(f"Gateway port {gateway_port} not listening")

    # 3. OpenViking (optional)
    ov_port = 2033
    ov_alive = check_port(ov_port)
    checks.append((f"OpenViking Port {ov_port}", ov_alive))
    # OpenViking failure is a warning, not critical

    # 4. Log directory disk usage
    try:
        result = subprocess.run(
            ["du", "-sm", str(LOG_DIR)],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            log_size_mb = int(result.stdout.split()[0])
            log_ok = log_size_mb < 500
            checks.append((f"Log Size ({log_size_mb}MB)", log_ok))
            if not log_ok:
                failures.append(f"Logs consuming {log_size_mb}MB (>500MB)")
    except Exception:
        pass

    # Print results
    for name, ok in checks:
        status = "OK" if ok else "FAIL"
        print(f"  [{status}] {name}")

    # Alert on failures
    if failures:
        msg = f"*OpenClaw Health Alert*\n_{now}_\n\n"
        msg += "\n".join(f"- {f}" for f in failures)
        send_telegram_alert(config, msg)
        print(f"\nFAILURES: {len(failures)}")
        sys.exit(1)
    else:
        print("\nAll checks passed.")
        sys.exit(0)

if __name__ == "__main__":
    main()
