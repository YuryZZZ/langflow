# OpenCode Model Reference (v7.5 - DeepSeek V3 Edition)

## Primary Models

| Role              | Model             | Provider | Context | Output | Cost/1M      |
| ----------------- | ----------------- | -------- | ------- | ------ | ------------ |
| **Orchestrator**  | DeepSeek V3 Chat  | DeepSeek | 128K    | 8K     | $0.27/$1.10  |
| **Primary Coder** | GLM-4.7           | Z.AI     | 256K    | 32K    | $0.60/$2.20  |
| **Fast Coder**    | Gemini 3 Flash    | Google   | 1M      | 65K    | $0.075/$0.30 |
| **Validator**     | Gemini 3 Flash    | Google   | 1M      | 65K    | $0.075/$0.30 |

## Provider Distribution

### DeepSeek (15% - 4 agents)

```
deepseek-chat (V3):
  - orchestrator (PRIMARY)
  - coder-deepseek

deepseek-reasoner:
  - deepseek-think
  - planner-4
```

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
gemini-3-pro-preview:
  - planner-1
  - debugger
  - analyst
  - gemini-pro (escalation)

gemini-3-flash-preview:
  - validator
  - coder-fast
  - gemini-flash (escalation)
```

### OpenAI (10% - 3 agents)

```
gpt-5.2:
  - gpt-5.2 (escalation)

gpt-5.1-codex:
  - build
  - planner-3
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

### DeepSeek V3 Chat (Orchestrator)

- **Context**: 128,000 tokens
- **Output**: 8,192 tokens
- **Role**: Task routing and workflow enforcement
- **Key Features**:
  - Best coordination for swarm architecture
  - Full tool/function calling support
  - Cost-effective ($0.27/1M input)
  - Does NOT code directly

### GLM-4.7 (Primary Coder)

- **Released**: December 22, 2025
- **Context**: 256,000 tokens
- **Output**: 32,000 tokens
- **Key Features**:
  - Preserved Thinking (maintains reasoning across turns)
  - Vibe Coding (enhanced UI generation)
  - Agentic stability for multi-step tasks

### Gemini 3 Flash (Fast Coder/Validator)

- **Context**: 1M+ tokens
- **Output**: 65K tokens
- **Key Features**:
  - Sub-2s response time
  - Large context for validation
  - Cost-effective

### Gemini 3 Pro (Fallback Orchestrator)

- **Context**: 1M tokens
- **Output**: 64K tokens
- **Key Features**:
  - Massive context window
  - Full tool support
  - Used as orchestrator fallback

## Cross-Model Validation Rules

Coders MUST be validated by different model families:

| Coder                 | Valid Validators                                |
| --------------------- | ----------------------------------------------- |
| GLM-4.7 (Z.AI)        | Gemini Flash (Google), Claude Haiku (Anthropic) |
| Gemini Flash (Google) | GLM-4.7 (Z.AI), Claude Haiku (Anthropic)        |
| DeepSeek (DeepSeek)   | Gemini Flash (Google), GLM-4.7 (Z.AI)           |

## Non-Coding Agents

| Agent        | Model            | Allowed Tasks                       |
| ------------ | ---------------- | ----------------------------------- |
| orchestrator | DeepSeek V3 Chat | Task routing, workflow only         |
| cheap-worker | Llama 3.1 8B     | Formatting, comments, trivial edits |
| search       | Sonar Pro        | Web search only                     |

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
| Tavily     | https://api.tavily.com                    |
