# Observer - Tools & Models

## Available Models

| Alias | Model ID | Use Case |
|-------|----------|----------|
| GPT-5.2 | openai-codex/gpt-5.2 | Primary: cost-effective batch processing |
| Flash | newapi/gemini-2.0-flash | Tier-1 coarse filtering, high throughput |
| Gemini3 | newapi/gemini-3-pro-preview | Tier-2 detailed evaluation, long content |
| Minimax | minimax/MiniMax-M2.5 | Final fallback |

## Model Selection for Pipeline Stages
- **Tier-1 Coarse filter:** Flash (cheapest, fastest)
- **Tier-2 Detailed scoring:** Gemini3 or GPT-5.2
- **Knowledge extraction:** GPT-5.2
- **Daily report generation:** GPT-5.2

## Data Sources
Configure sources in the collection scripts. Common types:
- **RSS feeds** via RSSHub (port 2035)
- **Web scrapers** for sites without RSS
- **API integrations** (GitHub Trending, Hacker News, etc.)
- **WeChat Official Accounts** via WeRSS

## Output Formats
- **Knowledge cards:** YAML frontmatter + Markdown
- **Daily report:** Structured summary pushed via Telegram
- **Archive:** Organized by date in workspace-observer/archive/

## Skills
- `web_search` / `web_fetch` — Ad-hoc research
- `summarize` — Content summarization
- `nano-pdf` — PDF extraction
