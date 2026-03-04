#!/usr/bin/env python3
"""
DingTalk <-> OpenClaw Bridge
=============================
Bidirectional bridge between DingTalk (Stream API) and OpenClaw Gateway.

Flow:
  DingTalk User --[Stream API]--> bridge.py --[openclaw agent]--> Gateway --> Agent
  DingTalk User <--[Robot API]-- bridge.py <--[stdout]---------- Agent

Prerequisites:
  - DingTalk app with Robot capability (Stream mode)
  - dingtalk-stream SDK
  - OpenClaw Gateway running, `openclaw` CLI in PATH

Usage:
  python bridge.py
  DINGTALK_APP_KEY=xxx DINGTALK_APP_SECRET=yyy python bridge.py
"""

import json
import logging
import os
import subprocess
import sys

# DingTalk is a domestic service — must bypass system proxy
# macOS system proxy leaks into urllib.request.getproxies() and breaks websockets
for k in list(os.environ):
    if k.lower() in ("http_proxy", "https_proxy", "all_proxy", "socks_proxy"):
        del os.environ[k]
os.environ["no_proxy"] = "*"

import urllib.request
urllib.request.getproxies = lambda: {}

try:
    from dingtalk_stream import (
        AckMessage, CallbackHandler, ChatbotHandler,
        ChatbotMessage, Credential, DingTalkStreamClient,
    )
except ImportError:
    print("ERROR: dingtalk-stream not installed.")
    print("  pip install dingtalk-stream")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("dingtalk-bridge")

# -- Configuration -----------------------------------------------------------

APP_KEY = os.environ.get("DINGTALK_APP_KEY", "")
APP_SECRET = os.environ.get("DINGTALK_APP_SECRET", "")

# Which OpenClaw agent handles DingTalk messages
AGENT_ID = os.environ.get("DINGTALK_AGENT_ID", "main")

# Timeout for agent response (seconds)
RESPONSE_TIMEOUT = int(os.environ.get("DINGTALK_RESPONSE_TIMEOUT", "120"))

# Path to openclaw CLI
OPENCLAW_BIN = os.environ.get("OPENCLAW_BIN", "openclaw")


# -- Gateway Communication --------------------------------------------------

def send_to_agent(text: str, session_id: str = "") -> str:
    """Send message to OpenClaw agent via CLI and get response."""
    cmd = [
        OPENCLAW_BIN, "agent",
        "--agent", AGENT_ID,
        "--message", text,
        "--json",
    ]
    if session_id:
        cmd.extend(["--session-id", session_id])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=RESPONSE_TIMEOUT,
        )

        if result.returncode != 0:
            logger.error(f"openclaw agent failed: {result.stderr[:200]}")
            return f"[Bridge Error] Agent returned error: {result.stderr[:200]}"

        data = json.loads(result.stdout)

        # Extract reply text from JSON response
        payloads = data.get("result", {}).get("payloads", [])
        if payloads:
            texts = [p.get("text", "") for p in payloads if p.get("text")]
            return "\n".join(texts) if texts else "[No response]"

        return data.get("text", "[No response]")

    except subprocess.TimeoutExpired:
        logger.error("Agent response timeout")
        return "[Bridge Error] Agent response timeout"
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse agent response: {e}")
        return result.stdout if result.stdout else "[Bridge Error] Invalid response"
    except Exception as e:
        logger.error(f"Agent error: {e}")
        return f"[Bridge Error] {e}"


# -- DingTalk Handler --------------------------------------------------------

class OpenClawChatbotHandler(ChatbotHandler):
    """Handle incoming DingTalk messages and forward to OpenClaw."""

    def process(self, callback: CallbackHandler):
        incoming: ChatbotMessage = ChatbotMessage.from_dict(callback.data)

        sender_id = incoming.sender_id or "unknown"
        sender_nick = incoming.sender_nick or sender_id
        text = (incoming.text.content or "").strip()
        conversation_id = incoming.conversation_id or sender_id

        if not text:
            self.reply_text("请发送文字消息。", incoming)
            return AckMessage.STATUS_OK, "OK"

        logger.info(f"[{sender_nick}] {text[:80]}")

        # Forward to OpenClaw agent
        # Use conversation_id as session_id for context continuity
        reply = send_to_agent(
            text=text,
            session_id=f"dingtalk:{conversation_id}",
        )

        # Truncate if too long for DingTalk (max ~20000 chars for markdown)
        if len(reply) > 18000:
            reply = reply[:18000] + "\n\n...(truncated)"

        logger.info(f"  -> Reply ({len(reply)} chars)")

        # Reply via DingTalk
        self.reply_markdown(
            title="Reply",
            text=reply,
            incoming_message=incoming,
        )

        return AckMessage.STATUS_OK, "OK"


# -- Main --------------------------------------------------------------------

def main():
    if not APP_KEY or not APP_SECRET:
        print("ERROR: DINGTALK_APP_KEY and DINGTALK_APP_SECRET required.")
        print("  Set them in .env or as environment variables.")
        sys.exit(1)

    # Verify openclaw CLI is available
    try:
        ver = subprocess.run(
            [OPENCLAW_BIN, "--version"],
            capture_output=True, text=True, timeout=5,
        )
        logger.info(f"OpenClaw: {ver.stdout.strip()}")
    except FileNotFoundError:
        print(f"ERROR: '{OPENCLAW_BIN}' not found in PATH.")
        print("  Set OPENCLAW_BIN env var or ensure openclaw is installed.")
        sys.exit(1)

    logger.info("DingTalk <-> OpenClaw Bridge starting")
    logger.info(f"  Agent: {AGENT_ID}")

    client = DingTalkStreamClient(
        credential=Credential(
            client_id=APP_KEY,
            client_secret=APP_SECRET,
        ),
    )

    client.register_callback_handler(
        ChatbotMessage.TOPIC,
        OpenClawChatbotHandler(),
    )

    logger.info("Connecting to DingTalk Stream...")
    client.start_forever()


if __name__ == "__main__":
    main()
