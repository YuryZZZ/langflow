# PARL: Parallel-Agent Reinforcement Learning

> **Reference**: Kimi K2.5 Technical Report & The Swarm Corporation Implementation

---

## Overview

PARL (Parallel-Agent Reinforcement Learning) is a training paradigm that teaches models to:
1. **Decompose** complex tasks into parallel subtasks
2. **Coordinate** multiple agents simultaneously
3. **Avoid serial collapse** (defaulting to sequential execution)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 ORCHESTRATOR (Trainable)                     │
│                                                              │
│  • Receives complex task                                     │
│  • Decomposes into parallelizable subtasks                   │
│  • Dynamically instantiates subagents                        │
│  • Coordinates workflows across 1,500+ steps                 │
│  • Aggregates results                                        │
└─────────────────────────────────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│ SUBAGENT 1  │   │ SUBAGENT 2  │   │ SUBAGENT N  │
│  (Frozen)   │   │  (Frozen)   │   │  (Frozen)   │
│             │   │             │   │             │
│ Execute     │   │ Execute     │   │ Execute     │
│ subtask     │   │ subtask     │   │ subtask     │
│ Report back │   │ Report back │   │ Report back │
└─────────────┘   └─────────────┘   └─────────────┘
```

### Key Components

| Component | Role | Training |
|-----------|------|----------|
| **Orchestrator** | Task decomposition, coordination | Trainable |
| **Subagents** | Execute specific subtasks | Frozen |

---

## Kimi K2.5 Specifications

| Metric | Value |
|--------|-------|
| Total Parameters | 1.04 trillion |
| Active Parameters | 32 billion |
| Experts | 384 (MoE) |
| Context Window | 256K tokens |
| Max Sub-agents | 100 |
| Max Coordinated Steps | 1,500+ |

---

## Reward Function

PARL uses staged reward shaping to balance parallelism with task success:

```
R_t = λ_aux(e) · r_parallel + (1 - λ_aux(e)) · (𝟙[success] · Q(τ))
```

### Components

| Symbol | Meaning | Behavior |
|--------|---------|----------|
| `λ_aux(e)` | Auxiliary weight | Anneals 0.1 → 0.0 over training |
| `r_parallel` | Instantiation reward | Encourages subagent creation |
| `𝟙[success]` | Success indicator | Binary (0 or 1) |
| `Q(τ)` | Trajectory quality | End-to-end task quality |

### Training Phases

1. **Early Training** (λ_aux = 0.1): Prioritizes parallelism exploration
2. **Late Training** (λ_aux → 0.0): Shifts focus to task success

---

## Critical Steps Metric

Instead of counting total steps, PARL measures **latency-aware critical steps**:

```
CriticalSteps = Σ(S_main^(t) + max_i S_sub,i^(t))
```

This measures:
- `S_main^(t)` = Orchestrator overhead at step t
- `max_i S_sub,i^(t)` = Slowest subagent at step t (the bottleneck)

### Why Critical Steps?

- Spawning more agents only helps if it shortens the **slowest path**
- Prevents "fake parallelism" (agents spawned but no latency reduction)
- Inspired by **critical path analysis** in parallel computing

---

## Serial Collapse Problem

### What is Serial Collapse?

Even with parallel capacity, naive systems default to sequential execution:

```
❌ BAD: Task → Agent1 → Agent2 → Agent3 → Result
         (sequential, slow)

✅ GOOD: Task → [Agent1, Agent2, Agent3] → Result
         (parallel, fast)
```

### How PARL Prevents It

1. **Staged Reward Shaping**: Early rewards for parallelism
2. **Computational Bottleneck**: Makes sequential execution impractical
3. **Critical Steps Metric**: Penalizes serial bottlenecks

---

## Performance Benchmarks

| Metric | Single Agent | PARL Swarm | Improvement |
|--------|--------------|------------|-------------|
| Runtime | 100% | 20% | **80% reduction** |
| Critical Steps | 1x | 0.22-0.33x | **3-4.5x faster** |
| Wall-clock | 1x | 0.22x | **4.5x speedup** |

---

## Implementation in OpenCode

### Current Setup (v9.1)

```
ORCHESTRATOR: moonshot/kimi-k2.5
    │
    ├── Uses PARL for native swarm orchestration
    ├── Can spawn up to 100 sub-agents
    ├── Executes 200-300 tool calls autonomously
    │
    └── Dispatches via TaskBus/parallel MCP
         │
         ▼
    ┌────────────────────────────────────────────┐
    │  5 PARALLEL PLANNERS (via parallel MCP)    │
    │  planner-1: Gemini 3 Pro (Architecture)    │
    │  planner-2: Claude Sonnet (Security)       │
    │  planner-3: Kimi K2.5 32K (Creative)       │
    │  planner-4: DeepSeek Reasoner (Logic)      │
    │  planner-5: GLM-4.7 (Implementation)       │
    └────────────────────────────────────────────┘
         │
         ▼
    ┌────────────────────────────────────────────┐
    │  5+ PARALLEL CODERS                        │
    │  coder: GLM-4.7 (Primary)                  │
    │  coder-fast: Gemini 3 Flash                │
    │  coder-kimi: Kimi K2.5 32K                 │
    │  coder-deepseek: DeepSeek V3               │
    │  coder-groq: Llama 3.3 70B                 │
    └────────────────────────────────────────────┘
```

### How TaskBus Implements PARL

1. **Task Decomposition**: Orchestrator calls `parallel.parallel_dispatch_planners()`
2. **Parallel Execution**: TaskBus enqueues to PostgreSQL, workers process concurrently
3. **Result Aggregation**: Orchestrator polls `taskbus.get_run_status()`
4. **Critical Path**: Full results stored in PostgreSQL, summaries to orchestrator

---

## API Example (Python)

```python
from parl import PARLReward, CriticalStepsMetric
import torch

# Initialize reward function
reward_fn = PARLReward(
    lambda_init=0.1,
    lambda_final=0.0,
    total_training_steps=10000,
    device='cuda'
)

# Compute rewards during training
rewards = reward_fn.compute_full_reward(
    num_subagents=torch.tensor([25, 30, 40]),  # Agents spawned
    trajectory_features=torch.randn(3, 64),
    success=torch.tensor([1.0, 1.0, 0.0]),      # Task success
    training_step=5000,
    max_subagents=100
)

# Evaluate critical steps
metric = CriticalStepsMetric()
critical_steps = metric(main_steps, sub_steps)
```

---

## Sources

- [Kimi K2.5 Technical Report](https://www.kimi.com/blog/kimi-k2-5.html)
- [The Swarm Corporation PARL GitHub](https://github.com/The-Swarm-Corporation/PARL)
- [DataCamp Kimi K2.5 Agent Swarm Guide](https://www.datacamp.com/tutorial/kimi-k2-agent-swarm-guide)
- [DEV.to Ultimate Guide to Kimi K2.5](https://dev.to/czmilo/kimi-k25-in-2026-the-ultimate-guide-to-open-source-visual-agentic-intelligence-18od)
