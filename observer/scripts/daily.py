#!/usr/bin/env python3
"""
Observer Daily Briefing Generator
==================================
Collects all knowledge cards from the day, generates a structured briefing
via LLM, and pushes to IM via OpenClaw CLI.

Usage:
  python daily.py                    # Today's briefing
  python daily.py --no-push          # Generate but don't push
  python daily.py --date 2026-02-15  # Specific date
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    import urllib.request
    HAS_HTTPX = False

WORKSPACE = Path(os.environ.get(
    "OBSERVER_WORKSPACE",
    os.path.expanduser("~/.openclaw/workspace-observer")
))
ARCHIVE_DIR = WORKSPACE / "archive"

LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://newapi.sms88.info/v1")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_DAILY_MODEL = os.environ.get("LLM_DAILY_MODEL", "gemini-3-pro-preview")

CST = timezone(timedelta(hours=8))


def _llm_call(system: str, user: str) -> str:
    if not LLM_API_KEY:
        return ""

    payload = {
        "model": LLM_DAILY_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.3,
        "max_tokens": 4096,
    }
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }

    if HAS_HTTPX:
        with httpx.Client(timeout=120) as client:
            resp = client.post(f"{LLM_BASE_URL}/chat/completions",
                               json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
    else:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{LLM_BASE_URL}/chat/completions", data=data, headers=headers)
        resp = urllib.request.urlopen(req, timeout=120)
        return json.loads(
            resp.read())["choices"][0]["message"]["content"]


def collect_cards(date_str: str) -> list:
    """Collect all knowledge cards for a given date."""
    month = date_str[:7]
    month_dir = ARCHIVE_DIR / month
    if not month_dir.exists():
        return []

    cards = []
    for f in month_dir.glob("*.md"):
        content = f.read_text(encoding="utf-8")
        m = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
        if not m:
            continue
        try:
            meta = yaml.safe_load(m.group(1))
            if not isinstance(meta, dict):
                continue
            if meta.get("date") == date_str:
                meta["_body"] = content[m.end():].strip()
                cards.append(meta)
        except Exception:
            continue

    cards.sort(key=lambda c: c.get("score", 0), reverse=True)
    return cards


def generate_briefing(cards: list, date_str: str) -> str:
    if not cards:
        return f"# {date_str} Observer Daily\n\nNo new intelligence today.\n"

    high = [c for c in cards if c.get("score", 0) >= 70]
    low = [c for c in cards if 50 <= c.get("score", 0) < 70]

    card_summaries = []
    for c in high:
        highlights = "\n".join(
            f"  - {h}" for h in c.get("highlights", []))
        card_summaries.append(
            f"### [{c.get('score', '?')}] {c.get('title', 'Untitled')}\n"
            f"Source: {c.get('source', '?')} | "
            f"Tags: {', '.join(c.get('topics', []))}\n"
            f"Highlights:\n{highlights}\n"
            + (f"Quote: {c.get('golden_quote', '')}\n"
               if c.get('golden_quote') else "")
            + f"Link: {c.get('url', '')}"
        )

    cards_text = "\n\n".join(card_summaries)

    system = (
        "你是 Observer，生成每日情报简报。风格要求：\n"
        "- 结论先行，不要铺垫\n"
        "- 按重要性分层：🔴 重要 / 🟡 关注 / 🔵 了解\n"
        "- 每条信息 2-3 行，包含核心观点和为什么重要\n"
        "- 最后加一段「今日洞察」：跨领域关联发现（如有）\n"
        "- 用 Markdown 格式\n"
        "- 不要超过 1500 字\n"
    )

    user_msg = (
        f"## Date: {date_str}\n"
        f"## High-score ({len(high)} items)\n\n{cards_text}\n\n"
        f"## Archived ({len(low)} items)\n"
        + "\n".join(
            f"- [{c.get('score', '?')}] {c.get('title', '')} "
            f"({c.get('source', '')})"
            for c in low)
        + "\n\nPlease generate the daily briefing:"
    )

    try:
        return _llm_call(system, user_msg)
    except Exception as e:
        briefing = f"# {date_str} Observer Daily\n\n"
        briefing += f"(Model generation failed: {e})\n\n"
        briefing += cards_text
        return briefing


def push_briefing(briefing: str, date_str: str):
    """Push briefing via OpenClaw CLI."""
    if len(briefing) > 3800:
        briefing = briefing[:3800] + "\n\n...(see archive for full version)"

    msg = f"Observer Daily {date_str}\n\n{briefing}"

    try:
        subprocess.run(
            ["openclaw", "agent", "--agent", "main",
             "--channel", "telegram", "--deliver", "-m", msg],
            capture_output=True, text=True, timeout=60,
        )
        print("  Pushed to IM")
    except FileNotFoundError:
        print("  WARN: openclaw CLI not found, skipping push")
    except Exception as e:
        print(f"  WARN push failed: {e}")


def run(date_str: str = None, push: bool = True):
    if not date_str:
        date_str = datetime.now(CST).strftime("%Y-%m-%d")

    print(f"Observer Daily Briefing — {date_str}")

    cards = collect_cards(date_str)
    print(f"  Knowledge cards: {len(cards)}")

    briefing = generate_briefing(cards, date_str)

    daily_dir = ARCHIVE_DIR / "daily"
    daily_dir.mkdir(parents=True, exist_ok=True)
    daily_file = daily_dir / f"{date_str}.md"
    daily_file.write_text(briefing, encoding="utf-8")
    print(f"  Saved: {daily_file}")

    if push and cards:
        push_briefing(briefing, date_str)

    print("Done.")


if __name__ == "__main__":
    args = sys.argv[1:]
    no_push = "--no-push" in args
    date_val = None
    for i, a in enumerate(args):
        if a == "--date" and i + 1 < len(args):
            date_val = args[i + 1]

    run(date_str=date_val, push=not no_push)
