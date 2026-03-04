#!/usr/bin/env python3
"""
DingTalk <-> OpenClaw Bridge
=============================
Bidirectional bridge between DingTalk (Stream API) and OpenClaw Gateway.

Flow:
  DingTalk User --[Stream API]--> bridge.py --[HTTP API]--> OpenClaw Gateway
  DingTalk User <--[Robot API]-- bridge.py <--[Response]-- OpenClaw Gateway

Prerequisites:
  - DingTalk enterprise app with Robot capability
  - dingtalk-stream SDK
  - OpenClaw Gateway running on localhost

Usage:
  python bridge.py
  DINGTALK_APP_KEY=xxx DINGTALK_APP_SECRET=yyy python bridge.py
"""

import json
import logging
import os
import sys
import time
import threading

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    import urllib.request
    HAS_HTTPX = False

try:
    from dingtalk_stream import (
        AckMessage, CallbackHandler, ChatbotHandler,
        ChatbotMessage, DingTalkStreamClient,
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

GATEWAY_URL = os.environ.get(
    "GATEWAY_URL", "http://127.0.0.1:18789")
GATEWAY_AUTH_TOKEN = os.environ.get("GATEWAY_AUTH_TOKEN", "")

# Which OpenClaw agent handles DingTalk messages
AGENT_ID = os.environ.get("DINGTALK_AGENT_ID", "main")

# Timeout for waiting for Gateway response
RESPONSE_TIMEOUT = int(os.environ.get("DINGTALK_RESPONSE_TIMEOUT", "120"))


# -- Gateway Communication --------------------------------------------------

def send_to_gateway(sender_id: str, text: str,
                    conversation_id: str = "") -> str:
    """Send message to OpenClaw Gateway and get response."""
    url = f"{GATEWAY_URL}/api/v1/message"
    payload = {
        "agentId": AGENT_ID,
        "channel": "dingtalk",
        "senderId": sender_id,
        "conversationId": conversation_id or sender_id,
        "text": text,
        "metadata": {
            "source": "dingtalk-bridge",
        },
    }
    headers = {
        "Content-Type": "application/json",
    }
    if GATEWAY_AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {GATEWAY_AUTH_TOKEN}"

    try:
        if HAS_HTTPX:
            with httpx.Client(timeout=RESPONSE_TIMEOUT) as client:
                resp = client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        else:
            req_data = json.dumps(payload).encode()
            req = urllib.request.Request(
                url, data=req_data, headers=headers)
            resp = urllib.request.urlopen(req, timeout=RESPONSE_TIMEOUT)
            data = json.loads(resp.read())

        # Extract response text
        if isinstance(data, dict):
            return (data.get("text", "")
                    or data.get("reply", "")
                    or data.get("message", "")
                    or json.dumps(data, ensure_ascii=False))
        return str(data)

    except Exception as e:
        logger.error(f"Gateway error: {e}")
        return f"[Bridge Error] Failed to reach agent: {e}"


def poll_gateway_response(request_id: str) -> str:
    """Poll Gateway for async response (if Gateway uses async mode)."""
    url = f"{GATEWAY_URL}/api/v1/message/{request_id}"
    headers = {}
    if GATEWAY_AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {GATEWAY_AUTH_TOKEN}"

    deadline = time.time() + RESPONSE_TIMEOUT
    while time.time() < deadline:
        try:
            if HAS_HTTPX:
                with httpx.Client(timeout=30) as client:
                    resp = client.get(url, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get("status") == "completed":
                            return data.get("text", "")
            else:
                req = urllib.request.Request(url, headers=headers)
                resp = urllib.request.urlopen(req, timeout=30)
                data = json.loads(resp.read())
                if data.get("status") == "completed":
                    return data.get("text", "")
        except Exception:
            pass
        time.sleep(2)

    return "[Bridge Error] Response timeout"


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
            self.reply_text("Please send a text message.", incoming)
            return AckMessage.STATUS_OK, "OK"

        logger.info(f"[{sender_nick}] {text[:80]}")

        # Forward to OpenClaw Gateway
        reply = send_to_gateway(
            sender_id=sender_id,
            text=text,
            conversation_id=conversation_id,
        )

        # Truncate if too long for DingTalk (max ~20000 chars for markdown)
        if len(reply) > 18000:
            reply = reply[:18000] + "\n\n...(truncated)"

        logger.info(f"  -> Reply ({len(reply)} chars)")

        # Reply via DingTalk
        self.reply_markdown(
            title=f"Reply",
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

    logger.info("DingTalk <-> OpenClaw Bridge starting")
    logger.info(f"  Gateway: {GATEWAY_URL}")
    logger.info(f"  Agent: {AGENT_ID}")

    client = DingTalkStreamClient(
        credential=DingTalkStreamClient.Credential(
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
