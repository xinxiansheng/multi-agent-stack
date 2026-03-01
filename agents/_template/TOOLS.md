# {{AGENT_NAME}} - Tools & Models

## Available Models

| Alias | Provider | Model ID | Strengths |
|-------|----------|----------|-----------|
| opus | Anthropic | claude-opus-4-6 | Strongest reasoning |
| GPT-5.2 | OpenAI Codex | gpt-5.2 | General-purpose |
| Codex | OpenAI Codex | gpt-5.2-codex | Code-specialized |
| Minimax | MiniMax | MiniMax-M2.5 | Cost-effective reasoning |
| Gemini3 | NewAPI | gemini-3-pro-preview | 1M context, multimodal |
| Flash | NewAPI | gemini-2.0-flash | Ultra-fast batch, free |
| Doubao | NewAPI | seed-1-8-251228 | Chinese-optimized, free |

Use `/model <alias>` to switch models for specific tasks.

## Model Selection Guidelines

- Default: use primary model (configured in openclaw.json)
- Complex reasoning / architecture: **opus**
- Programming tasks: **Codex**
- Ultra-long documents: **Gemini3** (1M tokens)
- Batch / simple tasks: **Flash** (free)
- Chinese content: **Doubao** (free)
- Cost-sensitive work: **Minimax**

## Skills
<!-- List skills this agent uses, install via: openclaw skill install <name> -->

## Custom Tools
<!-- Define any agent-specific tools or scripts -->
