# OpenCode v8.5 - HYPER-SWARM ARCHITECTURE

**Orchestrator**: GPT-5.2 Thinking (OpenAI)
- Provider: OpenAI
- Version: GPT-5.2
- Architecture: Parallel MCP with auto-workers
- Mode: No Monitor Required

## System Architecture

### Multi-Agent Tree Architecture

```
┌──────────────────────────────────────────────────────┐
│                  ORCHESTRATOR                   │
│         DeepSeek V3.2 Chat                      │
├──────────────────────────────────────────────────────┤
│         PLANNERS (5)          WORKERS (8+) │
│  ┌──────────────────────┐    ┌─────────────┐ │
│  │ Planning Layer      │    │ Execution    │ │
│  │                   │    │ Layer       │ │
│  ├─► planner-1       │    ├─► coder      │ │
│  ├─► planner-2       │    ├─► coder-fast  │ │
│  ├─► planner-3       │    ├─► coder-ts   │ │
│  ├─► planner-4       │    ├─► coder-deepseek │ │
│  └─► planner-5       │    ├─► coder-groq  │ │
│  ┌───────────────────┐    ├─► build       │ │
│  │ Consensus       │    ├─► tester     │ │
│  │                │    ├─► reviewer   │ │
│  └──────────────────┘    └─► validator  │ │
│                                └─────────────┘ │
└──────────────────────────────────────────────────────┘
```

### Provider Distribution

```
┌──────────────────────────────────────────────────────┐
│              7 AI PROVIDERS                           │
├──────────────────────────────────────────────────────┤
│  Google (23%)     │ Orchestration, Planning, Analysis  │
│  OpenAI (10%)     │ Primary Coding, Orchestration            │
│  DeepSeek (15%)    │ Fast Coding, Debugging              │
│  Z.AI (20%)        │ Planning, Coding, Testing             │
│  Anthropic (18%)   │ Security, Quality Assurance          │
│  Groq (10%)       │ Bulk Work, Creative Alternatives     │
│  Perplexity (3%)   │ Web Research, Fact-Checking            │
└──────────────────────────────────────────────────────┘
```

## Key Features

- **Parallel Execution**: Tasks execute automatically in background
- **No Monitor Window**: All workers run as daemon processes
- **Async Dispatch**: Never blocks, always returns immediately
- **Cross-Model Validation**: Coders validated by different providers
- **Project Isolation**: Each project has own database and memory
- **15 MCP Servers**: memory, sequential-thinking, taskbus, parallel, filesystem, github, fetch, codebase-map, postgres, playwright, computer-control, tavily, perplexity, context-compactor, apify
- **Progress Watchdog (Rule)**: Check TaskBus progress every 10 minutes and never stop unless user stops. If idle, auto-dispatch planners to research/develop 10x deeper, validate, and test.

## Workflow

```
REQUEST
    │
    ├─► orchestrator (DeepSeek)
    │
    ├─► taskbus.create_run()
    │
    ├─► parallel.parallel_dispatch_planners()
    │         │
    │         ├─► planner-1: Analysis
    │         ├─► planner-2: Reasoning
    │         ├─► planner-3: Planning
    │         ├─► planner-4: Logic
    │         └─► planner-5: Agentic
    │
    ├─► parallel.parallel_dispatch_workers()
    │         │
    │         ├─► coder: Implementation
    │         ├─► coder-fast: Quick Edits
    │         ├─► tester: Test Generation
    │         ├─► reviewer: Code Review
    │         └─► validator: Cross-Validation
    │
    └─► Results synthesized
    │
    ▼
RESPONSE
```

## Configuration Files

- `opencode.json`: Main configuration
- `SYSTEM.md`: System documentation
- `MODELS.md`: Model reference
- `.ai/PROJECT_KNOWLEDGE.md`: Project knowledge base
- `.env`: API keys
- `oc.bat`: Universal launcher

## Agent Roles

| Role | Model | Purpose |
|-------|--------|---------|
| orchestrator | DeepSeek V3.2 | Task routing, workflow orchestration |
| planner-1 | OpenAI GPT-5.2 | Analysis with 400K context |
| planner-2 | OpenAI GPT-5.2 | CoT reasoning with 128K context |
| planner-3 | OpenAI GPT-5.2 | Multi-step planning |
| planner-4 | OpenAI GPT-5.2 | Math & logic tasks |
| planner-5 | OpenAI GPT-5.2 | Agentic workflows |
| coder | Z.AI GLM-4.7 | Primary agentic coding |
| coder-fast | Google Gemini 3 Flash | Fast edits |
| coder-ts | Z.AI GLM-4.7 | TypeScript specialist |
| coder-deepseek | DeepSeek V3.2 | Complex logic |
| coder-groq | Groq Llama 3.3 | Ultra-fast coding |
| build | OpenAI GPT-5.1 Codex | Autonomous builds |
| tester | Z.AI GLM-4.7 | Test generation |
| reviewer | Z.AI GLM-4.7 | Code review |
| validator | Google Gemini 3 Flash | Cross-validation |

## MCP Server Architecture

- **memory**: Knowledge graph storage (.ai/knowledge-graph.json)
- **sequential-thinking**: Chain-of-thought persistence (.ai/sequential-thinking.json)
- **taskbus**: Task queue management (PostgreSQL)
- **parallel**: Parallel execution orchestration
- **filesystem**: File system access
- **github**: Git operations
- **fetch**: Web requests
- **codebase-map**: Code indexing (.ai/codebase-map.db)
- **postgres**: Direct SQL queries
- **playwright**: Browser automation
- **computer-control**: Desktop automation
- **tavily**: AI web search
- **perplexity**: Fact-checking
- **context-compactor**: Conversation compression
- **apify**: Web scraping and data extraction

## Project Isolation

Each project has:
- Unique project ID (UUID)
- Own TaskBus database (PostgreSQL)
- Separate memory graph (.ai/knowledge-graph.json)
- Separate sequential-thinking chains
- Project-specific MCP server configurations

## Status

✅ **OPENCODE CLI WORKING**
- oc.bat launches successfully
- Background workers start automatically
- No hanging after initialization
- MCP servers connect correctly
- Parallel execution operational

---

*Last Updated: 2026-01-28*
