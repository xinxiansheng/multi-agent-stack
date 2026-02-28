#!/usr/bin/env python3
"""
Observer Collection Pipeline — Two-Tier AI Filtering
=====================================================
Usage:
  python collect.py              # Normal mode (~23% sampling)
  python collect.py --full       # Full collection (no sampling)
  python collect.py --dry-run    # Preview only, no archive
  python collect.py --feed-only  # Show feed counts only

Pipeline:
  Sources → Dedup → Sample 23% → Tier-1 Topic Match (Flash)
  → Tier-2 Multi-dim Score (Flash) → Extract (≥70) → Archive → Push (≥85)
"""

import argparse
import hashlib
import json
import os
import random
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from pathlib import Path

import feedparser
import yaml

# ── Configuration ──────────────────────────────────────────────

WORKSPACE = Path(os.environ.get(
    "OBSERVER_WORKSPACE",
    os.path.expanduser("~/.openclaw/workspace-observer")
))
CONFIG_DIR = WORKSPACE / "config"
ARCHIVE_DIR = WORKSPACE / "archive"
SCRIPTS_DIR = WORKSPACE / "scripts"
STATE_FILE = SCRIPTS_DIR / "state.json"

# LLM settings (override via env vars)
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://newapi.sms88.info/v1")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_FILTER_MODEL = os.environ.get("LLM_FILTER_MODEL", "gemini-2.0-flash")
LLM_SCORE_MODEL = os.environ.get("LLM_SCORE_MODEL", "gemini-2.0-flash")
LLM_EXTRACT_MODEL = os.environ.get("LLM_EXTRACT_MODEL", "gemini-2.0-flash")

# OpenViking MCP endpoint for indexing
OPENVIKING_MCP_URL = os.environ.get("OPENVIKING_MCP_URL", "http://127.0.0.1:2033/mcp")

# Telegram push
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID", "")
TG_PROXY = os.environ.get("TG_PROXY", "")

# Pipeline settings
SAMPLE_RATE = 0.23
TIER1_BATCH = 20
TIER2_BATCH = 10
DEFAULT_SCORE = 50
MAX_ITEMS_PER_SOURCE = 10
DEDUP_WINDOW_DAYS = 30
LLM_DELAY = 0.5  # seconds between API calls

PROXY = os.environ.get("HTTPS_PROXY", os.environ.get("HTTP_PROXY", ""))


# ── Helpers ────────────────────────────────────────────────────

def md5(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()[:12]


def load_state() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"seen": {}, "last_run": None, "run_count": 0}


def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    # Purge entries older than DEDUP_WINDOW_DAYS
    cutoff = (datetime.now() - timedelta(days=DEDUP_WINDOW_DAYS)).isoformat()
    state["seen"] = {
        k: v for k, v in state["seen"].items()
        if v.get("ts", "") >= cutoff
    }
    state["last_run"] = datetime.now().isoformat()
    state["run_count"] = state.get("run_count", 0) + 1
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def llm_call(model: str, system_prompt: str, user_prompt: str) -> str:
    """Call LLM via OpenAI-compatible API."""
    if not LLM_API_KEY:
        print("  WARN: LLM_API_KEY not set, skipping LLM call")
        return ""

    url = f"{LLM_BASE_URL}/chat/completions"
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 4096
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
        resp = opener.open(req, timeout=60)
        data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"  LLM error: {e}")
        return ""


def tg_push(text: str):
    """Push message via Telegram bot."""
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        return
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
    except Exception as e:
        print(f"  TG push error: {e}")


def index_to_openviking(filepath: str):
    """Index a file to OpenViking via MCP."""
    try:
        payload = json.dumps({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "add_resource",
                "arguments": {"resource_path": filepath}
            },
            "id": 1
        }).encode()
        req = urllib.request.Request(
            OPENVIKING_MCP_URL,
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        opener = urllib.request.build_opener()
        opener.open(req, timeout=30)
    except Exception as e:
        print(f"  OpenViking index error: {e}")


# ── Source Loading ─────────────────────────────────────────────

def load_rss_sources() -> list:
    """Load RSS feed URLs from config/sources.yaml."""
    sources_file = CONFIG_DIR / "sources.yaml"
    if not sources_file.exists():
        print(f"  WARN: {sources_file} not found")
        return []
    with open(sources_file) as f:
        data = yaml.safe_load(f) or {}
    feeds = []
    for category, items in data.items():
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    feeds.append(item)
                elif isinstance(item, str):
                    feeds.append({"url": item, "name": item, "category": category})
    return feeds


def load_web_sources() -> list:
    """Load web scraper configs from config/web_sources.yaml."""
    ws_file = CONFIG_DIR / "web_sources.yaml"
    if not ws_file.exists():
        return []
    with open(ws_file) as f:
        return list((yaml.safe_load(f) or {}).values())


def fetch_rss(feed: dict) -> list:
    """Fetch and parse an RSS feed."""
    url = feed.get("url", "")
    name = feed.get("name", url)
    try:
        parsed = feedparser.parse(url)
        items = []
        for entry in parsed.entries[:MAX_ITEMS_PER_SOURCE]:
            title = entry.get("title", "").strip()
            link = entry.get("link", "")
            summary = entry.get("summary", entry.get("description", ""))[:300]
            if title and link:
                items.append({
                    "title": title,
                    "link": link,
                    "summary": re.sub(r"<[^>]+>", "", summary).strip(),
                    "source": name,
                    "published": entry.get("published", ""),
                })
        return items
    except Exception as e:
        print(f"  RSS error [{name}]: {e}")
        return []


def fetch_web_source(config: dict) -> list:
    """Fetch items from a web source using simple scraping."""
    # Placeholder — in production, use BeautifulSoup + requests
    # See config/web_sources.yaml for CSS selector configs
    return []


# ── Pipeline Stages ────────────────────────────────────────────

def dedup(items: list, state: dict) -> list:
    """Remove already-seen items via MD5 hash."""
    unique = []
    for item in items:
        key = md5(f"{item['link']}|{item['title']}")
        if key not in state["seen"]:
            unique.append(item)
            item["_hash"] = key
    return unique


def sample(items: list, rate: float, full: bool = False) -> list:
    """Random sample ~23% of items per run."""
    if full or len(items) <= 5:
        return items
    n = max(1, int(len(items) * rate))
    return random.sample(items, n)


def tier1_filter(items: list) -> list:
    """Tier-1: Topic matching via fast LLM."""
    if not items:
        return []

    interests_file = CONFIG_DIR / "interests.md"
    interests = ""
    if interests_file.exists():
        interests = interests_file.read_text()

    system = (
        "你是信息过滤器。判断每条信息是否与用户的任意一个关注方向相关。\n"
        "只返回相关条目的 ID，每行一个。无相关返回 NONE。不要解释。\n\n"
        f"用户关注方向:\n{interests}"
    )

    passed = []
    for i in range(0, len(items), TIER1_BATCH):
        batch = items[i:i + TIER1_BATCH]
        user = "\n".join(
            f"[{j}] {it['title']} — {it['summary'][:150]}"
            for j, it in enumerate(batch)
        )
        result = llm_call(LLM_FILTER_MODEL, system, user)
        if not result or "NONE" in result.upper():
            continue

        # Parse IDs
        try:
            ids = set()
            for line in result.strip().split("\n"):
                line = line.strip().strip("[]")
                if line.isdigit():
                    ids.add(int(line))
            passed.extend(batch[j] for j in ids if j < len(batch))
        except Exception:
            passed.extend(batch)  # Conservative: pass all on parse error

        time.sleep(LLM_DELAY)

    return passed


def tier2_score(items: list) -> list:
    """Tier-2: Multi-dimensional scoring."""
    if not items:
        return []

    scoring_file = CONFIG_DIR / "scoring.md"
    scoring_rules = ""
    if scoring_file.exists():
        scoring_rules = scoring_file.read_text()

    system = (
        "Rate each article 0-100. Rules:\n"
        f"{scoring_rules}\n\n"
        "Reply format (one line per article):\n"
        "ID|score|reason(max 10 words)|tag1,tag2"
    )

    for i in range(0, len(items), TIER2_BATCH):
        batch = items[i:i + TIER2_BATCH]
        user = "\n\n".join(
            f"[{j}] {it['title']}\nSource: {it['source']}\n{it['summary'][:300]}"
            for j, it in enumerate(batch)
        )
        result = llm_call(LLM_SCORE_MODEL, system, user)
        if not result:
            for it in batch:
                it["score"] = DEFAULT_SCORE
                it["reason"] = "scoring unavailable"
                it["tags"] = []
            continue

        # Parse scores
        scores = {}
        for line in result.strip().split("\n"):
            parts = line.strip().split("|")
            if len(parts) >= 2:
                try:
                    idx = int(parts[0].strip().strip("[]"))
                    score = int(parts[1].strip())
                    reason = parts[2].strip() if len(parts) > 2 else ""
                    tags = parts[3].strip().split(",") if len(parts) > 3 else []
                    scores[idx] = (score, reason, tags)
                except (ValueError, IndexError):
                    pass

        for j, it in enumerate(batch):
            if j in scores:
                it["score"], it["reason"], it["tags"] = scores[j]
            else:
                it["score"] = DEFAULT_SCORE
                it["reason"] = "parse error"
                it["tags"] = []

        time.sleep(LLM_DELAY)

    return items


def extract_card(item: dict) -> str:
    """Extract a structured knowledge card via LLM."""
    system = (
        "Extract a structured knowledge card in YAML+Markdown format.\n"
        "Output format:\n"
        "---\n"
        "title: <title>\n"
        "source: <source>\n"
        "url: <url>\n"
        "date: <YYYY-MM-DD>\n"
        "topics: [topic1, topic2]\n"
        "score: <score>\n"
        "---\n"
        "## Highlights\n- point1\n- point2\n- point3\n\n"
        "## Entities\n- entity1\n- entity2\n\n"
        "## Key Data\n- datapoint1\n\n"
        "## Golden Quote\n> one-sentence summary (14-28 chars)\n\n"
        "## Summary\n3-5 sentence summary."
    )
    user = (
        f"Title: {item['title']}\n"
        f"Source: {item['source']}\n"
        f"URL: {item['link']}\n"
        f"Score: {item.get('score', 0)}\n"
        f"Content:\n{item['summary']}"
    )
    return llm_call(LLM_EXTRACT_MODEL, system, user)


def archive_item(item: dict, card_text: str, state: dict) -> str:
    """Save knowledge card to archive and update state."""
    today = datetime.now().strftime("%Y-%m")
    archive_month = ARCHIVE_DIR / today
    archive_month.mkdir(parents=True, exist_ok=True)

    safe_title = re.sub(r"[^\w\u4e00-\u9fff-]", "_", item["title"])[:50]
    filename = f"{item['_hash']}_{safe_title}.md"
    filepath = archive_month / filename

    if not card_text:
        # Fallback: simple card
        card_text = (
            f"---\ntitle: \"{item['title']}\"\n"
            f"source: \"{item['source']}\"\n"
            f"url: \"{item['link']}\"\n"
            f"date: \"{datetime.now().strftime('%Y-%m-%d')}\"\n"
            f"score: {item.get('score', 0)}\n---\n\n"
            f"## Summary\n{item['summary']}\n"
        )

    filepath.write_text(card_text, encoding="utf-8")

    # Update state
    state["seen"][item["_hash"]] = {
        "t": item["title"],
        "s": item.get("score", 0),
        "ts": datetime.now().isoformat()
    }

    return str(filepath)


# ── Main Pipeline ──────────────────────────────────────────────

def run(args):
    now = datetime.now()
    print(f"\n{'='*60}")
    print(f"Observer Collection — {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    state = load_state()
    print(f"  Run #{state.get('run_count', 0) + 1}, seen: {len(state['seen'])} items")

    # 1. Fetch sources
    print("\n[1/6] Fetching sources...")
    rss_sources = load_rss_sources()
    all_items = []
    for feed in rss_sources:
        items = fetch_rss(feed)
        all_items.extend(items)
    print(f"  Fetched {len(all_items)} items from {len(rss_sources)} RSS feeds")

    # Web sources (placeholder)
    web_sources = load_web_sources()
    if web_sources:
        print(f"  {len(web_sources)} web scrapers configured (install bs4 to enable)")

    if args.feed_only:
        print("\n  --feed-only mode, stopping here.")
        return

    # 2. Dedup
    print("\n[2/6] Deduplication...")
    unique = dedup(all_items, state)
    print(f"  {len(all_items)} → {len(unique)} after dedup")

    # 3. Sample
    print("\n[3/6] Sampling...")
    sampled = sample(unique, SAMPLE_RATE, full=args.full)
    print(f"  {len(unique)} → {len(sampled)} (rate: {SAMPLE_RATE if not args.full else 1.0})")

    if not sampled:
        print("\n  No items to process. Done.")
        save_state(state)
        return

    # 4. Tier-1 filter
    print("\n[4/6] Tier-1 Topic Matching...")
    passed = tier1_filter(sampled)
    print(f"  {len(sampled)} → {len(passed)} passed topic filter")

    # 5. Tier-2 scoring
    print("\n[5/6] Tier-2 Scoring...")
    scored = tier2_score(passed)
    high = [i for i in scored if i.get("score", 0) >= 85]
    medium = [i for i in scored if 70 <= i.get("score", 0) < 85]
    low = [i for i in scored if 50 <= i.get("score", 0) < 70]
    discard = [i for i in scored if i.get("score", 0) < 50]
    print(f"  ≥85: {len(high)} | 70-84: {len(medium)} | 50-69: {len(low)} | <50: {len(discard)}")

    if args.dry_run:
        print("\n  --dry-run mode, not archiving.")
        for item in sorted(scored, key=lambda x: x.get("score", 0), reverse=True):
            print(f"  [{item.get('score', '?'):>3}] {item['title'][:60]} — {item.get('reason', '')}")
        return

    # 6. Extract & Archive
    print("\n[6/6] Extracting & Archiving...")
    archived = 0
    for item in scored:
        if item.get("score", 0) < 50:
            continue

        card_text = ""
        if item.get("score", 0) >= 70:
            card_text = extract_card(item)
            time.sleep(LLM_DELAY)

        filepath = archive_item(item, card_text, state)
        archived += 1

        # Index to OpenViking
        index_to_openviking(filepath)

        # Push high-score via Telegram
        if item.get("score", 0) >= 85:
            msg = (
                f"🔥 *High-score signal [{item['score']}]*\n\n"
                f"*{item['title']}*\n"
                f"Source: {item['source']}\n"
                f"Reason: {item.get('reason', '')}\n"
                f"Tags: {', '.join(item.get('tags', []))}\n\n"
                f"[Link]({item['link']})"
            )
            tg_push(msg)

    print(f"  Archived: {archived} items")
    save_state(state)
    print(f"\nDone. Total seen: {len(state['seen'])}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Observer Collection Pipeline")
    parser.add_argument("--full", action="store_true", help="Full collection (no sampling)")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no archive")
    parser.add_argument("--feed-only", action="store_true", help="Show feed counts only")
    args = parser.parse_args()
    run(args)
