# PARL Implementation Guide for OpenCode v9.1

> Full integration of Parallel-Agent Reinforcement Learning with OpenCode's TaskBus

---

## Current Architecture vs PARL Enhancement

### Current State (v9.1)
```
Orchestrator (Kimi K2.5)
    │
    ├── parallel.parallel_dispatch_planners() → 5 planners
    │
    └── taskbus.* → PostgreSQL queue → Background workers
```

### Target State (PARL-Native)
```
Orchestrator (Kimi K2.5 - PARL-trained)
    │
    ├── PARL Task Decomposition
    │   ├── Analyzes task complexity
    │   ├── Identifies parallelizable subtasks
    │   └── Estimates critical path
    │
    ├── Dynamic Subagent Spawning (up to 100)
    │   ├── Frozen execution workers
    │   ├── Session isolation per agent
    │   └── Automatic model resolution
    │
    ├── Critical Steps Tracking
    │   ├── CriticalSteps = Σ(S_main + max S_sub)
    │   ├── Prevents fake parallelism
    │   └── Latency-aware optimization
    │
    └── Result Aggregation
        ├── Parallel stream merging
        ├── Conflict resolution
        └── Knowledge graph update
```

---

## Implementation Roadmap

### Phase 1: Enhanced TaskBus (postgres_mcp.py)

Add PARL-specific tables and functions:

```sql
-- Critical Steps Tracking
CREATE TABLE IF NOT EXISTS critical_steps (
    id SERIAL PRIMARY KEY,
    run_id UUID NOT NULL,
    step_number INT NOT NULL,
    orchestrator_steps INT DEFAULT 0,
    max_subagent_steps INT DEFAULT 0,
    critical_step_total INT GENERATED ALWAYS AS (orchestrator_steps + max_subagent_steps) STORED,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Subagent Sessions (PARL isolation)
CREATE TABLE IF NOT EXISTS subagent_sessions (
    id SERIAL PRIMARY KEY,
    run_id UUID NOT NULL,
    subagent_id VARCHAR(64) NOT NULL,
    model VARCHAR(128),
    spawned_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    status VARCHAR(32) DEFAULT 'active',
    context_tokens INT DEFAULT 0,
    steps_executed INT DEFAULT 0,
    UNIQUE(run_id, subagent_id)
);

-- Parallel Execution Graph
CREATE TABLE IF NOT EXISTS execution_graph (
    id SERIAL PRIMARY KEY,
    run_id UUID NOT NULL,
    parent_task_id UUID,
    child_task_id UUID NOT NULL,
    dependency_type VARCHAR(32), -- 'parallel', 'sequential', 'aggregate'
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Phase 2: Enhanced parallel_mcp.py

Add PARL orchestration functions:

```python
# New tools to add to parallel_mcp.py

def parl_decompose_task(
    task_description: str,
    max_subagents: int = 100,
    parallelism_threshold: float = 0.5
) -> Dict[str, Any]:
    """
    PARL Task Decomposition

    Uses the orchestrator's trained decomposition to:
    1. Analyze task complexity
    2. Identify parallelizable subtasks
    3. Create execution graph
    4. Estimate critical steps
    """
    tb = get_taskbus()
    run_id = tb.create_run(f"PARL: {task_description[:50]}...")

    # Create decomposition request
    decomposition = {
        "task": task_description,
        "max_parallel": max_subagents,
        "strategy": "parl_native",  # Use Kimi K2.5's trained decomposition
    }

    # The orchestrator (Kimi K2.5) will decompose via its PARL training
    # This is a hint to trigger PARL mode
    return {
        "run_id": run_id,
        "decomposition_mode": "parl",
        "max_subagents": max_subagents,
        "status": "awaiting_orchestrator_decomposition",
        "hint": "Orchestrator should decompose into parallelizable subtasks using PARL training"
    }


def parl_spawn_subagent(
    run_id: str,
    subagent_type: str,
    task: str,
    model: Optional[str] = None
) -> Dict[str, Any]:
    """
    Spawn a frozen subagent for PARL execution.

    Subagents:
    - Are frozen (no training updates)
    - Have isolated session context
    - Execute assigned subtask only
    - Report back to orchestrator
    """
    tb = get_taskbus()

    # Auto-resolve model from OpenCode config if not specified
    if not model:
        model = _resolve_model_for_type(subagent_type)

    subagent_id = f"sub_{uuid.uuid4().hex[:8]}"

    # Register subagent session
    with tb.conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO subagent_sessions (run_id, subagent_id, model, status)
                VALUES (%s, %s, %s, 'spawning')
                RETURNING id
            """, (run_id, subagent_id, model))
            session_id = cur.fetchone()[0]
            conn.commit()

    # Create task for this subagent
    task_id = tb.create_task(
        task_type=f"parl_subagent_{subagent_type}",
        agent=subagent_type,
        payload={
            "subagent_id": subagent_id,
            "session_id": session_id,
            "task": task,
            "model": model,
            "frozen": True,  # Subagent doesn't learn
        },
        priority=8
    )

    return {
        "subagent_id": subagent_id,
        "session_id": session_id,
        "task_id": task_id,
        "model": model,
        "status": "spawned"
    }


def parl_track_critical_steps(
    run_id: str,
    orchestrator_steps: int,
    subagent_steps: Dict[str, int]
) -> Dict[str, Any]:
    """
    Track critical steps for PARL optimization.

    CriticalSteps = Σ(S_main + max(S_sub_i))

    This measures the true execution time considering parallel operations.
    """
    tb = get_taskbus()

    max_sub_steps = max(subagent_steps.values()) if subagent_steps else 0

    with tb.conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO critical_steps (run_id, step_number, orchestrator_steps, max_subagent_steps)
                SELECT %s, COALESCE(MAX(step_number), 0) + 1, %s, %s
                FROM critical_steps WHERE run_id = %s
                RETURNING step_number, critical_step_total
            """, (run_id, orchestrator_steps, max_sub_steps, run_id))
            result = cur.fetchone()
            conn.commit()

    return {
        "run_id": run_id,
        "step_number": result[0],
        "orchestrator_steps": orchestrator_steps,
        "max_subagent_steps": max_sub_steps,
        "critical_steps_total": result[1],
        "subagent_breakdown": subagent_steps
    }


def parl_aggregate_results(
    run_id: str,
    aggregation_strategy: str = "merge"
) -> Dict[str, Any]:
    """
    Aggregate results from parallel subagents.

    Strategies:
    - 'merge': Combine all results
    - 'vote': Use majority consensus
    - 'best': Select highest quality result
    - 'sequential': Chain results in order
    """
    tb = get_taskbus()

    # Get all completed subagent results
    with tb.conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT t.result, s.subagent_id, s.model
                FROM tasks t
                JOIN subagent_sessions s ON t.payload->>'subagent_id' = s.subagent_id
                WHERE s.run_id = %s AND t.status = 'completed'
            """, (run_id,))
            results = cur.fetchall()

    if not results:
        return {"status": "no_results", "run_id": run_id}

    # Aggregate based on strategy
    aggregated = {
        "run_id": run_id,
        "strategy": aggregation_strategy,
        "subagent_count": len(results),
        "results": [{"subagent_id": r[1], "model": r[2], "result": r[0]} for r in results]
    }

    return aggregated
```

### Phase 3: Reward Shaping Integration

Add reward tracking for PARL optimization:

```python
def parl_compute_reward(
    run_id: str,
    success: bool,
    num_subagents: int,
    critical_steps: int,
    training_step: int = 0,
    lambda_init: float = 0.1,
    lambda_final: float = 0.0,
    total_training_steps: int = 10000
) -> Dict[str, Any]:
    """
    PARL Reward Function:
    R_t = λ_aux(e) · r_parallel + (1 - λ_aux(e)) · (𝟙[success] · Q(τ))

    Components:
    - λ_aux(e): Anneals from lambda_init to lambda_final
    - r_parallel: Instantiation reward (encourages subagent creation)
    - success: Binary task success indicator
    - Q(τ): Quality metric based on critical steps efficiency
    """
    # Compute annealing weight
    progress = min(1.0, training_step / total_training_steps)
    lambda_aux = lambda_init + (lambda_final - lambda_init) * progress

    # Instantiation reward (normalized by max subagents)
    r_parallel = num_subagents / 100.0

    # Quality metric (inverse of critical steps, normalized)
    q_tau = 1.0 / (1.0 + critical_steps / 100.0) if success else 0.0

    # Combined reward
    reward = lambda_aux * r_parallel + (1 - lambda_aux) * (1.0 if success else 0.0) * q_tau

    return {
        "run_id": run_id,
        "reward": reward,
        "components": {
            "lambda_aux": lambda_aux,
            "r_parallel": r_parallel,
            "success_indicator": 1.0 if success else 0.0,
            "q_tau": q_tau
        },
        "meta": {
            "num_subagents": num_subagents,
            "critical_steps": critical_steps,
            "training_step": training_step
        }
    }
```

---

## MCP Tool Additions

Add these tools to `TOOLS_LIST` in parallel_mcp.py:

```python
PARL_TOOLS = [
    {
        "name": "parl_decompose_task",
        "description": "PARL: Decompose complex task into parallelizable subtasks. Triggers Kimi K2.5's trained decomposition.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_description": {"type": "string"},
                "max_subagents": {"type": "integer", "default": 100},
                "parallelism_threshold": {"type": "number", "default": 0.5}
            },
            "required": ["task_description"]
        }
    },
    {
        "name": "parl_spawn_subagent",
        "description": "PARL: Spawn a frozen subagent for parallel execution with isolated session.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string"},
                "subagent_type": {"type": "string"},
                "task": {"type": "string"},
                "model": {"type": "string"}
            },
            "required": ["run_id", "subagent_type", "task"]
        }
    },
    {
        "name": "parl_track_critical_steps",
        "description": "PARL: Track critical steps for latency-aware optimization.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string"},
                "orchestrator_steps": {"type": "integer"},
                "subagent_steps": {"type": "object"}
            },
            "required": ["run_id", "orchestrator_steps", "subagent_steps"]
        }
    },
    {
        "name": "parl_aggregate_results",
        "description": "PARL: Aggregate results from parallel subagents.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string"},
                "aggregation_strategy": {
                    "type": "string",
                    "enum": ["merge", "vote", "best", "sequential"],
                    "default": "merge"
                }
            },
            "required": ["run_id"]
        }
    },
    {
        "name": "parl_compute_reward",
        "description": "PARL: Compute reward for training optimization (informational).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string"},
                "success": {"type": "boolean"},
                "num_subagents": {"type": "integer"},
                "critical_steps": {"type": "integer"}
            },
            "required": ["run_id", "success", "num_subagents", "critical_steps"]
        }
    }
]
```

---

## Orchestrator Prompt Enhancement

Update orchestrator description in opencode.json:

```json
"orchestrator": {
  "model": "moonshot/kimi-k2.5",
  "description": "ORCHESTRATOR v9.1 - Kimi K2.5 (1T MoE, PARL-native swarm)

PARL ARCHITECTURE:
- Native parallel decomposition via PARL training
- Spawn up to 100 frozen subagents
- Critical steps tracking for latency optimization
- Avoids serial collapse through staged reward shaping

MANDATORY PARL WORKFLOW:
1. parl_decompose_task() - Analyze and decompose complex task
2. For each subtask: parl_spawn_subagent() - Create isolated workers
3. Workers execute in parallel (frozen, no learning)
4. parl_track_critical_steps() - Monitor latency metric
5. parl_aggregate_results() - Merge parallel outputs
6. memory.create_entities() - Store knowledge

CRITICAL RULES:
- NEVER execute sequentially if parallel is possible
- Track CriticalSteps = Σ(S_main + max S_sub_i)
- Subagents are FROZEN - they execute, don't decide
- Orchestrator DECOMPOSES and COORDINATES only

ALLOWED MCP:
- parl.*, parallel.*, taskbus.*, memory.*, context-compactor.*

FORBIDDEN (delegate to subagents):
- edit, write, bash, fetch, codebase-map"
}
```

---

## Integration with Oh-My-OpenCode / Orchestra

For full PARL support, integrate with existing orchestration frameworks:

### Orchestra Integration (Hub-and-Spoke)

```python
# In parallel_mcp.py, add Orchestra compatibility

def orchestra_task_start(
    worker_profile: str,
    task: str,
    run_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Orchestra-compatible task_start.
    Maps to PARL subagent spawning.
    """
    if not run_id:
        tb = get_taskbus()
        run_id = tb.get_current_run() or tb.create_run("orchestra_task")

    # Map Orchestra profiles to OpenCode agents
    profile_map = {
        "vision": "multimodal",
        "docs": "researcher",
        "coder": "coder",
        "architect": "planner-1",
        "explorer": "explore",
        "memory": "memory"
    }

    agent = profile_map.get(worker_profile, "coder")
    return parl_spawn_subagent(run_id, agent, task)


def orchestra_task_await(task_id: str) -> Dict[str, Any]:
    """Orchestra-compatible task_await."""
    tb = get_taskbus()
    # Poll until complete
    while True:
        task = tb.get_task(task_id)
        if task and task.get("status") in ("completed", "failed"):
            return task
        time.sleep(0.5)


def orchestra_task_peek(task_id: str) -> Dict[str, Any]:
    """Orchestra-compatible task_peek (non-blocking)."""
    tb = get_taskbus()
    return tb.get_task(task_id) or {"status": "unknown"}
```

---

## Deployment Checklist

1. **Database Migration**
   ```bash
   psql -U postgres -d opencode_taskbus -f parl_tables.sql
   ```

2. **Update parallel_mcp.py**
   - Add PARL functions
   - Add PARL tools to TOOLS_LIST
   - Update tool handler

3. **Update opencode.json**
   - Enhance orchestrator description
   - Add parl to mcpAllowlist

4. **Update MODELS.md**
   - Document PARL capabilities
   - Update architecture diagram

5. **Test**
   ```bash
   # Verify PARL tools are available
   opencode --agent orchestrator "Use parl_decompose_task to analyze: Build a REST API"
   ```

---

## Performance Expectations

| Metric | Without PARL | With PARL |
|--------|--------------|-----------|
| Runtime (complex task) | 100% | ~20% |
| Critical Steps | 1x | 0.22-0.33x |
| Max Parallel Agents | 5 (manual) | 100 (auto) |
| Serial Collapse Risk | High | Low |

---

## Sources

- [Kimi K2.5 Technical Report](https://www.kimi.com/blog/kimi-k2-5.html)
- [PARL GitHub](https://github.com/The-Swarm-Corporation/PARL)
- [Open Orchestra](https://github.com/0xSero/orchestra)
- [Oh-My-OpenCode](https://github.com/code-yeongyu/oh-my-opencode)
- [OpenCode Docs](https://opencode.ai/docs/agents/)
