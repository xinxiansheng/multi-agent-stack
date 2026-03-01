# Nexus - Tools & Multi-Model Strategy

## Available Models

| Alias | Provider | Model ID | Strengths |
|-------|----------|----------|-----------|
| opus | Anthropic | claude-opus-4-6 | Strongest reasoning, complex coordination |
| GPT-5.2 | OpenAI Codex | gpt-5.2 | General-purpose, balanced cost/quality |
| Codex | OpenAI Codex | gpt-5.2-codex | Code-specialized, programming tasks |
| Codex-5.3 | OpenAI Codex | gpt-5.3-codex | Next-gen code model |
| Minimax | MiniMax | MiniMax-M2.5 | Cost-effective reasoning, 200K context |
| Gemini3 | NewAPI | gemini-3-pro-preview | 1M context, frontend/UI, multimodal |
| Flash | NewAPI | gemini-2.0-flash | Ultra-fast batch, free, 1M context |
| Doubao | NewAPI | seed-1-8-251228 | Chinese-optimized, free |
| Sonnet-NewAPI | NewAPI | claude-sonnet-4-5-20250929 | Balanced Claude via proxy |
| Opus-NewAPI | NewAPI | claude-opus-4-5-20251101 | Strong Claude via proxy |

## Fallback Chain

```
primary: opus (Anthropic)
   ↓ fail
fallback-1: GPT-5.2 (OpenAI Codex)
   ↓ fail
fallback-2: Minimax (MiniMax)
```

## Task-Based Model Routing

Use `/model <alias>` to switch models for specific tasks.

| Task Type | Recommended Model | Reason |
|-----------|-------------------|--------|
| Complex reasoning, architecture | opus | Deepest reasoning capability |
| General programming | Codex / Codex-5.3 | Code-specialized, cost-effective |
| Frontend / UI / React / CSS | Gemini3 | Excellent at components, styles, layouts |
| Ultra-long document analysis | Gemini3 | 1M token context window |
| Batch processing, simple tasks | Flash | Fastest, zero cost |
| Chinese content tasks | Doubao | Chinese-optimized, free via Volcengine |
| Cost-sensitive repetitive work | Minimax | Reliable reasoning at low cost |
| Balanced quality (no Anthropic key) | Sonnet-NewAPI | Claude quality via aggregator |

### Auto-Routing Hints

When the user says:
- "做个页面", "写前端", "UI 组件" → switch to **Gemini3**
- "写代码", "实现功能", "debug" → switch to **Codex**
- "分析这个文档" (long) → switch to **Gemini3**
- "翻译", "中文" → switch to **Doubao**
- Simple scripting, one-off tasks → switch to **Flash**

## Core Skills

Skills are installed via `openclaw skill install <name>`. Common skills:
- `memo` — Quick notes
- `remindctl` — Reminders management
- `himalaya` — Email client
- `summarize` — Content summarization
- `web_search` / `web_fetch` — Web access
- `gh` — GitHub operations
- `obsidian` — Knowledge management

## Agent Dispatch

Use `@AgentName` to route tasks to other agents.
- `@Observer` — Information collection and analysis
- Additional agents can be added via `new-agent.sh`

## OpenViking (Knowledge Base)

Via MCP protocol (port 2033):
- `query` — Keyword search in knowledge base
- `search` / `smart_search` — Semantic search
- `add_resource` — Index new content
- `session_commit` — Save session learnings
