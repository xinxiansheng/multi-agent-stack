# Observer - Tools & Pipeline Model Strategy

## Available Models

| Alias | Model ID | Use Case |
|-------|----------|----------|
| GPT-5.2 | openai-codex/gpt-5.2 | Primary: interactive tasks, ad-hoc analysis |
| Flash | newapi/gemini-2.0-flash | Pipeline: batch filtering & scoring (fast, free) |
| Gemini3 | newapi/gemini-3-pro-preview | Daily reports, deep analysis (1M context) |
| Minimax | minimax/MiniMax-M2.5 | Final fallback |
| Doubao | newapi/seed-1-8-251228 | Chinese source processing (free) |

## Collection Pipeline — Model Assignment

```
RSS/Web Sources
      │
      ▼
┌─────────────────┐
│ Tier-1 Filter   │  Model: Flash (gemini-2.0-flash)
│ Topic matching  │  Batch 20 items → keep/reject
│ Cost: free      │  Speed: ~2s per batch
└────────┬────────┘
         │ pass
         ▼
┌─────────────────┐
│ Tier-2 Scoring  │  Model: Flash (gemini-2.0-flash)
│ Multi-dimension │  Batch 10 items → score 0-100
│ Cost: free      │  Threshold: 70+ archive, 85+ push
└────────┬────────┘
         │ ≥70
         ▼
┌─────────────────┐
│ Extract & Index │  Model: Flash (gemini-2.0-flash)
│ Knowledge card  │  YAML frontmatter + summary
│ → OpenViking    │  Index to knowledge base
└────────┬────────┘
         │ ≥85
         ▼
┌─────────────────┐
│ Push to User    │  Via Telegram (Nexus channel)
│ Instant alert   │
└─────────────────┘

         ┌─────────────────┐
21:00 →  │ Daily Report    │  Model: Gemini3 (gemini-3-pro-preview)
         │ Synthesize day  │  Strong reasoning for trend analysis
         │ → archive/daily │  1M context handles full day's data
         └─────────────────┘
```

### Why Flash for Pipeline (not Gemini3)?

- Gemini 3 Pro has output truncation issues on NewAPI for structured JSON batches
- Flash is stable for item-by-item JSON scoring
- Flash is free and fast (~2s per batch vs ~8s for Gemini3)
- For MVP: Flash handles all pipeline stages; upgrade Extract stage to Opus for high-value content later

### Model Override via Environment

All pipeline models can be changed in `.env`:
```
LLM_FILTER_MODEL=gemini-2.0-flash    # Tier-1
LLM_SCORE_MODEL=gemini-2.0-flash     # Tier-2
LLM_EXTRACT_MODEL=gemini-2.0-flash   # Knowledge extraction
LLM_DAILY_MODEL=gemini-3-pro-preview # Daily report
```

## Data Sources

Configure in `workspace-observer/config/`:
- **sources.yaml** — RSS feeds via RSSHub (port 2035)
- **web_sources.yaml** — CSS-selector web scrapers for sites without RSS
- **interests.md** — Tier-1 topic filter keywords
- **scoring.md** — Tier-2 scoring dimensions and weights

Source types:
- RSS feeds (RSSHub, native RSS)
- Web page scraping (CSS selectors)
- API integrations (GitHub Trending, Hacker News, etc.)
- WeChat Official Accounts (via WeRSS)

## Output Formats

- **Knowledge cards:** YAML frontmatter + Markdown (archive/)
- **Daily report:** Structured summary (archive/daily/)
- **Telegram push:** Instant alerts for score ≥85

## Skills

- `web_search` / `web_fetch` — Ad-hoc research
- `summarize` — Content summarization
- `nano-pdf` — PDF extraction
