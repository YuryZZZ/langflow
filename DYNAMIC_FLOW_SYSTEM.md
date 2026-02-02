# Dynamic Flow Generator System

## Overview

This system allows you to submit any task or question, and OpenCode will:
1. **Research and analyze** the task
2. **Decompose** it into subtasks for appropriate agents
3. **Generate prompts** programmatically for each agent
4. **Create a new Langflow flow** with all agents connected
5. **Execute via MCP** with memory persistence to avoid truncation

## Features

### ✅ Automatic Agent Selection
The system analyzes your task and automatically selects the right agents:
- **Research tasks** → Perplexity Sonar Pro
- **Security tasks** → Claude Sonnet 4.5
- **Complex logic** → DeepSeek V3.2
- **Fast edits** → Gemini 3 Flash
- **Architecture** → Gemini 3 Pro
- **Implementation** → GLM-4.7
- **Testing** → GLM-4.7
- **Review** → Claude Sonnet 4.5
- **Validation** → Cross-model (Gemini + Claude)

### ✅ Correct OpenCode Models (v9.5)
All agents use the correct models from MODELS.md:

**Orchestrator:**
- Kimi K2.5 (Moonshot) - 1T MoE, 256K context

**Planners (5 parallel):**
1. Gemini 3 Pro (Google) - Architecture & Data
2. Claude Sonnet 4.5 (Anthropic) - Security & Validation
3. Kimi K2.5 (Moonshot) - Workflow & Creative
4. DeepSeek V3.2 - Logic & Algorithms
5. GLM-4.7 (Z.AI) - Implementation & Testing

**Coders:**
- Gemini 3 Flash - Fast edits (<2s)
- Kimi K2.5 - Primary coding
- GLM-4.7 - Stable implementation
- DeepSeek V3.2 - Complex logic

**Validators:**
- Gemini 3 Flash (Google family)
- Claude Haiku 4.5 (Anthropic family)

### ✅ MCP Integration
- Uses MCP gateways for cross-layer memory
- Prevents context truncation
- Enables real-time progress monitoring
- Fallback to local memory if MCP unavailable

### ✅ Dynamic Flow Creation
Every serious task creates a **new Langflow flow**:
- Unique flow ID
- All agents properly connected
- Edges show data flow
- Memory component integrated
- Saved to `agent/workflows/dynamic/`

## Usage

### Quick Start

```bash
# Submit a task
python run_task.py "Create a secure user authentication API with JWT and tests"

# Create flow without executing
python run_task.py "Analyze this codebase for security vulnerabilities" --no-execute
```

### Python API

```python
from dynamic_flow_generator import DynamicFlowGenerator

# Initialize
generator = DynamicFlowGenerator()

# Submit task
result = generator.process_user_task(
    user_task="Your complex task here",
    auto_execute=True
)

# Get flow path
flow_path = result['flow_path']

# Execute manually later
execution = generator.execute_flow(flow_path)
```

## How It Works

### 1. Task Analysis
```python
analysis = generator.analyze_task(user_task)
# Returns: required_agents, complexity, workflow_type
```

### 2. Prompt Generation
Each agent gets a custom prompt:
```python
prompt = generator.generate_agent_prompt(agent_id, user_task, context)
# Role-specific instructions
# MCP memory configuration
# Constraints and expected outputs
```

### 3. Flow Creation
Creates a complete Langflow flow:
```json
{
  "name": "DynamicFlow_abc123_20260202_143022",
  "components": [...],
  "edges": [...],
  "execution_config": {...}
}
```

### 4. Execution
- Dispatches to parallel agents
- Monitors progress via MCP
- Validates outputs
- Aggregates results

## Example Flow Structure

```
User Task: "Create a secure API with authentication"

Generated Flow:
├── Orchestrator (Kimi K2.5)
│   ├── dispatches → Security Analyst (Claude)
│   ├── dispatches → Architect (Gemini Pro)
│   ├── dispatches → Coder (Kimi K2.5)
│   ├── dispatches → Tester (GLM-4.7)
│   ├── dispatches → Reviewer (Claude)
│   └── dispatches → Validator (Gemini Flash)
│
├── All agents → Shared Memory (MCP)
│
└── Results Aggregator
```

## Memory & MCP

### Avoiding Truncation
- Large prompts stored in MCP memory
- Agents read context from memory
- Progress tracked in real-time
- No context window limits

### MCP Endpoints
- Memory: `/api/mcp/memory`
- Parallel execution: `/api/mcp/parallel`
- Status: `/api/mcp/status/{execution_id}`

## File Structure

```
Langflow/
├── dynamic_flow_generator.py      # Main system
├── run_task.py                     # CLI interface
├── mcp_gateway_integration.py      # MCP client
├── agent/workflows/
│   ├── hybrid_multiflow.json      # Base template
│   ├── hybrid_multiflow_updated.json  # Updated with correct models
│   └── dynamic/                    # Generated flows
│       ├── DynamicFlow_xxx_20260202.json
│       └── ...
└── DYNAMIC_FLOW_SYSTEM.md         # This file
```

## Best Practices

### Task Descriptions
✅ **Good:**
- "Create a REST API with JWT authentication, role-based access control, rate limiting, and comprehensive tests"
- "Research the latest best practices for React performance optimization and implement them"
- "Analyze this codebase for security vulnerabilities and provide a detailed report"

❌ **Too vague:**
- "Build something"
- "Fix the code"
- "Make it better"

### Serious Tasks Only
The system creates a **new flow for every serious task**. This means:
- Each flow is optimized for that specific task
- Agents are selected based on task requirements
- Prompts are tailored to the task
- Results are persisted separately

### Monitoring
Check flow execution:
```bash
# List all dynamic flows
ls -la agent/workflows/dynamic/

# Check MCP status
curl https://langflow-mcp.onrender.com/health
```

## Model Provider Distribution

Following MODELS.md guidelines:

| Provider | Percentage | Models |
|----------|-----------|---------|
| Moonshot | 25% | Kimi K2.5 (Orchestrator, Coder) |
| Google | 20% | Gemini 3 Pro/Flash (Planners, Fast coding) |
| Z.AI | 20% | GLM-4.7 (Implementation, Testing) |
| DeepSeek | 15% | DeepSeek V3.2 (Logic, Algorithms) |
| Anthropic | 12% | Claude Sonnet 4.5 (Security, Review) |
| Groq | 5% | Llama 3.3 70B (Ultra-fast tasks) |
| OpenAI | 3% | GPT-5.2 (Critical reasoning) |

## Troubleshooting

### MCP Connection Failed
```python
# Check connection
generator = DynamicFlowGenerator()
if generator.hybrid_system.use_mcp:
    print("MCP connected!")
else:
    print("Using local fallback")
```

### Flow Not Executing
- Check if MCP gateway is accessible
- Verify flow JSON is valid
- Check agent configurations

### Memory Issues
- MCP memory is used automatically for large contexts
- Local SQLite fallback if MCP unavailable
- Progress saved every 5 seconds

## Next Steps

1. **Submit your first task:**
   ```bash
   python run_task.py "Your complex task here"
   ```

2. **Check generated flows:**
   ```bash
   ls agent/workflows/dynamic/
   ```

3. **View in Langflow:**
   - Go to: https://langflow-7vd3.onrender.com
   - Import flow from `agent/workflows/dynamic/`
   - See all agents connected

4. **Monitor execution:**
   - Check MCP gateway logs
   - View task progress
   - Review aggregated results

## Integration with OpenCode

This system integrates with OpenCode's:
- **TaskBus** for task queuing
- **Memory MCP** for persistence
- **Parallel execution** for speed
- **PARL** (Parallel-Agent Reinforcement Learning) for orchestration

Every task gets the full power of OpenCode's multi-agent system, visualized in Langflow.
