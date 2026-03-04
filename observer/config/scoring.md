# Tier-2 Scoring Rules (11-Dimension)

> Observer uses these rules in Tier-2 to score each article 0-100.
> The LLM evaluates all dimensions and outputs a composite score.

## Positive Signals (Additive, base = 0)

| Dimension | Max Points | Description |
|-----------|-----------|-------------|
| originality | +20 | First-hand information, original research, exclusive |
| new-insight | +15 | Novel interpretation of known facts, unique angle |
| actionability | +15 | Directly usable information, clear next steps |
| data-driven | +10 | Backed by specific data, metrics, benchmarks |
| info-density | +10 | High information per word ratio, concise |
| insider | +10 | Insider perspective, non-public information |
| timeliness | +10 | Breaking news, very recent event, first report |
| readability | +5 | Well-structured, clear writing, good formatting |
| scarcity | +5 | Rare topic, not widely covered elsewhere |

## Negative Signals (Deductions)

| Dimension | Penalty | Description |
|-----------|---------|-------------|
| marketing | -30 | Sponsored content, product promotion, advertorial |
| clickbait | -20 | Misleading title, sensationalism, exaggeration |
| repeat | -20 | Same story rehashed from other sources |
| one-sided | -15 | No counterargument, heavily biased perspective |
| AI-slop | -15 | Obviously AI-generated filler, no human insight |
| no-evidence | -10 | Claims without supporting data or sources |
| too-obscure | -10 | Too niche, no practical relevance to user |

## Score Tiers

| Score Range | Action |
|-------------|--------|
| 85-100 | Instant push + daily report |
| 70-84 | Daily report + deep extraction |
| 50-69 | Silent archive (simple card) |
| 0-49 | Discard |
