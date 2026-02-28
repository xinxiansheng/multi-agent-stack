#!/usr/bin/env python3
"""
Observer Daily Briefing Generator
==================================
Usage:
  python daily.py                    # Today's briefing
  python daily.py --no-push          # Generate but don't push
  python daily.py --date 2026-02-15  # Specific date

Collects all cards from the day, generates a structured briefing via LLM,
and pushes to Telegram via OpenClaw.
"""

import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

WORKSPACE = Path(os.environ.get(
    "OBSERVER_WORKSPACE",
    os.path.expanduser("~/.openclaw/workspace-observer")
))
ARCHIVE_DIR = WORKSPACE / "archive"
DAILY_DIR = ARCHIVE_DIR / "daily"

LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://newapi.sms88.info/v1")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_DAILY_MODEL = os.environ.get("LLM_DAILY_MODEL", "gemini-3-pro-preview")

TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID", "")
TG_PROXY = os.environ.get("TG_PROXY", "")
PROXY = os.environ.get("HTTPS_PROXY", os.environ.get("HTTP_PROXY", ""))


def llm_call(model: str, system: str, user: str) -> str:
    if not LLM_API_KEY:
        return ""
    url = f"{LLM_BASE_URL}/chat/completions"
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ],
        "temperature": 0.3,
        "max_tokens": 8192
    }).encode()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LLM_API_KEY}"
    }
    if PROXY:
        handler = urllib.request.ProxyHandler({"http": PROXY, "https": PROXY})
        opener = urllib.request.build_opener(handler)
    else:
        opener = urllib.request.build_opener()
    req = urllib.request.Request(url, data=payload, headers=headers)
    try:
        resp = opener.open(req, timeout=120)
        data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"  LLM error: {e}")
        return ""


def tg_push(text: str):
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        return False
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    payload = json.dumps({
        "chat_id": TG_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }).encode()
    if TG_PROXY:
        handler = urllib.request.ProxyHandler({"http": TG_PROXY, "https": TG_PROXY})
        opener = urllib.request.build_opener(handler)
    else:
        opener = urllib.request.build_opener()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        opener.open(req, timeout=15)
        return True
    except Exception as e:
        print(f"  TG push error: {e}")
        return False


def collect_cards(date_str: str) -> list:
    """Collect all knowledge cards for a given date."""
    # Cards are stored in archive/YYYY-MM/
    month = date_str[:7]
    month_dir = ARCHIVE_DIR / month
    if not month_dir.exists():
        return []

    cards = []
    for f in sorted(month_dir.glob("*.md")):
        content = f.read_text(encoding="utf-8")
        # Parse YAML frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                # Check if card date matches
                if date_str in parts[1]:
                    cards.append({"file": f.name, "content": content})
    return cards


def generate_briefing(cards: list, date_str: str) -> str:
    """Generate daily briefing via LLM."""
    if not cards:
        return f"📋 *Observer Daily — {date_str}*\n\n今日无新采集。"

    system = (
        "你是信息分析师，生成一份简洁的每日情报简报。\n"
        "格式:\n"
        "📋 Observer Daily — {date}\n\n"
        "📊 今日统计: X 条采集\n\n"
        "🔥 重点关注 (≥70分):\n"
        "逐条列出标题、分数、一句话要点\n\n"
        "📦 其他归档 (50-69分):\n"
        "仅列标题\n\n"
        "💡 今日洞察:\n"
        "跨领域趋势观察 (1-2句)\n\n"
        "保持简洁，每条不超过2行。"
    )

    user = f"日期: {date_str}\n采集 {len(cards)} 条:\n\n"
    for card in cards[:30]:  # Limit to avoid context overflow
        user += f"---\n{card['content'][:500]}\n"

    return llm_call(LLM_DAILY_MODEL, system, user)


def main():
    parser = argparse.ArgumentParser(description="Observer Daily Briefing")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"),
                        help="Date for briefing (YYYY-MM-DD)")
    parser.add_argument("--no-push", action="store_true",
                        help="Don't push to Telegram")
    args = parser.parse_args()

    date_str = args.date
    print(f"Observer Daily Briefing — {date_str}")

    # Collect cards
    cards = collect_cards(date_str)
    print(f"  Found {len(cards)} cards")

    # Generate briefing
    briefing = generate_briefing(cards, date_str)
    print(f"  Briefing generated ({len(briefing)} chars)")

    # Save to daily/
    DAILY_DIR.mkdir(parents=True, exist_ok=True)
    daily_file = DAILY_DIR / f"{date_str}.md"
    daily_file.write_text(briefing, encoding="utf-8")
    print(f"  Saved: {daily_file}")

    # Push
    if not args.no_push:
        if tg_push(briefing):
            print("  Pushed to Telegram")
        else:
            print("  TG push skipped/failed")

    print("Done.")


if __name__ == "__main__":
    main()
