# Architecture

## System Overview

```
                    ┌─────────────┐
                    │    User     │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
     ┌────────▼───┐  ┌────▼─────┐  ┌───▼──────────┐
     │  Telegram   │  │  钉钉    │  │  CLI / HTTP  │
     │  (N Bots)   │  │  Bridge  │  │              │
     └────────┬───┘  └────┬─────┘  └───┬──────────┘
              │            │            │
              └────────────┼────────────┘
                           │
                ┌──────────▼──────────┐
                │   OpenClaw Gateway  │
                │    :18789           │
                └──────────┬──────────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
     ┌────────▼───┐  ┌────▼─────┐  ┌───▼──────┐
     │   Nexus    │  │ Observer │  │  Agent N  │
     │   (main)   │  │          │  │           │
     └────────┬───┘  └────┬─────┘  └───┬──────┘
              │            │            │
              └────────────┼────────────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
     ┌────────▼───┐  ┌────▼─────┐  ┌───▼──────┐
     │   Shared   │  │OpenViking│  │  Memory   │
     │  STATE.yaml│  │  :2033   │  │  (per WS) │
     └────────────┘  └──────────┘  └───────────┘
```

One person + One AI team = Small company-level capability.

Not one omnipotent AI, but a collaborative system of specialized agents,
each with distinct responsibilities, coordinated through central dispatch.

## Pre-installed Agents

### Nexus (main)
- **Role:** Central hub and dispatcher
- **Model:** Claude Opus (primary)
- **Responsibility:** Intent recognition, task routing, daily operations
- **Dispatch logic:** Recognizes user intent and routes to the right agent

### Observer
- **Role:** Intelligence analyst, 7x24 information patrol
- **Model:** GPT-5.2 (cost-effective for batch processing)
- **Responsibility:** Automated collection, two-tier filtering, knowledge extraction
- **Schedule:** Collection every 4h, daily report at 21:00

## Adding Agents

Use `./new-agent.sh` to scaffold new agents. Recommended additions from the
blueprint (see reference/agent-system-blueprint-v1.1.pdf):

| Agent | Role | Use Case |
|-------|------|----------|
| Arbiter | Strategic advisor | Decision analysis, pre-mortem, option matrix |
| Prism | Content editor | Long documents, reports, PPT |
| Forge | Tech partner | Coding, prototyping, CI/CD |
| Vitals | Health companion | Health data tracking, trend analysis |
| Wingman | Emotional wingman | Relationship tactics, chat analysis |

## Data Flows

### Observer -> Nexus (Intelligence Escalation)
1. Observer patrols sources on schedule
2. Tier-1 filter (Flash) checks topic match
3. Tier-2 evaluation (Gemini3) scores 11 dimensions
4. Score >= 85: instant push to user + forward to Nexus
5. Score 70-84: included in daily report
6. Score < 70: silent archive

### User -> Nexus -> Agent (Dispatch)
1. User sends message to Nexus via Telegram / DingTalk / CLI
2. Nexus identifies intent
3. Nexus routes to appropriate agent (or handles directly)
4. Agent processes and returns result
5. Nexus delivers result to user

### Cross-Agent Collaboration
- Agents call each other via `subagents.allowAgents` whitelist
- Shared state via STATE.yaml (optional)
- Knowledge sharing via OpenViking (MCP protocol)

## Communication Channels

### Telegram (built-in)
- Each agent has its own Telegram bot
- Direct integration via OpenClaw's Telegram plugin
- Supports text, images, voice (via Whisper)

### DingTalk (bridge)
- External bridge service: `dingtalk-bridge.py`
- DingTalk Stream API → OpenClaw Gateway HTTP API → Agent
- Deployed as LaunchAgent, auto-reconnects
- See [DINGTALK.md](./DINGTALK.md) for setup

### CLI / HTTP
- `openclaw chat` for local terminal access
- Gateway HTTP API for programmatic access

## Infrastructure

### Services

| Service | Port | Purpose | Schedule |
|---------|------|---------|----------|
| OpenClaw Gateway | 18789 | Agent orchestration | Always-on |
| OpenViking MCP | 2033 | Knowledge base search | Always-on |
| OpenViking Dashboard | 2034 | Knowledge base web UI | Always-on |
| RSSHub | 2035 | RSS feed aggregation | Always-on |
| DingTalk Bridge | — | DingTalk ↔ Gateway | Always-on (optional) |
| Health Check | — | Service monitoring | Every 30min |
| Log Rotation | — | Log management | Daily 03:00 |
| Observer Collect | — | Source patrol | Every 4h |
| Observer Daily | — | Daily report | Daily 21:00 |
| Memory Sync | — | Agent memory → OpenViking | Daily 23:30 |
| Morning Brief | — | Daily briefing | Daily 08:30 |

### Observer Pipeline

```
Sources (RSS + Web + API)
    │
    ▼
collect.py (every 4h)
    │
    ├─ RSS: feedparser → entries
    ├─ Web: BeautifulSoup → CSS selector extraction
    └─ API: HN top stories, GitHub Trending
    │
    ▼
Tier-1 Filter (Flash LLM)
    │  topic match against interests.md
    ▼
Tier-2 Scoring (Flash LLM)
    │  11-dimension evaluation per scoring.md
    ▼
    ├─ Score ≥ 85 → instant push
    ├─ Score 70-84 → daily report
    └─ Score < 70 → archive only
    │
    ▼
daily.py (21:00)
    │  aggregate day's cards → briefing
    ▼
Push via OpenClaw CLI
```

### Memory System

Each agent workspace contains:
- `SOUL.md` — Personality and principles
- `IDENTITY.md` — Name, emoji, role
- `TOOLS.md` — Available models and skills
- `AGENTS.md` — Relationships with other agents
- `HEARTBEAT.md` — Periodic task config (Nexus only)
- `USER.md` — User profile context (Nexus only)
- `memory/` — Session logs (YYYY-MM-DD.md)
- `MEMORY.md` — Long-term curated memory

### OpenViking Knowledge Base

```
Agent Memories ──(memory-sync.py)──→ OpenViking Store
                                          │
Observer Archive ──(memory-sync.py)──→    │
                                          ▼
                                    Semantic Search
                                    (MCP Protocol)
                                          │
                                          ▼
                                    Dashboard (:2034)
                                    API Endpoints
```

- **MCP Server** (`:2033`): `smart_search`, `query`, `session_commit` tools
- **Dashboard** (`:2034`): Web UI for browsing and searching knowledge base
- **Memory Sync**: Nightly sync of agent workspace memories into the knowledge base

### Multi-Model Strategy

```
Primary: Claude Opus 4.6 (strongest reasoning)
    |
Fallback 1: GPT-5.2 (cost-effective)
    |
Fallback 2: MiniMax M2.5 (lowest cost)

Specialized:
  - Gemini 3 Pro: 1M context (ultra-long documents)
  - Gemini 2.0 Flash: batch filtering (high throughput)
  - Doubao Seed 1.8: Chinese optimization (zero cost)
```

### Network

- **Tailscale:** Encrypted mesh networking for remote access
- **Telegram:** Primary user interface (each agent has its own bot)
- **DingTalk:** Enterprise IM integration (via bridge service)
- **HTTP Proxy:** For API calls that need proxy (configurable)

## Security

- Gateway binds to loopback only (local access)
- Token-based gateway authentication
- Telegram bots restricted to owner user ID via `allowFrom`
- DingTalk bridge authenticates via Gateway token
- API keys stored in `.env` (not in version control)
- `openclaw.json` permissions: 600 (owner-only)

## Directory Layout

```
~/.openclaw/
├── openclaw.json          # Main config (generated from template)
├── logs/                  # All service logs
├── scripts/               # healthcheck.py, logrotate.sh
├── shared/
│   └── STATE.yaml         # Cross-agent shared state
├── agents/                # Agent metadata
│   ├── main/agent/
│   └── observer/agent/
├── workspace/             # Nexus workspace
│   ├── SOUL.md
│   ├── IDENTITY.md
│   ├── TOOLS.md
│   ├── AGENTS.md
│   ├── USER.md
│   ├── HEARTBEAT.md
│   └── memory/
├── workspace-observer/    # Observer workspace
│   ├── SOUL.md
│   ├── IDENTITY.md
│   ├── TOOLS.md
│   ├── AGENTS.md
│   ├── config/            # sources.md, interests.md, scoring.md
│   ├── scripts/           # collect.py, daily.py
│   ├── memory/
│   └── archive/daily/
├── dingtalk-bridge/       # DingTalk bridge (optional)
│   ├── .venv/
│   └── bridge.py
├── openviking-data/       # Knowledge base storage
│   └── viking/
└── backups/               # Config backups

~/projects/openviking-local/   # OpenViking MCP server
├── server.py
├── dashboard-server.py
├── build-dashboard.py
├── memory-sync.py
└── .venv/
```

## Design Documents

| Document | Description |
|----------|-------------|
| [PERSONALITY-INJECTION.md](./PERSONALITY-INJECTION.md) | 人格注入机制调研：我们的 SOUL/IDENTITY/USER 体系 vs 行业方案（soul.md、SoulSpec）vs 名人人格注入案例 |
| [ARBITER.md](./ARBITER.md) | Arbiter（仲裁者）技术方案：决策分析 Agent 的完整设计，含思维工具箱、标准输出格式、记忆系统、协作模式 |
| [MODELS.md](./MODELS.md) | 多模型策略：主力/回退/专用模型选择和成本分析 |
| [DINGTALK.md](./DINGTALK.md) | 钉钉桥接服务：企业应用创建 + 配置详细步骤 |
| [QUICKSTART.md](./QUICKSTART.md) | 部署指南：从零开始部署整套系统 |
