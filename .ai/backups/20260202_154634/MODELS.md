# OpenCode Model Reference (v9.3 - 7 Planners + DB Persistence)

## Primary Models

| Role | Model | Provider | Context | Output | Cost/1M In/Out |
|------|-------|----------|---------|--------|----------------|
| **Orchestrator** | **Kimi K2.5** | Moonshot | 256K | 32K | $0.60/$3.00 |
| **Primary Coder** | **Kimi K2.5** | Moonshot | 256K | 32K | $0.60/$3.00 |
| Fast Coder | Gemini 3 Flash (Vertex) | Google | 1M | 64K | $0.05/$0.30 |
| Validator | Gemini 3 Flash (Vertex) | Google | 1M | 64K | $0.05/$0.30 |

## Architecture Overview

```
ORCHESTRATOR (Kimi K2.5 - 1T MoE, 256K context, Native Agent Swarm)
    │
    ├── 32B active params per token (1T total)
    ├── Native vision encoder (MoonViT 400M params)
    ├── Agent Swarm: up to 100 parallel agents, 1,500 tool calls
    └── Uses: memory, taskbus, parallel, context-compactor
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  7 PARALLEL PLANNERS (diverse providers + DB persistence)       │
├─────────────────────────────────────────────────────────────────┤
│  planner-1: Gemini 3 Pro (Google) - Architecture & Data         │
│  planner-2: Claude Sonnet (Anthropic) - Security & Validation   │
│  planner-3: Kimi K2.5 (Moonshot) - Workflow & Creative          │
│  planner-4: DeepSeek V3 Chat - Logic & Algorithms               │
│  planner-5: GLM-4.7 (Z.AI) - Implementation & Testing           │
│  planner-6: GPT-5.2 (OpenAI) - System Design & Deep Reasoning   │
│  planner-7: Sonar Pro (Perplexity) - Research & Discovery       │
│  ALL planners write progress to taskbus + memory MCP            │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  5+ PARALLEL CODERS (speed-optimized)                           │
├─────────────────────────────────────────────────────────────────┤
│  coder: Kimi K2.5 (Moonshot) - Primary, 256K context            │
│  coder-fast: Gemini 3 Flash (Google) - Sub-2s response          │
│  coder-kimi: Kimi K2.5 (Moonshot) - Creative implementations    │
│  coder-deepseek: DeepSeek V3 - Complex logic                    │
│  coder-groq: Llama 3.3 70B (Groq) - Ultra-fast bulk             │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  VALIDATORS (cross-provider - always different from coder)      │
├─────────────────────────────────────────────────────────────────┤
│  validator: Gemini 3 Flash (Google)                             │
│  validator-anthropic: Claude Haiku (Anthropic)                  │
└─────────────────────────────────────────────────────────────────┘
```

## Model Power Ranking (Verified Token Limits)

| Rank | Model | Provider | Context | Output | Cost/1M In/Out | Best For |
|------|-------|----------|---------|--------|----------------|----------|
| S | GPT-5.2 | OpenAI | 400K | 128K | $1.75/$14.00 | CRITICAL ONLY |
| S | Claude Opus 4.5 | Anthropic | 200K | 32K | $5.00/$25.00 | CRITICAL ONLY |
| A | Gemini 3 Pro | Google | 1M | 64K | $2.00/$12.00 | Architecture |
| A | Claude Sonnet 4.5 | Anthropic | 200K (1M beta) | 64K | $3.00/$15.00 | Security |
| A | Kimi K2.5 | Moonshot | 256K | 32K | $0.60/$3.00 | Swarm/Creative |
| B | GLM-4.7 | Z.AI | 200K | 128K | $0.60/$2.20 | Coding |
| B | DeepSeek V3.2 | DeepSeek | 131K | 8K | $0.27/$1.10 | Orchestration |
| B | DeepSeek Reasoner | DeepSeek | 64K | 64K | $0.55/$2.19 | Logic |
| C | Gemini 3 Flash | Google | 1M | 64K | $0.05/$0.30 | Fast tasks |
| C | Claude Haiku 4.5 | Anthropic | 200K | 64K | $1.00/$5.00 | Validation |
| D | Llama 3.3 70B | Groq | 128K | 8K | $0.59/$0.79 | Bulk work |

## Kimi K2.5 Specifications (Primary Orchestrator)

**Architecture:**
- 1 Trillion total parameters (MoE)
- 32B active parameters per token
- 61 layers (1 dense + 384 experts)
- Multi-head Latent Attention (MLA) - 7,168 attention dimensions
- MoonViT vision encoder (400M params)
- Native INT4 quantization (2x inference speed)

**Context & Output:**
- Context Window: 256,000 tokens
- Max Output: 32,000 tokens
- Supports: Text, Images, Video input

**Agent Swarm Capability:**
- Up to 100 parallel specialized agents
- Up to 1,500 parallel tool calls
- 4.5x speedup for large-scale tasks
- Autonomous debugging and code correction

**Benchmarks:**
- SWE-Bench Verified: 76.8%
- SWE-Bench Multilingual: 73.0%
- LiveCodeBench v6: 85.0%
- AIME 2025: 96.1%
- BrowseComp (swarm): 78.4%

**API Models Available:**
| Model ID | Context | Features |
|----------|---------|----------|
| kimi-k2.5 | 256K | Vision, Video, Reasoning |
| kimi-k2-thinking | 256K | Deep reasoning mode |
| kimi-k2-thinking-turbo | 256K | Fast thinking mode |
| moonshot-v1-128k | 128K | Standard |
| moonshot-v1-32k | 32K | Standard |
| moonshot-v1-8k | 8K | Standard |

## Claude 4.5 Family Specifications

| Model | Context | Output | Cost In/Out | Knowledge Cutoff |
|-------|---------|--------|-------------|------------------|
| Claude Opus 4.5 | 200K | 32K | $5/$25 | March 2025 |
| Claude Sonnet 4.5 | 200K (1M beta) | 64K | $3/$15 | January 2025 |
| Claude Haiku 4.5 | 200K | 64K | $1/$5 | February 2025 |

**Features:**
- Context awareness (token budget tracking)
- Extended 1M context in beta for Sonnet (Tier 4+ orgs)

## GPT-5 Family Specifications

| Model | Context | Output | Cost In/Out | Features |
|-------|---------|--------|-------------|----------|
| GPT-5.2 Thinking | 400K | 128K | $1.75/$14 | Deep reasoning |
| GPT-5.2 Instant | 128K | 16K | $1.75/$14 | Fast response |
| GPT-5.2 Pro | 400K | 128K | Premium | Highest accuracy |
| GPT-5.1 | 400K | 128K | $1.50/$12 | General purpose |
| GPT-5.1 Codex-Max | Unlimited* | 128K | Premium | Compaction tech |

*GPT-5.1 Codex-Max uses "compaction" for project-scale coding

## DeepSeek Specifications

| Model | Context | Output | Cost In/Out |
|-------|---------|--------|-------------|
| DeepSeek V3.2 | 131K | 8K | $0.27/$1.10 |
| DeepSeek V3.1 | 128K | 8K | $0.27/$1.10 |
| DeepSeek Reasoner | 64K | 64K | $0.55/$2.19 |

**Architecture:** 671B total params, 37B active per token (MoE)

## GLM-4.7 Specifications (Z.AI)

| Model | Context | Output | Cost In/Out |
|-------|---------|--------|-------------|
| GLM-4.7 | 200K | 128K | $0.60/$2.20 |
| GLM-4.6 | 200K | 128K | $0.50/$2.00 |
| GLM-4.6V | 128K | 128K | $0.50/$2.00 |

**Architecture:** ~400B parameters

**Benchmarks:**
- SWE-Bench: 73.8%
- SWE-Bench Multilingual: 66.7%
- Terminal Bench 2.0: 41%

## Gemini 3 Specifications (Google)

| Model | Context | Output | Cost In/Out |
|-------|---------|--------|-------------|
| Gemini 3 Pro | 1M | 64K | $2.00/$12.00 |
| Gemini 3 Flash | 1M | 64K | $0.05/$0.30 |

**Features:**
- 1M token context window
- Multimodal (text, images, video, audio, PDF, code)
- Available via Vertex AI

## Groq (Llama 3.3 70B)

| Model | Context | Output | Cost In/Out |
|-------|---------|--------|-------------|
| Llama 3.3 70B Versatile | 128K | 8K | $0.59/$0.79 |
| Llama 3.3 70B SpecDec | 8K (expanding) | 8K | $0.59/$0.79 |

**Features:**
- Ultra-fast inference on Groq LPU
- Tool use, JSON mode
- Grouped-Query Attention (GQA)

## Agent Assignments

### Orchestrator
| Agent | Model | Context | Role |
|-------|-------|---------|------|
| orchestrator | `moonshot/kimi-k2.5` | 256K | Task routing, Agent Swarm |

### Planners (7 parallel)
| Agent | Model | Context | Focus |
|-------|-------|---------|-------|
| planner-1 | `google/gemini-3-pro-preview` | 1M | Architecture & Data |
| planner-2 | `anthropic/claude-sonnet-4-5` | 200K | Security & Validation |
| planner-3 | `moonshot/kimi-k2.5` | 256K | Workflow & Creative |
| planner-4 | `deepseek/deepseek-chat` | 131K | Logic & Algorithms |
| planner-5 | `zai/glm-4.7` | 200K | Implementation & Testing |
| planner-6 | `openai/gpt-5.2` | 400K | System Design & Deep Reasoning |
| planner-7 | `perplexity/sonar-pro` | 128K | Research & Discovery |

### Coders (5+ parallel)
| Agent | Model | Context | Speed |
|-------|-------|---------|-------|
| coder | `moonshot/kimi-k2.5` | 256K | Medium |
| coder-fast | `google/gemini-3-flash-preview` | 1M | <2s |
| coder-glm | `zai/glm-4.7` | 200K | Medium |
| coder-deepseek | `deepseek/deepseek-chat` | 131K | Fast |
| coder-groq | `groq/llama-3.3-70b-versatile` | 128K | <1s |

### Validators (cross-provider)
| Agent | Model | Context | Validates |
|-------|-------|---------|-----------|
| validator | `google/gemini-3-flash-preview` | 1M | Z.AI, DeepSeek, Moonshot |
| validator-anthropic | `anthropic/claude-haiku-4-5` | 200K | Google, Z.AI, Groq |

### Escalation Tiers
| Tier | Agent | Model | Context | When to Use |
|------|-------|-------|---------|-------------|
| A | claude-haiku | `anthropic/claude-haiku-4-5` | 200K | Cost-effective quality |
| A | claude-sonnet | `anthropic/claude-sonnet-4-5` | 200K | High quality code |
| S | claude-opus | `anthropic/claude-opus-4-5` | 200K | CRITICAL ONLY |
| A | gpt-5.1 | `openai/gpt-5.1` | 400K | Complex reasoning |
| S | gpt-5.2 | `openai/gpt-5.2` | 400K | CRITICAL ONLY |
| A | gemini-pro | `google/gemini-3-pro-preview` | 1M | Large context |
| B | gemini-flash | `google/gemini-3-flash-preview` | 1M | Fast execution |

## API Endpoints

| Provider | Base URL |
|----------|----------|
| Moonshot | `https://api.moonshot.ai/v1` |
| Z.AI | `https://api.z.ai/api/coding/paas/v4/` |
| DeepSeek | `https://api.deepseek.com/v1` |
| Perplexity | `https://api.perplexity.ai` |
| OpenAI | `https://api.openai.com/v1` |
| Anthropic | `https://api.anthropic.com` |
| Google | `https://aiplatform.googleapis.com` (Vertex) |
| Groq | `https://api.groq.com/openai/v1` |

## Cross-Model Validation Rules

| Coder Provider | Valid Validators |
|----------------|------------------|
| Z.AI (GLM-4.7) | Google, Anthropic |
| Google (Gemini) | Z.AI, Anthropic |
| DeepSeek | Google, Z.AI |
| Moonshot (Kimi) | Google, Anthropic |
| Groq (Llama) | Google, Z.AI |

## Key Optimizations (v9.3)

1. **Kimi K2.5 as Orchestrator**: Native Agent Swarm (100 agents, 1500 tool calls)
2. **7 Parallel Planners**: Added GPT-5.2 and Perplexity Sonar Pro for maximum coverage
3. **DeepSeek V3 Chat**: Changed from Reasoner to Chat (as per user requirement)
4. **DB Persistence**: All planners/orchestrator write progress to taskbus + memory MCP (avoid truncation)
5. **41 TaskBus Tools**: Added update_task_progress for continuous progress tracking
6. **GLM-4.7 200K context**: Verified 200K (not 256K estimate)
7. **Gemini 3 1M context**: Confirmed for both Pro and Flash
8. **GPT-5.2 400K context**: Enterprise-grade context window
9. **Cross-provider validation enforced**: No same-provider validation
