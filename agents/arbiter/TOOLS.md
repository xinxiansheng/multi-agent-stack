# Arbiter - Tools & Models

## Model Configuration

| Config | Value |
|--------|-------|
| Primary | anthropic/claude-opus-4-6 |
| Fallback | None (decision analysis demands highest quality, no downgrade) |

## Why No Fallback
Arbiter's core value is judgment quality. A wrong decision costs more than a delayed decision.
If the primary model is unavailable, wait — don't degrade.

## Core Skills

- `web_search` / `web_fetch` — Research for decision context
- `summarize` — Distill long documents before analysis

## OpenViking (Knowledge Base)

Via MCP protocol (port 2033):
- `query` — Search historical decisions and related intelligence
- `smart_search` — Semantic search across knowledge base
- `session_commit` — Save decision analysis to knowledge base

## Decision Archive

Store major decisions in `decisions/` directory:
- Each decision: `decisions/YYYY-MM-DD-<topic>.md`
- Index: `decisions/INDEX.md`
- Format: standard 9-step output + outcome tracking

## Memory Layers

| Layer | Path | Purpose |
|-------|------|---------|
| Daily | `memory/YYYY-MM-DD.md` | Per-session notes |
| Long-term | `MEMORY.md` | Decision patterns, lessons, key conclusions |
| Archive | `decisions/ + INDEX.md` | Full decision records, reviewable |
| Monthly | `memory/archive/YYYY-MM.md` | Monthly rollup, keep recent 7 days |
