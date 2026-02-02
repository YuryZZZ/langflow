# OpenCode Model Reference

## Primary Models

| Role              | Model                      | Provider | Context | Output | Cost/1M      |
| ----------------- | -------------------------- | -------- | ------- | ------ | ------------ |
| **Orchestrator**  | DeepSeek Reasoner Thinking | DeepSeek | 128K    | 64K    | $0.55/$2.19  |
| **Primary Coder** | GLM-4.7                    | Z.AI     | 200K    | 128K   | $0.60/$2.20  |
| **Fast Coder**    | Gemini 3 Flash             | Google   | 1M      | 65K    | $0.075/$0.30 |
| **Validator**     | Gemini 3 Flash             | Google   | 1M      | 65K    | $0.075/$0.30 |

## Provider Distribution

### Z.AI (20% - 6 agents)

```
glm-4.7:
  - coder (PRIMARY)
  - coder-ts
  - tester
  - reviewer
  - researcher
  - planner-5
```

### Google (23% - 7 agents)

```
gemini-3-pro:
  - planner-1
  - debugger
  - analyst
  - gemini-pro (escalation)

gemini-3-flash:
  - validator
  - coder-fast
  - gemini-flash (escalation)
```

### DeepSeek (Main Orchestrator - 20% - 6 agents)

```
deepseek-reasoner (V3 Thinking):
  - orchestrator (PRIMARY)
  - planner-4
  - deepseek-think
  - deepseek-reasoner (escalation)

deepseek-chat (V3.2):
  - coder-deepseek
  - planner-3
```

### OpenAI (Legacy/Fallback - 5%)

```
gpt-4o:
  - gpt-4o (escalation)
```

### Anthropic (17% - 5 agents)

```
claude-sonnet-4.5:
  - planner-2
  - security
  - claude-sonnet (escalation)

claude-haiku-4.5:
  - claude-haiku

claude-opus-4.5:
  - claude-opus (escalation - CRITICAL ONLY)
```

...

### DeepSeek Reasoner Thinking (Orchestrator)

- **Context**: 128,000 tokens
- **Output**: 64,000 tokens (Thinking)
- **Role**: Task routing and workflow enforcement
- **Key Features**:
  - State-of-the-art chain-of-thought
  - 10x cheaper than legacy models
  - Code-aware reasoning

...

### Expensive (Daily Cap: 10 calls)

- anthropic/claude-opus-4.5: $15/$75 per 1M tokens
- openai/gpt-4o: $5/$15 per 1M tokens

### Moderate

- anthropic/claude-sonnet-4.5: $3/$15 per 1M tokens
- google/gemini-3-pro: $1.25/$5 per 1M tokens
- deepseek/deepseek-reasoner: $0.55/$2.19 per 1M tokens

...

| Agent        | Model             | Allowed Tasks               |
| ------------ | ----------------- | --------------------------- |
| orchestrator | DeepSeek Reasoner | Task routing, workflow only |

### Groq (13% - 4 agents)

```
llama-3.3-70b:
  - mass-worker

llama-3.1-8b:
  - cheap-worker (TRIVIAL ONLY)

kimi-k2:
  - kimi

gpt-oss-120b:
  - reasoner
```

### Perplexity (3% - 1 agent)

```
sonar-pro:
  - search
```

## Model Capabilities

### GLM-4.7 (Primary Coder)

- **Released**: December 22, 2025
- **Context**: 200,000 tokens
- **Output**: 128,000 tokens (8x larger than GLM-4.6)
- **Key Features**:
  - Preserved Thinking (maintains reasoning across turns)
  - Vibe Coding (enhanced UI generation)
  - Agentic stability for multi-step tasks
- **Benchmarks**:
  - SWE-bench Verified: 73.8%
  - LiveCodeBench-v6: 84.9%
  - AIME 2025: 95.7%

### DeepSeek Reasoner Thinking (Orchestrator)

- **Context**: 128,000 tokens
- **Output**: 64,000 tokens (Thinking)
- **Role**: Task routing and workflow enforcement
- **Key Features**:
  - State-of-the-art chain-of-thought
  - 10x cheaper than legacy models
  - Code-aware reasoning

### Gemini 3 Flash (Fast Coder/Validator)

- **Context**: 1,048,576 tokens (1M)
- **Output**: 65,536 tokens
- **Key Features**:
  - Sub-2s response time
  - Large context for validation
  - Cost-effective

### Gemini 3 Pro (Debugger/Analyst)

- **Context**: 1,000,000 tokens
- **Output**: 64,000 tokens
- **Key Features**:
  - Deep reasoning capability
  - Root cause analysis
  - Architecture review

## Cross-Model Validation Rules

Coders MUST be validated by different model families:

| Coder                 | Valid Validators                                |
| --------------------- | ----------------------------------------------- |
| GLM-4.7 (Z.AI)        | Gemini Flash (Google), Claude Haiku (Anthropic) |
| Gemini Flash (Google) | GLM-4.7 (Z.AI), Claude Haiku (Anthropic)        |
| DeepSeek (DeepSeek)   | Gemini Flash (Google), GLM-4.7 (Z.AI)           |
| Llama 3.3 (Groq)      | Gemini Flash (Google), GLM-4.7 (Z.AI)           |

## Cost Tiers

### Expensive (Daily Cap: 10 calls)

- openai/gpt-4o: $5/$15 per 1M tokens
- anthropic/claude-opus-4.5: $15/$75 per 1M tokens

### Moderate

- anthropic/claude-sonnet-4.5: $3/$15 per 1M tokens
- google/gemini-3-pro: $1.25/$5 per 1M tokens
- deepseek/deepseek-reasoner: $0.55/$2.19 per 1M tokens

### Cheap (Preferred)

- google/gemini-3-flash: $0.075/$0.30 per 1M tokens
- zai/glm-4.7: $0.60/$2.20 per 1M tokens
- deepseek/deepseek-chat: $0.14/$0.28 per 1M tokens
- groq/llama-3.3-70b: $0.59/$0.79 per 1M tokens

## Agent Selection by Complexity

| Complexity | Coder          | Validator                | Notes                           |
| ---------- | -------------- | ------------------------ | ------------------------------- |
| 1-2        | coder-fast     | None                     | Trivial, no validation          |
| 3-4        | coder          | validator                | Standard with Gemini validation |
| 5-6        | coder          | validator + reviewer     | Dual validation                 |
| 7-8        | coder-ts       | claude-haiku + validator | Multi-validator                 |
| 9-10       | coder-deepseek | validator + escalation   | Critical complexity             |

## Non-Coding Agents

These agents are NOT allowed to write code:

| Agent        | Model             | Allowed Tasks                       |
| ------------ | ----------------- | ----------------------------------- |
| orchestrator | DeepSeek Reasoner | Task routing, workflow only         |
| cheap-worker | Llama 3.1 8B      | Formatting, comments, trivial edits |
| search       | Sonar Pro         | Web search only                     |

## API Endpoints

| Provider   | Base URL                                  |
| ---------- | ----------------------------------------- |
| Z.AI       | https://api.z.ai/api/coding/paas/v4/      |
| DeepSeek   | https://api.deepseek.com/v1               |
| Perplexity | https://api.perplexity.ai                 |
| OpenAI     | https://api.openai.com/v1                 |
| Anthropic  | https://api.anthropic.com                 |
| Google     | https://generativelanguage.googleapis.com |
| Groq       | https://api.groq.com/openai/v1            |
