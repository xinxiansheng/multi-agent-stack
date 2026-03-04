# Observer Source Registry

> All information sources are managed here. Observer reads this file to know what to fetch.
> To add a source, add a row to the appropriate table with a backtick-wrapped RSS URL.
> Sources without RSS can be configured as web scrapers in `web_sources.yaml`.

## Collection Strategy

- **Sampling rate**: ~23% per round (random)
- **Rounds per day**: 4-6 rounds
- **Interval**: 3-4 hours between rounds
- **Daily coverage**: > 95% (mathematically guaranteed)

---

## AI & Technology

| Name | Site | Type | RSS | Status | Notes |
|------|------|------|-----|--------|-------|
| Import AI | https://importai.substack.com | RSS | `https://importai.substack.com/feed` | ACTIVE | Weekly AI newsletter |
| Latent Space | https://www.latent.space | RSS | `https://www.latent.space/feed` | ACTIVE | AI engineering podcast |
| AlphaSignal | https://alphasignal.ai | RSS | `https://alphasignal.ai/feed` | ACTIVE | AI research digest |
| Simon Willison | https://simonwillison.net | RSS | `https://simonwillison.net/atom/everything/` | ACTIVE | AI + dev tools |
| Hugging Face Blog | https://huggingface.co | RSS | `https://huggingface.co/blog/feed.xml` | ACTIVE | ML models & tools |
<!-- Add your AI sources:
| 36Kr AI | https://36kr.com | RSSHub | `http://localhost:2035/36kr/information/ai` | ACTIVE | Chinese tech media |
-->

## Business & Finance

| Name | Site | Type | RSS | Status | Notes |
|------|------|------|-----|--------|-------|
<!-- Example entries (uncomment and customize):
| Caixin Latest | https://www.caixin.com | RSSHub | `http://localhost:2035/caixin/latest` | ACTIVE | Premium finance news |
| 21st Century Finance | https://m.21jingji.com | RSSHub | `http://localhost:2035/21caijing/channel/金融` | ACTIVE | Financial regulation |
-->

## Your Industry

| Name | Site | Type | RSS | Status | Notes |
|------|------|------|-----|--------|-------|
<!-- Add industry-specific feeds here -->

## Tech Community

| Name | Site | Type | RSS | Status | Notes |
|------|------|------|-----|--------|-------|
| Hacker News Best | https://news.ycombinator.com | RSS | `https://hnrss.org/best?count=15` | ACTIVE | Tech community |
<!-- Note: HN and GitHub Trending are also fetched via API automatically -->

## WeChat Official Accounts (via WeRSS)

| Name | Site | Type | RSS | Status | Notes |
|------|------|------|-----|--------|-------|
<!-- Example (requires WeRSS running on port 8001):
| NPL Headlines | WeChat: npltoutiao | WeRSS | `http://127.0.0.1:8001/feed/MP_WXS_3002580414.xml` | ACTIVE | Industry news |
-->
