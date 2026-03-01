# Multi-Model Strategy

## Architecture Overview

OpenClaw 采用 **多提供商、多模型、分层路由** 架构：

```
                    ┌──────────────────────────────────┐
                    │       Model Router               │
                    │  primary → fallback1 → fallback2 │
                    └──────┬───────────────────────────┘
                           │
        ┌──────────┬───────┴───────┬──────────┐
        ▼          ▼               ▼          ▼
   ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
   │Anthropic│ │OpenAI    │ │ MiniMax  │ │ NewAPI   │
   │ (官方)  │ │Codex     │ │          │ │ (聚合)   │
   └────┬────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘
        │          │           │           │
   claude-     gpt-5.2     MiniMax-    gemini-3-pro
   opus-4-6    gpt-5.2-    M2.5       gemini-2.0-flash
               codex                   seed-1-8 (Doubao)
               gpt-5.3-               claude-sonnet-4-5
               codex                   claude-opus-4-5
```

## Provider Details

### Provider 1: Anthropic (Official)

| Key | Value |
|-----|-------|
| Auth | API Key (`ANTHROPIC_API_KEY`) |
| Protocol | Anthropic Messages API |
| Models | `claude-opus-4-6` |
| Best For | Complex reasoning, architecture, coordination |
| Cost | Highest (official pricing) |

### Provider 2: OpenAI Codex

| Key | Value |
|-----|-------|
| Auth | OAuth (run `openclaw auth login openai-codex`) |
| Protocol | OpenAI Completions |
| Models | `gpt-5.2`, `gpt-5.2-codex`, `gpt-5.3-codex` |
| Best For | General programming, code generation |
| Cost | Free (Codex program) |

### Provider 3: MiniMax

| Key | Value |
|-----|-------|
| Auth | API Key (`MINIMAX_API_KEY`) |
| Protocol | Anthropic Messages API (compatible) |
| Models | `MiniMax-M2.5` |
| Best For | Cost-effective reasoning, final fallback |
| Cost | Low (15¥/M input, 60¥/M output) |

### Provider 4: NewAPI (Aggregated Proxy)

| Key | Value |
|-----|-------|
| Auth | API Key (`NEWAPI_API_KEY`) |
| Protocol | OpenAI Completions (compatible) |
| Base URL | Configurable (`NEWAPI_BASE_URL`) |
| Models | See below |
| Best For | Access to multiple model families via single endpoint |

NewAPI Models:

| Model ID | Alias | Context | Cost | Reasoning | Notes |
|----------|-------|---------|------|-----------|-------|
| gemini-3-pro-preview | Gemini3 | 1M | Free | Yes | Frontend/UI, long docs |
| gemini-2.0-flash | Flash | 1M | Free | No | Batch processing, fastest |
| seed-1-8-251228 | Doubao | 128K | Free | Yes | Chinese-optimized |
| claude-sonnet-4-5-20250929 | Sonnet-NewAPI | 200K | Mid | Yes | Balanced Claude |
| claude-opus-4-5-20251101 | Opus-NewAPI | 200K | High | Yes | Strong Claude |

## Fallback Chain

每个 Agent 配置一条降级链，模型不可用时自动切换：

```
Agent Default:   opus → GPT-5.2 → Minimax
Observer:        GPT-5.2 → Minimax
```

配置方式（`.env`）：
```bash
PRIMARY_MODEL=anthropic/claude-opus-4-6
FALLBACK_MODEL_1=openai-codex/gpt-5.2
FALLBACK_MODEL_2=minimax/MiniMax-M2.5
```

## Task-Based Routing

不同任务类型使用不同模型，在 `.env` 中配置：

| 任务类型 | 环境变量 | 默认模型 | 选择理由 |
|---------|----------|---------|---------|
| 前端/UI 开发 | `FRONTEND_MODEL` | Gemini3 | 组件生成、样式、布局能力强 |
| 代码编程 | `CODE_MODEL` | Codex | 编程专精 |
| 超长文档分析 | `LONG_CONTEXT_MODEL` | Gemini3 | 1M token 上下文 |
| 中文任务 | `CHINESE_MODEL` | Doubao | 中文优化，免费 |
| 批量处理 | `BATCH_MODEL` | Flash | 最快，免费 |

## Observer Pipeline Model Assignment

采集管线使用独立的模型配置，优化成本：

| 阶段 | 环境变量 | 默认模型 | 说明 |
|------|----------|---------|------|
| Tier-1 粗筛 | `LLM_FILTER_MODEL` | gemini-2.0-flash | 批量20条，快速判断相关性 |
| Tier-2 评分 | `LLM_SCORE_MODEL` | gemini-2.0-flash | 批量10条，多维度打分 |
| 知识抽取 | `LLM_EXTRACT_MODEL` | gemini-2.0-flash | 提取结构化知识卡片 |
| 每日简报 | `LLM_DAILY_MODEL` | gemini-3-pro-preview | 综合分析需要强推理 |

### 为什么管线用 Flash 而不是 Gemini3？

1. Gemini 3 Pro 在 NewAPI 上输出结构化 JSON 时有截断问题
2. Flash 对逐条 JSON 评分输出稳定
3. Flash 免费且快（~2s/batch vs ~8s/batch）
4. MVP 阶段 Flash 够用；后续可将 Extract 阶段升级到 Opus

## Embeddings (OpenViking)

知识库语义搜索使用独立的嵌入模型：

| 配置 | 说明 |
|------|------|
| `VOLCENGINE_API_KEY` | 火山引擎 API 密钥 |
| `VOLCENGINE_EMBED_MODEL` | 文本嵌入模型 |
| `VOLCENGINE_VLM_MODEL` | 视觉语言模型（可选） |

## Cost Optimization Strategy

```
                 质量 ▲
                      │  opus ●
                      │          ● Opus-NewAPI
                      │     ● GPT-5.2
                      │        ● Sonnet-NewAPI
                      │  ● Gemini3
                      │     ● Minimax
                      │ ● Flash    ● Doubao
                      └───────────────────────► 成本
                      免费                    高
```

**最佳实践：**

1. **日常交互** → opus（最高质量）或 GPT-5.2（免费 OAuth）
2. **编程任务** → Codex（代码专精）或 Gemini3（前端）
3. **批量处理** → Flash（免费、最快）
4. **中文内容** → Doubao（免费、中文优化）
5. **超长文档** → Gemini3（1M 上下文）
6. **兜底保障** → Minimax（低成本、稳定）
7. **无官方 Key** → Sonnet-NewAPI / Opus-NewAPI（通过聚合代理）

## Adding New Providers

如需添加新的模型提供商：

1. 在 `.env` 中添加 API Key 变量
2. 在 `config/openclaw.template.json` 的 `models.providers` 中添加提供商定义
3. 在 `auth.profiles` 中添加认证配置
4. 在 `agents.defaults.models` 中添加别名
5. 运行 `make config` 重新生成配置
6. 运行 `make restart` 重启网关

示例 — 添加一个 OpenRouter 提供商：

```json
// config/openclaw.template.json → models.providers
"openrouter": {
  "baseUrl": "https://openrouter.ai/api/v1",
  "api": "openai-completions",
  "models": [
    {
      "id": "meta-llama/llama-3.1-405b",
      "name": "Llama 3.1 405B",
      "reasoning": true,
      "input": ["text"],
      "cost": { "input": 3, "output": 3, "cacheRead": 0, "cacheWrite": 0 },
      "contextWindow": 131072,
      "maxTokens": 4096
    }
  ]
}
```
