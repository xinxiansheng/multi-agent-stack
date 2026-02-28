# Architecture

## System Overview

```
User <-> Telegram (N Bots) <-> OpenClaw Gateway <-> N Agents
                                      |
                              Shared State Layer
                                      |
                              Knowledge Base (OpenViking)
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
1. User sends message to Nexus via Telegram
2. Nexus identifies intent
3. Nexus routes to appropriate agent (or handles directly)
4. Agent processes and returns result
5. Nexus delivers result to user

### Cross-Agent Collaboration
- Agents call each other via `subagents.allowAgents` whitelist
- Shared state via STATE.yaml (optional)
- Knowledge sharing via OpenViking (MCP protocol)

## Infrastructure

### Services

| Service | Port | Purpose | Schedule |
|---------|------|---------|----------|
| OpenClaw Gateway | 18789 | Agent orchestration | Always-on |
| OpenViking MCP | 2033 | Knowledge base search | Always-on |
| RSSHub | 2035 | RSS feed aggregation | Always-on |
| Health Check | — | Service monitoring | Every 30min |
| Log Rotation | — | Log management | Daily 03:00 |
| Observer Collect | — | Source patrol | Every 4h |
| Observer Daily | — | Daily report | Daily 21:00 |

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
- **HTTP Proxy:** For API calls that need proxy (configurable)

## Security

- Gateway binds to loopback only (local access)
- Token-based gateway authentication
- Telegram bots restricted to owner user ID via `allowFrom`
- API keys stored in `.env` (not in version control)
- `openclaw.json` permissions: 600 (owner-only)

## Directory Layout

```
~/.openclaw/
├── openclaw.json          # Main config (generated from template)
├── logs/                  # All service logs
├── scripts/               # healthcheck.py, logrotate.sh
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
│   ├── memory/
│   └── archive/
├── openviking-data/       # Knowledge base storage
└── backups/               # Config backups
```
