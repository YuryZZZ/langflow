# OpenCode v9.2 - PARL MULTI-AGENT SWARM

**Orchestrator**: Kimi K2.5 (Moonshot) - DISPATCH ONLY
- Provider: Moonshot AI
- Version: Kimi K2.5 (1T MoE, 32B active params)
- Architecture: PARL (Parallel Agent Reasoning Layer)
- Mode: Multi-Agent Dispatch - NEVER writes files directly
- Capabilities: Task decomposition, parallel dispatch, coordination

## CRITICAL RULE: ORCHESTRATOR = DISPATCH ONLY

```
⚠️ ORCHESTRATOR MUST NEVER:
- Write files directly (no filesystem_write_file)
- Edit files directly (no edit/write tools)
- Run bash commands (no bash tool)
- Do work itself

✅ ORCHESTRATOR MUST ALWAYS:
- Call taskbus.create_task() to create work items
- Call parallel.parallel_dispatch_planners() for planning
- Call parallel.parallel_dispatch_workers() for coding
- Monitor via taskbus.get_run_status()
```

## System Architecture

### Multi-Agent Tree Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR (Kimi K2.5)                  │
│                    DISPATCH ONLY - NO DIRECT WORK            │
├──────────────────────────────────────────────────────────────┤
│           ↓ DISPATCH via taskbus/parallel MCP ↓              │
├──────────────────────────────────────────────────────────────┤
│         PLANNERS (5)              CODERS (10+)               │
│  ┌─────────────────────┐    ┌─────────────────────┐         │
│  │ planner-1 (Gemini)  │    │ coder (Kimi K2.5)   │         │
│  │ planner-2 (Claude)  │    │ coder-fast (Gemini) │         │
│  │ planner-3 (Moonshot)│    │ coder-glm (GLM-4.7) │         │
│  │ planner-4 (DeepSeek)│    │ coder-deepseek      │         │
│  │ planner-5 (GLM-4.7) │    │ coder-groq          │         │
│  └─────────────────────┘    │ build (GPT-5.2)     │         │
│                             │ tester (GLM-4.7)    │         │
│                             │ reviewer (Claude)   │         │
│                             │ validator (Gemini)  │         │
│                             └─────────────────────┘         │
└──────────────────────────────────────────────────────────────┘
```

### Correct Workflow (Multi-Agent)

```
USER REQUEST
    │
    ├─► Orchestrator (Kimi K2.5) - DISPATCH ONLY
    │   ├─ Analyze request
    │   ├─ Decompose into tasks
    │   └─ Create taskbus run
    │
    ├─► taskbus.create_run()
    │   └─ Creates run with task queue
    │
    ├─► parallel.parallel_dispatch_planners()
    │   ├─► planner-1 (Gemini Pro): Architecture
    │   ├─► planner-2 (Claude): Security
    │   ├─► planner-3 (Moonshot): Workflow
    │   ├─► planner-4 (DeepSeek): Logic
    │   └─► planner-5 (GLM-4.7): Implementation
    │
    ├─► Planners create sub-tasks → taskbus
    │
    ├─► parallel.parallel_dispatch_workers()
    │   ├─► coder (Kimi K2.5): Main coding
    │   ├─► coder-fast (Gemini Flash): Quick edits
    │   ├─► coder-glm (GLM-4.7): Stable coding
    │   ├─► validator (Gemini): Validation
    │   └─► tester (GLM-4.7): Testing
    │
    └─► Workers complete tasks → taskbus.complete_task()
```

### WRONG Workflow (Single Agent - DO NOT DO THIS)

```
❌ WRONG - Orchestrator doing work directly:
    │
    └─► Orchestrator (Kimi K2.5)
        ├─ filesystem_write_file  ← WRONG!
        ├─ edit                   ← WRONG!
        └─ bash                   ← WRONG!
```

## Provider Distribution

| Provider | % | Role |
|----------|---|------|
| Moonshot | 25% | Orchestrator, Primary Coder |
| Google | 20% | Planning, Validation |
| Z.AI | 20% | Backup Coding, Testing |
| DeepSeek | 15% | Logic, Debugging |
| Anthropic | 12% | Security, Review |
| Groq | 5% | Ultra-fast bulk |
| OpenAI | 3% | Escalation only |

## Agent Roles

| Role | Model | MCP Access |
|------|-------|------------|
| orchestrator | Kimi K2.5 | taskbus, parallel, memory ONLY |
| coder | Kimi K2.5 | filesystem, edit, write, bash |
| coder-fast | Gemini Flash | filesystem, edit, write |
| coder-glm | GLM-4.7 | filesystem, edit, write, bash |
| planner-* | Various | read, glob, grep |
| validator | Gemini Flash | read, glob, grep |
| tester | GLM-4.7 | filesystem, bash |

## Aggressive Fallback (v9.2)

```json
{
  "retry": {
    "maxAttempts": 2,
    "initialDelayMs": 1000,
    "maxDelayMs": 5000,
    "failFast": true,
    "autoFallback": true
  },
  "timeout": 30000
}
```

Fallback chain:
- Kimi K2.5 → GLM-4.7 → DeepSeek → Gemini Flash

## MCP Server Permissions

| MCP Server | Orchestrator | Coders | Planners |
|------------|-------------|--------|----------|
| taskbus | ✅ | ✅ | ✅ |
| parallel | ✅ | ❌ | ❌ |
| memory | ✅ | ✅ | ✅ |
| filesystem | ❌ | ✅ | ❌ |
| github | ❌ | ✅ | ❌ |
| playwright | ❌ | ✅ | ❌ |

## Configuration Files

- `opencode.json`: Main configuration
- `SYSTEM.md`: This file
- `MODELS.md`: Model reference with token limits
- `.ai/PROJECT_KNOWLEDGE.md`: Project knowledge
- `.env`: API keys

---
*OpenCode v9.2 - PARL Architecture - Last Updated: 2026-02-02*
