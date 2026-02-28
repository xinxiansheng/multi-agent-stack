# Nexus - Tools & Models

## Available Models

| Alias | Model ID | Use Case |
|-------|----------|----------|
| opus | anthropic/claude-opus-4-6 | Primary: complex reasoning, coordination |
| GPT-5.2 | openai-codex/gpt-5.2 | Fallback: general tasks |
| Minimax | minimax/MiniMax-M2.5 | Final fallback: lowest cost |
| Gemini3 | newapi/gemini-3-pro-preview | Ultra-long context (1M tokens) |
| Flash | newapi/gemini-2.0-flash | Batch processing, high throughput |
| Doubao | newapi/seed-1-8-251228 | Chinese optimization, zero cost |

## Model Selection Guidelines
- Default: use primary model (opus)
- Batch/simple tasks: switch to Flash or Doubao
- Ultra-long documents: use Gemini3
- Cost-sensitive repetitive tasks: use Minimax

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
