#!/usr/bin/env python3
"""
Observer Collection Pipeline — Two-Tier AI Filtering
=====================================================
Pipeline:
  Sources -> Dedup -> Sample 23% -> Tier-1 Topic Match (Flash)
  -> Tier-2 Multi-dim Score (Flash) -> Extract (>=70) -> Archive -> Push (>=85)

Usage:
  python collect.py              # Normal mode (~23% sampling)
  python collect.py --full       # Full collection (no sampling)
  python collect.py --dry-run    # Preview only, no archive
  python collect.py --feed-only  # Show feed counts only
"""

import hashlib
import json
import os
import random
import re
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from html import unescape
from pathlib import Path

import feedparser
import yaml

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    import urllib.request
    import urllib.error
    HAS_HTTPX = False

try:
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

# -- Configuration ----------------------------------------------------------

WORKSPACE = Path(os.environ.get(
    "OBSERVER_WORKSPACE",
    os.path.expanduser("~/.openclaw/workspace-observer")
))
CONFIG_DIR = WORKSPACE / "config"
ARCHIVE_DIR = WORKSPACE / "archive"
MEMORY_DIR = WORKSPACE / "memory"
SCRIPTS_DIR = WORKSPACE / "scripts"
STATE_FILE = SCRIPTS_DIR / "state.json"
LOG_FILE = SCRIPTS_DIR / "collect.log"

LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://newapi.sms88.info/v1")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_FILTER_MODEL = os.environ.get("LLM_FILTER_MODEL", "gemini-2.0-flash")
LLM_SCORE_MODEL = os.environ.get("LLM_SCORE_MODEL", "gemini-2.0-flash")
LLM_EXTRACT_MODEL = os.environ.get("LLM_EXTRACT_MODEL", "gemini-2.0-flash")

OPENVIKING_MCP_URL = os.environ.get(
    "OPENVIKING_MCP_URL", "http://127.0.0.1:2033/mcp")

SAMPLE_RATE = 0.23
MAX_ENTRIES_PER_FEED = 10
FETCH_TIMEOUT = 15
DEDUP_WINDOW_DAYS = 30
LLM_DELAY = 0.5

CST = timezone(timedelta(hours=8))


def log(msg: str):
    ts = datetime.now(CST).strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


# -- HTTP Helpers ------------------------------------------------------------

def _http_get(url: str, timeout: int = FETCH_TIMEOUT, headers: dict = None):
    if HAS_HTTPX:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            return client.get(url, headers=headers or {})
    else:
        req = urllib.request.Request(url, headers=headers or {})
        resp = urllib.request.urlopen(req, timeout=timeout)

        class _Resp:
            def __init__(self, r):
                self.status_code = r.status
                self._data = r.read()
                self.text = self._data.decode("utf-8", errors="replace")

            def json(self):
                return json.loads(self._data)

        return _Resp(resp)


def _llm_call(model: str, system: str, user: str,
              temperature: float = 0.3, max_tokens: int = 4096) -> str:
    if not LLM_API_KEY:
        log("  WARN: LLM_API_KEY not set, skipping LLM call")
        return ""

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }

    if HAS_HTTPX:
        with httpx.Client(timeout=90) as client:
            resp = client.post(f"{LLM_BASE_URL}/chat/completions",
                               json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
    else:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{LLM_BASE_URL}/chat/completions", data=data, headers=headers)
        resp = urllib.request.urlopen(req, timeout=90)
        return json.loads(
            resp.read())["choices"][0]["message"]["content"].strip()


# -- State -------------------------------------------------------------------

def entry_id(link: str, title: str) -> str:
    return hashlib.md5(f"{link}|{title}".encode()).hexdigest()[:12]


def load_state() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"seen": {}, "last_run": None, "run_count": 0}


def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    cutoff = (
        datetime.now(CST) - timedelta(days=DEDUP_WINDOW_DAYS)).isoformat()
    state["seen"] = {
        k: v for k, v in state["seen"].items()
        if v.get("ts", "") > cutoff
    }
    state["last_run"] = datetime.now(CST).isoformat()
    state["run_count"] = state.get("run_count", 0) + 1
    tmp = STATE_FILE.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    tmp.rename(STATE_FILE)


def strip_html(html: str) -> str:
    if not html:
        return ""
    text = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html,
                  flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


# -- Source Loading ----------------------------------------------------------

def _parse_sources_md() -> list:
    """Parse RSS sources from sources.md (table format with backtick URLs)."""
    sources_file = CONFIG_DIR / "sources.md"
    if not sources_file.exists():
        return []

    content = sources_file.read_text()
    sources = []

    for line in content.split("\n"):
        if "|" not in line or line.strip().startswith("|--"):
            continue

        feed_match = re.search(
            r'`([^`]*(?:feed|rss|atom|localhost:\d+/)[^`]*)`',
            line, re.IGNORECASE)
        if not feed_match:
            continue

        feed_url = feed_match.group(1).strip()
        if not feed_url.startswith("http"):
            feed_url = "https://" + feed_url

        cols = [c.strip() for c in line.split("|") if c.strip()]
        name = cols[0] if cols else "Unknown"

        url_match = re.search(r'https?://[^\s|`]+', line)
        site_url = url_match.group(0).rstrip("/") if url_match else ""
        if site_url == feed_url:
            site_url = ""

        sources.append({
            "name": name,
            "url": site_url or feed_url,
            "rss": feed_url,
        })

    return sources


def _parse_sources_yaml() -> list:
    """Parse RSS sources from sources.yaml (legacy format)."""
    sources_file = CONFIG_DIR / "sources.yaml"
    if not sources_file.exists():
        return []
    with open(sources_file) as f:
        data = yaml.safe_load(f) or {}
    feeds = []
    for category, items in data.items():
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict) and item.get("url"):
                    feeds.append({
                        "name": item.get("name", item["url"]),
                        "url": item["url"],
                        "rss": item["url"],
                    })
                elif isinstance(item, str):
                    feeds.append({"name": item, "url": item, "rss": item})
    return feeds


def load_rss_sources() -> list:
    """Load RSS sources, preferring sources.md over sources.yaml."""
    sources = _parse_sources_md()
    if sources:
        return sources
    return _parse_sources_yaml()


def load_interests() -> str:
    path = CONFIG_DIR / "interests.md"
    return path.read_text() if path.exists() else ""


# -- Extra Sources: HN + GitHub Trending ------------------------------------

def fetch_hn_top(count: int = 15, state: dict = None) -> list:
    """Fetch Hacker News Top Stories via Firebase API."""
    entries = []
    try:
        ids_resp = _http_get(
            "https://hacker-news.firebaseio.com/v0/topstories.json")
        ids = ids_resp.json()[:count]
        for sid in ids:
            item_resp = _http_get(
                f"https://hacker-news.firebaseio.com/v0/item/{sid}.json")
            item = item_resp.json()
            if not item or item.get("type") != "story":
                continue
            title = item.get("title", "")
            link = item.get(
                "url", f"https://news.ycombinator.com/item?id={sid}")
            eid = entry_id(link, title)
            if state and eid in state.get("seen", {}):
                continue
            entries.append({
                "id": eid,
                "source": "Hacker News",
                "source_url": "https://news.ycombinator.com",
                "title": title,
                "link": link,
                "summary": (f"HN score: {item.get('score', 0)}, "
                            f"comments: {item.get('descendants', 0)}"),
                "published": "",
            })
        log(f"  Hacker News: {len(entries)} new items")
    except Exception as e:
        log(f"  WARN Hacker News: {e}")
    return entries


def fetch_github_trending(state: dict = None) -> list:
    """Fetch trending repos via GitHub Search API."""
    entries = []
    try:
        yesterday = (
            datetime.now(CST) - timedelta(days=1)).strftime("%Y-%m-%d")
        url = (
            "https://api.github.com/search/repositories"
            f"?q=created:>{yesterday}+stars:>10"
            "&sort=stars&order=desc&per_page=10"
        )
        resp = _http_get(
            url, headers={"Accept": "application/vnd.github.v3+json"})
        if resp.status_code != 200:
            log(f"  WARN GitHub Trending: HTTP {resp.status_code}")
            return entries
        data = resp.json()
        for repo in (data.get("items") or []):
            if not isinstance(repo, dict):
                continue
            desc = repo.get("description") or "(no desc)"
            title = f"{repo.get('full_name', '?')}: {desc}"
            link = repo["html_url"]
            eid = entry_id(link, title)
            if state and eid in state.get("seen", {}):
                continue
            entries.append({
                "id": eid,
                "source": "GitHub Trending",
                "source_url": "https://github.com/trending",
                "title": title[:200],
                "link": link,
                "summary": (
                    f"Stars: {repo.get('stargazers_count', 0)} | "
                    f"{repo.get('language') or ''} | {desc[:300]}"),
                "published": repo.get("created_at", ""),
            })
        log(f"  GitHub Trending: {len(entries)} new items")
    except Exception as e:
        log(f"  WARN GitHub Trending: {e}")
    return entries


# -- RSS Fetching ------------------------------------------------------------

def fetch_feeds(sources: list, state: dict) -> list:
    entries = []
    for src in sources:
        try:
            feed = feedparser.parse(src["rss"])
            if feed.bozo and not feed.entries:
                log(f"  WARN {src['name']}: feed parse failed")
                continue

            count = 0
            for entry in feed.entries[:MAX_ENTRIES_PER_FEED]:
                link = getattr(entry, "link", "")
                title = getattr(entry, "title", "")
                eid = entry_id(link, title)
                if eid in state["seen"]:
                    continue

                raw = (getattr(entry, "summary", "")
                       or getattr(entry, "description", ""))
                summary = strip_html(raw)[:500]

                entries.append({
                    "id": eid,
                    "source": src["name"],
                    "source_url": src.get("url", ""),
                    "title": unescape(title),
                    "link": link,
                    "summary": summary,
                    "published": getattr(entry, "published", ""),
                })
                count += 1

            if count > 0:
                log(f"  {src['name']}: {count} new items")
        except Exception as e:
            log(f"  WARN {src['name']}: {e}")

    return entries


# -- Web Scraper -------------------------------------------------------------

def fetch_web_sources(state: dict) -> list:
    """Fetch items from web sources configured in web_sources.yaml."""
    config_file = CONFIG_DIR / "web_sources.yaml"
    if not config_file.exists():
        return []
    if not HAS_BS4:
        log("  WARN: beautifulsoup4 not installed, skipping web sources")
        return []

    with open(config_file) as f:
        config = yaml.safe_load(f) or {}

    entries = []
    sites = config.get("sites", config)
    if isinstance(sites, dict):
        for key, site in sites.items():
            if not isinstance(site, dict) or not site.get("url"):
                continue
            try:
                items = _scrape_site(site, state)
                entries.extend(items)
                if items:
                    log(f"  {site.get('name', key)}: {len(items)} new items")
            except Exception as e:
                log(f"  WARN {site.get('name', key)}: {e}")
    return entries


def _scrape_site(site: dict, state: dict) -> list:
    timeout = site.get("timeout", 15)
    verify = site.get("verify_ssl", True)
    ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Observer/1.0"

    if HAS_HTTPX:
        with httpx.Client(timeout=timeout, follow_redirects=True,
                          verify=verify) as client:
            resp = client.get(site["url"], headers={"User-Agent": ua})
            if resp.status_code != 200:
                return []
            html = resp.text
    else:
        req = urllib.request.Request(
            site["url"], headers={"User-Agent": ua})
        resp = urllib.request.urlopen(req, timeout=timeout)
        html = resp.read().decode("utf-8", errors="replace")

    soup = BeautifulSoup(html, "html.parser")
    base_url = site.get("base_url", site["url"])
    max_items = site.get("max_items", 15)
    items_raw = soup.select(site["list_selector"])

    if site.get("skip_styled"):
        items_raw = [i for i in items_raw if not i.get("style")]

    entries = []
    seen_links = set()
    for el in items_raw[:max_items * 2]:
        link_sel = site.get("link_selector", "a")
        link_el = el.select_one(link_sel) if link_sel else el
        if not link_el:
            continue
        href = link_el.get(site.get("link_attr", "href"), "")
        if not href or href == "#":
            continue
        link = urljoin(base_url + "/", href)
        if link in seen_links:
            continue
        seen_links.add(link)

        title_from = site.get("title_from", "text")
        if title_from == "text":
            title = (link_el.get_text(strip=True)
                     or link_el.get("title", ""))
        elif title_from.startswith("attr:"):
            attr_name = title_from.split(":", 1)[1]
            title = (link_el.get(attr_name, "")
                     or link_el.get_text(strip=True))
        elif title_from.startswith("a["):
            a_el = el.select_one("a")
            title = (a_el.get("title", a_el.get_text(strip=True))
                     if a_el else "")
        else:
            title = link_el.get_text(strip=True)
        title = " ".join(title.split())[:200]

        suffix = site.get("title_strip_suffix")
        if suffix and title.endswith(suffix):
            title = title[:-len(suffix)]
        if not title:
            continue

        date_str = ""
        if site.get("date_selector"):
            date_el = el.select_one(site["date_selector"])
            if date_el:
                date_str = date_el.get_text(strip=True)
                for ch in site.get("date_strip", ""):
                    date_str = date_str.replace(ch, "").strip()

        eid = entry_id(link, title)
        if eid in state["seen"]:
            continue

        entries.append({
            "id": eid,
            "source": site.get("name", "Web"),
            "source_url": site["url"],
            "title": unescape(title),
            "link": link,
            "summary": "",
            "published": date_str,
        })
        if len(entries) >= max_items:
            break

    return entries


# -- Article Text ------------------------------------------------------------

def fetch_article_text(url: str) -> str:
    if not url:
        return ""
    try:
        ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Observer/1.0"
        resp = _http_get(url, headers={"User-Agent": ua})
        if resp.status_code != 200:
            return ""
        html = resp.text
        article = re.search(
            r'<(article|main)[^>]*>(.*?)</\1>', html,
            re.DOTALL | re.IGNORECASE)
        if article:
            return strip_html(article.group(2))[:3000]
        body = re.search(
            r'<body[^>]*>(.*?)</body>', html,
            re.DOTALL | re.IGNORECASE)
        if body:
            return strip_html(body.group(1))[:3000]
        return strip_html(html)[:3000]
    except Exception:
        return ""


# -- Pipeline Stages ---------------------------------------------------------

def tier1_filter(entries: list, interests: str) -> list:
    if not entries:
        return []

    passed = []
    for i in range(0, len(entries), 20):
        batch = entries[i:i + 20]
        items = "\n".join(
            f"[{e['id']}] {e['title']}"
            + (f" — {e['summary'][:150]}" if e.get("summary") else "")
            for e in batch
        )

        system = (
            "你是信息过滤器。判断每条信息是否与用户的任意一个关注方向相关。"
            "只返回相关条目的 ID，每行一个。无相关返回 NONE。不要解释。"
        )
        user_msg = (
            f"## 关注方向\n{interests}\n\n"
            f"## 待过滤\n{items}\n\n相关 ID："
        )

        try:
            result = _llm_call(LLM_FILTER_MODEL, system, user_msg,
                               temperature=0.1, max_tokens=1024)
            if not result or "NONE" in result.upper():
                continue
            ids = set(
                line.strip().strip("[]")
                for line in result.strip().split("\n") if line.strip()
            )
            passed.extend(e for e in batch if e["id"] in ids)
        except Exception as e:
            log(f"  WARN Tier-1 error: {e}")
            passed.extend(batch)

        time.sleep(LLM_DELAY)

    return passed


SCORING_PROMPT = (
    "Rate each article 0-100. Rules: "
    "originality(+20), new-insight(+15), actionability(+15), "
    "data-driven(+10), info-density(+10), insider(+10), "
    "timeliness(+10), readability(+5), scarcity(+5). "
    "Deductions: marketing(-30), clickbait(-20), one-sided(-15), "
    "AI-slop(-15), repeat(-20), no-evidence(-10), too-obscure(-10).\n\n"
    "Reply format, one line per article (NO other text):\n"
    "ID|score|reason(max 10 words)|tag1,tag2"
)


def tier2_score(entries: list) -> list:
    if not entries:
        return []

    scored = []
    for i in range(0, len(entries), 10):
        batch = entries[i:i + 10]
        items = "\n".join(
            f"[{e['id']}] {e['title']} ({e['source']})"
            + (f" — {e['summary'][:120]}" if e.get("summary") else "")
            for e in batch
        )

        try:
            result = _llm_call(LLM_SCORE_MODEL, "",
                               f"{SCORING_PROMPT}\n\nArticles:\n{items}",
                               temperature=0.2, max_tokens=1024)
            parsed_ids = set()
            for line in result.strip().split("\n"):
                if "|" not in line:
                    continue
                parts = [p.strip() for p in line.split("|")]
                if len(parts) < 3:
                    continue
                eid = parts[0]
                try:
                    score = int(parts[1])
                except (ValueError, IndexError):
                    continue
                reason = parts[2] if len(parts) > 2 else ""
                tags = ([t.strip() for t in parts[3].split(",")]
                        if len(parts) > 3 else [])

                for e in batch:
                    if e["id"] == eid:
                        e["score"] = max(0, min(100, score))
                        e["score_reason"] = reason
                        e["topics"] = tags
                        parsed_ids.add(eid)
                        break

            for e in batch:
                if e["id"] not in parsed_ids:
                    e["score"] = 50
                    e["score_reason"] = "not scored by model"
                    e["topics"] = []
            scored.extend(batch)
        except Exception as e:
            log(f"  WARN Tier-2 error: {e}")
            for entry in batch:
                entry["score"] = 50
                entry["score_reason"] = str(e)
                entry["topics"] = []
            scored.extend(batch)

        time.sleep(LLM_DELAY)

    return scored


def extract_card(entry: dict) -> str:
    full_text = fetch_article_text(entry.get("link", ""))
    if not full_text:
        full_text = entry.get("summary", "")

    today = datetime.now(CST).strftime("%Y-%m-%d")

    system = (
        "你是 Observer，情报分析师。将文章萃取为知识卡片。"
        "输出纯 YAML（不要 ```yaml 标记，不要 --- 分隔符），格式如下：\n"
        "title: 去标题党化的真实标题\n"
        "source: 信源名称\n"
        "url: 原文链接\n"
        f"date: {today}\n"
        "topics: [标签1, 标签2]\n"
        "score: 分数\n"
        "highlights:\n"
        "  - 核心信息1\n"
        "  - 核心信息2\n"
        "  - 核心信息3\n"
        "entities:\n"
        "  people: [人名1]\n"
        "  orgs: [机构1]\n"
        "  products: [产品1]\n"
        "datapoints:\n"
        "  - 具体数据点\n"
        "quotes:\n"
        "  - 原文关键句\n"
        "golden_quote: 14-28字金句\n"
        "action: none 或 alert 或 analyze\n"
        "summary: 3-5句摘要\n"
    )
    user_msg = (
        f"标题: {entry['title']}\n来源: {entry['source']}\n"
        f"链接: {entry['link']}\n评分: {entry.get('score', 'N/A')}\n"
        f"评分理由: {entry.get('score_reason', '')}\n\n"
        f"## 内容\n{full_text[:3000]}\n\n请萃取："
    )

    try:
        raw = _llm_call(LLM_EXTRACT_MODEL, system, user_msg,
                        temperature=0.2, max_tokens=2048)
        raw = re.sub(r'^```ya?ml\s*', '', raw.strip())
        raw = re.sub(r'\s*```$', '', raw.strip())
        yaml.safe_load(raw)
        return f"---\n{raw}\n---"
    except Exception as e:
        log(f"  WARN extract error [{entry['id']}]: {e}")
        return (
            f"---\n"
            f"title: \"{entry['title']}\"\n"
            f"source: \"{entry['source']}\"\n"
            f"url: \"{entry['link']}\"\n"
            f"date: \"{today}\"\n"
            f"score: {entry.get('score', 50)}\n"
            f"topics: "
            f"{json.dumps(entry.get('topics', []), ensure_ascii=False)}\n"
            f"highlights:\n"
            f"  - \"{entry.get('summary', '')[:200]}\"\n"
            f"action: none\n"
            f"---"
        )


# -- Archive & Push ----------------------------------------------------------

def archive_card(entry: dict, card: str) -> Path:
    today = datetime.now(CST)
    month_dir = ARCHIVE_DIR / today.strftime("%Y-%m")
    month_dir.mkdir(parents=True, exist_ok=True)
    safe_title = re.sub(
        r'[^\w\u4e00-\u9fff-]', '_', entry['title'][:30]).strip('_')
    filename = f"{entry['id']}_{safe_title}.md"
    filepath = month_dir / filename
    filepath.write_text(card, encoding="utf-8")
    return filepath


def archive_simple(entry: dict) -> Path:
    today = datetime.now(CST).strftime("%Y-%m-%d")
    card = (
        f"---\n"
        f"title: \"{entry['title']}\"\n"
        f"source: \"{entry['source']}\"\n"
        f"url: \"{entry['link']}\"\n"
        f"date: \"{today}\"\n"
        f"score: {entry.get('score', 50)}\n"
        f"topics: "
        f"{json.dumps(entry.get('topics', []), ensure_ascii=False)}\n"
        f"---\n\n"
        f"{entry.get('summary', '')[:300]}\n"
    )
    return archive_card(entry, card)


def push_to_openviking(filepath: Path):
    try:
        payload = {
            "jsonrpc": "2.0",
            "id": f"ov-{filepath.stem[:12]}",
            "method": "tools/call",
            "params": {
                "name": "add_resource",
                "arguments": {"resource_path": str(filepath)},
            },
        }
        if HAS_HTTPX:
            with httpx.Client(timeout=30) as client:
                resp = client.post(
                    OPENVIKING_MCP_URL, json=payload,
                    headers={
                        "Accept": "application/json, text/event-stream"})
                data = resp.json()
        else:
            req_data = json.dumps(payload).encode()
            req = urllib.request.Request(
                OPENVIKING_MCP_URL, data=req_data,
                headers={"Content-Type": "application/json"})
            resp = urllib.request.urlopen(req, timeout=30)
            data = json.loads(resp.read())

        text = str(
            data.get("result", {}).get("content", [{}])[0].get("text", ""))
        if "indexed" in text or "added" in text:
            log(f"   OpenViking indexed: {filepath.name}")
    except Exception as e:
        log(f"   WARN OpenViking index failed: {e}")


def push_to_im(entry: dict):
    score = entry.get("score", 0)
    topics = ", ".join(entry.get("topics", []))
    msg = (f"Observer Alert [{score}]\n\n"
           f"{entry['title']}\nSource: {entry['source']}\n")
    if topics:
        msg += f"Tags: {topics}\n"
    msg += f"\n{entry.get('score_reason', '')}\n\n{entry['link']}"

    try:
        subprocess.run(
            ["openclaw", "agent", "--agent", "main",
             "--channel", "telegram", "--deliver", "-m", msg],
            capture_output=True, text=True, timeout=60,
        )
        log(f"  Pushed: {entry['title'][:40]}")
    except FileNotFoundError:
        log("  WARN: openclaw CLI not found, skipping push")
    except Exception as e:
        log(f"  WARN push failed: {e}")


# -- Collection Log ---------------------------------------------------------

def write_collection_log(stats: dict):
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(CST)
    log_file = MEMORY_DIR / f"{today.strftime('%Y-%m-%d')}.md"

    section = (
        f"\n## {today.strftime('%H:%M')} Collection\n\n"
        f"- Sampled: {stats['sampled']}/{stats['total_rss']} sources\n"
        f"- New items: {stats['new']}\n"
        f"- Tier-1 passed: {stats['t1']}\n"
        f"- Tier-2 scored: {stats['t2']}\n"
        f"- Pushed (85+): {stats['pushed']}\n"
        f"- Daily (70-84): {stats['daily']}\n"
        f"- Archived (50-69): {stats['archived']}\n"
        f"- Dropped (<50): {stats['dropped']}\n"
    )

    if stats.get("items"):
        section += "\n| Score | Title | Source |\n|------|------|------|\n"
        for e in stats["items"]:
            section += (f"| {e.get('score', '?')} "
                        f"| {e['title'][:40]} | {e['source']} |\n")

    if log_file.exists():
        with open(log_file, "a") as f:
            f.write(section)
    else:
        header = f"# {today.strftime('%Y-%m-%d')} Observer Log\n"
        log_file.write_text(header + section, encoding="utf-8")


# -- Main Pipeline -----------------------------------------------------------

def run(full: bool = False, dry_run: bool = False, feed_only: bool = False):
    log(f"{'='*50}")
    log("Observer Collection Pipeline")
    log(f"  Mode: {'full' if full else 'sampled'}"
        f"{' (dry-run)' if dry_run else ''}")
    log(f"{'='*50}")

    state = load_state()
    all_sources = load_rss_sources()
    interests = load_interests()

    log(f"RSS sources: {len(all_sources)}")

    if full:
        sources = all_sources
    else:
        n = max(2, int(len(all_sources) * SAMPLE_RATE))
        sources = random.sample(all_sources, min(n, len(all_sources)))
    log(f"This round: {len(sources)} sources")
    for s in sources:
        log(f"  - {s['name']}")

    log("\nFetching RSS...")
    entries = fetch_feeds(sources, state)

    log("\nFetching web sources...")
    entries.extend(fetch_web_sources(state))

    log("\nFetching Hacker News...")
    entries.extend(fetch_hn_top(15, state))
    log("Fetching GitHub Trending...")
    entries.extend(fetch_github_trending(state))

    log(f"  Total new items: {len(entries)}")

    if feed_only:
        for e in entries:
            log(f"  [{e['source']}] {e['title']}")
        return

    if not entries:
        log("No new items")
        state["last_run"] = datetime.now(CST).isoformat()
        state["run_count"] += 1
        save_state(state)
        write_collection_log({
            "sampled": len(sources), "total_rss": len(all_sources),
            "new": 0, "t1": 0, "t2": 0, "pushed": 0,
            "daily": 0, "archived": 0, "dropped": 0,
        })
        return

    log(f"\nTier-1 Topic Matching ({LLM_FILTER_MODEL})...")
    passed = tier1_filter(entries, interests)
    log(f"  Passed: {len(passed)}/{len(entries)}")

    if not passed:
        log("No relevant items")
        for e in entries:
            state["seen"][e["id"]] = {
                "t": e["title"][:50],
                "ts": datetime.now(CST).isoformat(), "f": True}
        save_state(state)
        return

    log(f"\nTier-2 Scoring ({LLM_SCORE_MODEL})...")
    scored = tier2_score(passed)
    scored.sort(key=lambda x: x.get("score", 0), reverse=True)
    for e in scored:
        log(f"  [{e.get('score', '?'):>3}] {e['title'][:50]}")

    if dry_run:
        log("\nDry-run complete, not archiving/pushing")
        for e in entries:
            state["seen"][e["id"]] = {
                "t": e["title"][:50],
                "ts": datetime.now(CST).isoformat()}
        save_state(state)
        return

    pushed = daily = archived = dropped = 0

    for entry in scored:
        score = entry.get("score", 0)

        if score >= 70:
            log(f"\nExtracting: {entry['title'][:40]}...")
            card = extract_card(entry)
            archived_path = archive_card(entry, card)
            push_to_openviking(archived_path)
            time.sleep(1)

            if score >= 85:
                log(f"  Push (score={score})")
                push_to_im(entry)
                pushed += 1
            else:
                log(f"  Daily (score={score})")
                daily += 1

        elif score >= 50:
            archive_simple(entry)
            archived += 1
        else:
            dropped += 1

        state["seen"][entry["id"]] = {
            "t": entry["title"][:50],
            "s": score,
            "ts": datetime.now(CST).isoformat(),
        }

    for e in entries:
        if e["id"] not in state["seen"]:
            state["seen"][e["id"]] = {
                "t": e["title"][:50],
                "ts": datetime.now(CST).isoformat(), "f": True}

    save_state(state)
    write_collection_log({
        "sampled": len(sources), "total_rss": len(all_sources),
        "new": len(entries), "t1": len(passed), "t2": len(scored),
        "pushed": pushed, "daily": daily, "archived": archived,
        "dropped": dropped, "items": scored,
    })

    log(f"\n{'='*50}")
    log(f"Done — pushed:{pushed} daily:{daily}"
        f" archived:{archived} dropped:{dropped}")
    log(f"{'='*50}\n")


if __name__ == "__main__":
    args = set(sys.argv[1:])
    run(
        full="--full" in args,
        dry_run="--dry-run" in args,
        feed_only="--feed-only" in args,
    )
