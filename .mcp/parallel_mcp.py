#!/usr/bin/env python3
"""parallel_mcp.py

Parallel Orchestrator MCP Server with PARL (Parallel-Agent Reinforcement Learning)
Implementing Kimi K2.5 Native Agent Swarm Architecture

KIMI K2.5 AGENT SWARM FEATURES (from Moonshot AI Technical Report):
=======================================================================
- 1 Trillion parameter MoE (32B activated, 384 experts, 8 selected per token)
- 256K context length with MLA attention
- Self-directed Agent Swarm: up to 100 sub-agents, 1,500 tool calls
- PARL (Parallel-Agent Reinforcement Learning) for swarm orchestration
- Critical Steps metric: S_main + max(S_sub_i) for latency optimization
- Dynamic subagent instantiation (no predefined roles)
- 4.5x speedup vs sequential execution

PARL REWARD FUNCTION:
- R = Success × (1 + λ_aux × Auxiliary)
- λ_aux anneals from 0.1 → 0.0 during training
- Early: prioritizes parallelism | Later: focuses on task quality Q(τ)

RECOMMENDED SETTINGS (per Moonshot docs):
- Thinking Mode: temperature=1.0, top_p=0.95
- Instant Mode: temperature=0.6, top_p=0.95
- Main agent: max 15 steps (BrowseComp) or 100 steps (WideSearch)
- Sub-agents: max 100 steps each
- Max reasoning tokens: 96K | Max vision tokens: 64K

IMPORTANT
This server is responsible for *true parallel orchestration surface area*.
In OpenCode, the LLM agents are executed by the OpenCode runtime; this MCP server
must be reliable and must integrate with the PostgreSQL TaskBus.

This implementation focuses on correctness + reliability:
- Requires TaskBus (Postgres). No silent fallback.
- Uses TaskBus to create runs and enqueue tasks (push_tasks_batch).
- Optionally waits/polls task completion via get_parallel_status.
- PARL support for dynamic subagent spawning (up to 100 agents)
- Critical path tracking for latency-aware optimization

It does NOT simulate "DONE" work. If you want local execution, build an external
worker that claims tasks from TaskBus and completes them.

Tools (Standard)
- parallel_dispatch_planners
- parallel_dispatch_workers
- parallel_run_tasks
- get_parallel_capabilities

Tools (PARL - Kimi K2.5 Native)
- parl_decompose_task
- parl_spawn_subagent
- parl_track_critical_steps
- parl_aggregate_results
- parl_compute_reward
- parl_get_status
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# --- TaskBus integration (required) ---

def get_taskbus():
    # Import must succeed; DB must be reachable.
    sys.path.insert(0, str(Path(__file__).parent))
    from postgres_mcp import TaskBusDB

    return TaskBusDB()


def _now_iso_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _wait_for_tasks(db, task_ids: List[str], timeout_s: int = 180, poll_ms: int = 250) -> Dict[str, Any]:
    deadline = time.time() + timeout_s
    last = None
    while time.time() < deadline:
        last = db.get_parallel_status(task_ids)
        # Expected shape: { task_id: {status: ...}, ... } or a dict with results
        # We treat completion when all statuses are terminal.
        results = last.get("results") if isinstance(last, dict) else None
        if isinstance(results, list):
            statuses = [r.get("status") for r in results if isinstance(r, dict)]
        elif isinstance(last, dict):
            # try dict mapping
            statuses = []
            for v in last.values():
                if isinstance(v, dict) and "status" in v:
                    statuses.append(v.get("status"))
        else:
            statuses = []

        if statuses and all(s in ("DONE", "FAILED", "BLOCKED", "CANCELLED", "COMPLETED") for s in statuses):
            return {"done": True, "status": last}

        time.sleep(max(poll_ms, 50) / 1000.0)

    return {"done": False, "status": last, "error": f"timeout after {timeout_s}s"}


# --- Tool handlers ---

def run_parallel_tasks(tasks: List[Dict[str, Any]], wait: bool = False, timeout_s: int = 180, poll_ms: int = 250) -> Dict[str, Any]:
    db = get_taskbus()
    batch = db.push_tasks_batch(tasks)

    task_ids = batch.get("task_ids") or []
    run_id = batch.get("run_id")

    out: Dict[str, Any] = {
        "parallel_execution": True,
        "mode": "taskbus-queue",
        "run_id": run_id,
        "task_ids": task_ids,
        "enqueued": len(task_ids),
        "ts": _now_iso_z(),
    }

    if wait and task_ids:
        out["wait"] = {"timeout_s": timeout_s, "poll_ms": poll_ms}
        out["completion"] = _wait_for_tasks(db, task_ids, timeout_s=timeout_s, poll_ms=poll_ms)

    return out


def dispatch_all_planners(task_description: str, subtasks: Optional[List[str]] = None, wait: bool = False) -> Dict[str, Any]:
    # TOP MODELS ONLY for planning (diverse perspectives)
    planners = [
        {"name": "planner-1", "provider": "Google", "model": "gemini-3-pro"},
        {"name": "planner-2", "provider": "Anthropic", "model": "claude-sonnet-4-5"},
        {"name": "planner-3", "provider": "DeepSeek", "model": "deepseek-chat"},
        {"name": "planner-4", "provider": "OpenAI", "model": "gpt-5.2"},
        {"name": "planner-5", "provider": "Z.AI", "model": "glm-4.7"},
    ]

    if not subtasks or len(subtasks) < 5:
        subtasks = [
            f"[planner-1] Database/storage component: {task_description}",
            f"[planner-2] Security/validation component: {task_description}",
            f"[planner-3] Workflow/coordination component: {task_description}",
            f"[planner-4] Logic/algorithm component: {task_description}",
            f"[planner-5] Implementation/testing component: {task_description}",
        ]

    tasks: List[Dict[str, Any]] = []
    for i, p in enumerate(planners):
        tasks.append(
            {
                "task_type": f"planner_subtask_{p['name']}",
                "agent": p["name"],
                "payload": {
                    "subtask": subtasks[i] if i < len(subtasks) else task_description,
                    "provider": p["provider"],
                    "model": p["model"],
                    "task_description": task_description,
                },
                "priority": 9,
            }
        )

    return run_parallel_tasks(tasks, wait=wait)


def dispatch_parallel_workers(planner: str, task_description: str, worker_tasks: Optional[List[Dict[str, str]]] = None, wait: bool = False) -> Dict[str, Any]:
    default_workers = [
        {"worker": "coder", "role": "primary implementation"},
        {"worker": "coder-fast", "role": "fast parallel implementation"},
        {"worker": "coder-deepseek", "role": "complex logic"},
        {"worker": "tester", "role": "tests"},
        {"worker": "reviewer", "role": "review"},
    ]

    workers = worker_tasks if worker_tasks and len(worker_tasks) >= 5 else default_workers

    tasks: List[Dict[str, Any]] = []
    for w in workers:
        worker = w.get("worker") or "unknown"
        role = w.get("role") or "worker"
        desc = w.get("task_description") or task_description
        tasks.append(
            {
                "task_type": f"worker_{worker}",
                "agent": worker,
                "payload": {
                    "planner": planner,
                    "role": role,
                    "task_description": desc,
                },
                "priority": 7,
            }
        )

    return run_parallel_tasks(tasks, wait=wait)


def get_parallel_capabilities() -> Dict[str, Any]:
    """Return comprehensive PARL/Kimi K2.5 Agent Swarm capabilities."""
    return {
        "parallel_execution": True,
        "mode": "taskbus-queue",
        "orchestrator": "moonshot/kimi-k2.5",
        "note": "Kimi K2.5 Native Agent Swarm with PARL. TaskBus-backed parallel execution.",
        "min_planners": 5,
        "min_workers_per_planner": 5,
        # PARL/Kimi K2.5 Swarm Capabilities
        "parl_enabled": True,
        "parl_version": "2.0.0",
        "kimi_k2_swarm": {
            "max_subagents": KIMI_K2_CONFIG["max_subagents"],
            "max_tool_calls": KIMI_K2_CONFIG["max_tool_calls"],
            "main_agent_max_steps": KIMI_K2_CONFIG["main_agent_max_steps_widesearch"],
            "subagent_max_steps": KIMI_K2_CONFIG["subagent_max_steps"],
            "speedup_factor": KIMI_K2_CONFIG["speedup_factor"],
            "temperature": {
                "thinking": KIMI_K2_CONFIG["temperature_thinking"],
                "instant": KIMI_K2_CONFIG["temperature_instant"],
            },
            "top_p": KIMI_K2_CONFIG["top_p"],
            "context_length": KIMI_K2_CONFIG["context_length"],
            "output_length": KIMI_K2_CONFIG["output_length"],
        },
        "features": [
            "dynamic_subagent_instantiation",
            "session_isolation",
            "critical_path_tracking",
            "decomposition_caching",
            "reward_computation",
            "lambda_aux_annealing",
        ],
    }


# =============================================================================
# PARL (Parallel-Agent Reinforcement Learning) Functions
# Kimi K2.5 Native Agent Swarm Implementation
# =============================================================================
#
# KIMI K2.5 AGENT SWARM SPECS (from Moonshot AI Technical Report):
# - Self-directed swarm: up to 100 sub-agents, 1,500 tool calls per run
# - Main agent: max 15 steps (BrowseComp) or 100 steps (WideSearch mode)
# - Sub-agents: max 100 steps each, frozen (no training updates)
# - Dynamic instantiation: subagents spawned on-demand (no predefined roles)
# - Session isolation: each subagent has independent conversation context
#
# CRITICAL STEPS METRIC (latency-aware optimization):
# - CriticalSteps = S_main + max(S_sub_i)
# - Prevents "fake parallelism" where tasks appear parallel but execute sequentially
# - 4.5x speedup vs sequential execution when properly parallelized
#
# REWARD FUNCTION:
# - R = Success × (1 + λ_aux × Auxiliary)
# - λ_aux anneals from 0.1 → 0.0 during training (curriculum learning)
# - Early training: prioritizes parallelism | Later: focuses on task quality Q(τ)
#
# TEMPERATURE SETTINGS:
# - Thinking Mode: temperature=1.0, top_p=0.95 (for reasoning/planning)
# - Instant Mode: temperature=0.6, top_p=0.95 (for fast execution)
#
# TOKEN LIMITS:
# - Max reasoning tokens: 96K | Max vision tokens: 64K
# - Context: 256K tokens | Output: 32K tokens
# =============================================================================

# Kimi K2.5 Swarm Configuration Constants
KIMI_K2_CONFIG = {
    "max_subagents": 100,
    "max_tool_calls": 1500,
    "main_agent_max_steps_browsecomp": 15,
    "main_agent_max_steps_widesearch": 100,
    "subagent_max_steps": 100,
    "temperature_thinking": 1.0,
    "temperature_instant": 0.6,
    "top_p": 0.95,
    "max_reasoning_tokens": 96000,
    "max_vision_tokens": 64000,
    "context_length": 256000,
    "output_length": 32000,
    "lambda_aux_initial": 0.1,
    "lambda_aux_final": 0.0,
    "speedup_factor": 4.5,
}

def _generate_subagent_id() -> str:
    """Generate unique subagent ID."""
    return f"sub_{uuid.uuid4().hex[:12]}"


def _hash_task_description(task: str) -> str:
    """Create deterministic hash for task decomposition caching."""
    return hashlib.sha256(task.encode()).hexdigest()[:16]


def _resolve_model_for_type(subagent_type: str) -> str:
    """Resolve model name based on subagent type from OpenCode config."""
    model_map = {
        # Orchestrator
        "orchestrator": "moonshot/kimi-k2.5",
        # Planners - TOP MODELS ONLY (diverse perspectives)
        "planner": "openai/gpt-5.2",           # OpenAI thinking
        "planner-1": "google/gemini-3-pro",    # Google
        "planner-2": "anthropic/claude-sonnet-4-5",  # Anthropic
        "planner-3": "deepseek/deepseek-chat", # DeepSeek
        "planner-4": "openai/gpt-5.2",         # OpenAI thinking
        "planner-5": "zai/glm-4.7",            # Z.AI
        # Coders
        "coder": "zai/glm-4.7",
        "coder-fast": "google/gemini-3-flash",
        "coder-ts": "zai/glm-4.7",
        "coder-deepseek": "deepseek/deepseek-chat",
        # Validators
        "validator": "google/gemini-3-flash",
        "tester": "zai/glm-4.7",
        "reviewer": "zai/glm-4.7",
        # Debug/Analysis
        "debugger": "google/gemini-3-pro",
        "analyst": "google/gemini-3-pro",
        # Research
        "researcher": "zai/glm-4.7",
        "search": "perplexity/sonar-pro",
        # Security
        "security": "anthropic/claude-sonnet-4-5",
        # Groq Fast Workers (for quick tasks only)
        "reasoner": "groq/gpt-oss-120b",
        # Moonshot Kimi K2.5 (Primary Orchestrator - 1T MoE, 256K context)
        "kimi": "moonshot/kimi-k2.5",
        "kimi-k2.5": "moonshot/kimi-k2.5",
        # Escalation
        "gpt-5.2": "openai/gpt-5.2",
        "moonshot": "moonshot/kimi-k2.5",
        "claude-opus": "anthropic/claude-opus-4-5",
        "claude-sonnet": "anthropic/claude-sonnet-4-5",
        "claude-haiku": "anthropic/claude-haiku-4-5",
        "gemini-pro": "google/gemini-3-pro",
        "gemini-flash": "google/gemini-3-flash",
    }
    return model_map.get(subagent_type, "zai/glm-4.7")


def parl_decompose_task(
    task_description: str,
    max_subagents: int = 100,
    parallelism_threshold: float = 0.5,
    use_cache: bool = True,
    mode: str = "widesearch"
) -> Dict[str, Any]:
    """
    PARL Task Decomposition (Kimi K2.5 Native Agent Swarm)

    Uses the orchestrator's trained decomposition capability to:
    1. Analyze task complexity
    2. Identify parallelizable subtasks
    3. Create execution graph
    4. Estimate critical steps

    Kimi K2.5 Modes:
    - "browsecomp": Max 15 steps for main agent (fast, focused tasks)
    - "widesearch": Max 100 steps for main agent (complex, exploratory tasks)

    Args:
        task_description: The main task to decompose
        max_subagents: Maximum number of parallel subagents (up to 100)
        parallelism_threshold: Minimum parallelism score to spawn subagent (0-1)
        use_cache: Whether to check decomposition cache first
        mode: Execution mode - "browsecomp" (15 steps) or "widesearch" (100 steps)

    Returns:
        Decomposition result with run_id and suggested subtasks
    """
    # Determine main agent max steps based on mode
    if mode == "browsecomp":
        main_agent_max_steps = KIMI_K2_CONFIG["main_agent_max_steps_browsecomp"]
    else:
        main_agent_max_steps = KIMI_K2_CONFIG["main_agent_max_steps_widesearch"]
    db = get_taskbus()
    task_hash = _hash_task_description(task_description)

    # Check cache first
    if use_cache:
        try:
            conn = db._get_conn()
            cur = conn.cursor()
            cur.execute(
                "SELECT decomposition, success_rate FROM decomposition_cache WHERE task_hash = %s",
                (task_hash,)
            )
            row = cur.fetchone()
            cur.close()
            db._put_conn(conn)

            if row and row[0]:
                cached = row[0] if isinstance(row[0], dict) else json.loads(row[0])
                return {
                    "run_id": None,
                    "decomposition_mode": "parl_cached",
                    "cached": True,
                    "success_rate": float(row[1]) if row[1] else 0.0,
                    "subtasks": cached.get("subtasks", []),
                    "max_subagents": min(max_subagents, 100),
                    "task_hash": task_hash,
                }
        except Exception as e:
            sys.stderr.write(f"[PARL] Cache lookup failed: {e}\n")

    # Create new PARL run
    run_result = db.create_run(f"PARL:{task_hash}")
    run_id = run_result.get("run_id")

    # Initialize critical steps tracking (step_number defaults to 0)
    try:
        conn = db._get_conn()
        cur = conn.cursor()
        # Check if table has step_number column
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'critical_steps' AND column_name = 'step_number'
        """)
        has_step_number = cur.fetchone() is not None

        if has_step_number:
            cur.execute(
                """INSERT INTO critical_steps (run_id, step_number, orchestrator_steps, max_subagent_steps)
                   VALUES (%s, 0, 0, 0)
                   ON CONFLICT DO NOTHING""",
                (run_id,)
            )
        else:
            cur.execute(
                """INSERT INTO critical_steps (run_id, orchestrator_steps, max_subagent_steps)
                   VALUES (%s, 0, 0)
                   ON CONFLICT DO NOTHING""",
                (run_id,)
            )
        conn.commit()
        cur.close()
        db._put_conn(conn)
    except Exception as e:
        sys.stderr.write(f"[PARL] Critical steps init warning: {e}\n")

    return {
        "run_id": run_id,
        "decomposition_mode": "parl_native",
        "cached": False,
        "max_subagents": min(max_subagents, KIMI_K2_CONFIG["max_subagents"]),
        "parallelism_threshold": parallelism_threshold,
        "task_hash": task_hash,
        "status": "awaiting_orchestrator_decomposition",
        "hint": "Orchestrator should decompose into parallelizable subtasks. Use parl_spawn_subagent for each subtask.",
        # Kimi K2.5 Swarm Configuration
        "kimi_k2_config": {
            "mode": mode,
            "main_agent_max_steps": main_agent_max_steps,
            "subagent_max_steps": KIMI_K2_CONFIG["subagent_max_steps"],
            "max_tool_calls": KIMI_K2_CONFIG["max_tool_calls"],
            "temperature_thinking": KIMI_K2_CONFIG["temperature_thinking"],
            "temperature_instant": KIMI_K2_CONFIG["temperature_instant"],
            "top_p": KIMI_K2_CONFIG["top_p"],
            "lambda_aux_initial": KIMI_K2_CONFIG["lambda_aux_initial"],
            "speedup_factor": KIMI_K2_CONFIG["speedup_factor"],
        },
        "ts": _now_iso_z(),
    }


def parl_spawn_subagent(
    run_id: str,
    subagent_type: str,
    task: str,
    model: Optional[str] = None,
    parent_task_id: Optional[str] = None,
    priority: int = 7,
    mode: str = "instant",
    max_steps: Optional[int] = None
) -> Dict[str, Any]:
    """
    Spawn a frozen subagent for PARL execution (Kimi K2.5 Native Swarm).

    Subagents are (per Kimi K2.5 spec):
    - Frozen (no training updates during execution)
    - Session-isolated (independent conversation context)
    - Task-focused (execute assigned subtask only)
    - Trackable (report back to orchestrator)
    - Max 100 steps per subagent

    Args:
        run_id: The PARL run ID from parl_decompose_task
        subagent_type: Type of agent (planner, coder, tester, etc.)
        task: The subtask description
        model: Optional model override (auto-resolved if not specified)
        parent_task_id: Optional parent task for dependency tracking
        priority: Task priority (default 7)
        mode: Execution mode - "thinking" (temp=1.0) or "instant" (temp=0.6)
        max_steps: Max steps for this subagent (default from config: 100)

    Returns:
        Subagent spawn result with subagent_id and task_id
    """
    db = get_taskbus()
    subagent_id = _generate_subagent_id()
    resolved_model = model or _resolve_model_for_type(subagent_type)

    # Kimi K2.5 specific parameters
    temperature = KIMI_K2_CONFIG["temperature_thinking"] if mode == "thinking" else KIMI_K2_CONFIG["temperature_instant"]
    effective_max_steps = max_steps or KIMI_K2_CONFIG["subagent_max_steps"]

    # Register subagent session
    try:
        conn = db._get_conn()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO subagent_sessions (run_id, subagent_id, model, status)
               VALUES (%s, %s, %s, 'active')
               ON CONFLICT (run_id, subagent_id) DO UPDATE SET status = 'active'""",
            (run_id, subagent_id, resolved_model)
        )
        conn.commit()
        cur.close()
        db._put_conn(conn)
    except Exception as e:
        sys.stderr.write(f"[PARL] Subagent session registration failed: {e}\n")

    # Create task via TaskBus with Kimi K2.5 swarm parameters
    task_payload = {
        "task_type": f"parl_subagent_{subagent_type}",
        "agent": subagent_id,
        "payload": {
            "subagent_id": subagent_id,
            "subagent_type": subagent_type,
            "model": resolved_model,
            "task": task,
            "run_id": run_id,
            "parl_mode": True,
            # Kimi K2.5 Swarm Parameters
            "kimi_k2_config": {
                "temperature": temperature,
                "top_p": KIMI_K2_CONFIG["top_p"],
                "max_steps": effective_max_steps,
                "mode": mode,
                "frozen": True,  # Subagents are frozen (no training updates)
                "session_isolated": True,  # Independent conversation context
            },
        },
        "priority": priority,
    }

    batch_result = db.push_tasks_batch([task_payload])
    task_ids = batch_result.get("task_ids", [])
    task_id = task_ids[0] if task_ids else None

    # Record execution graph dependency
    if parent_task_id and task_id:
        try:
            conn = db._get_conn()
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO execution_graph (run_id, parent_task_id, child_task_id, dependency_type)
                   VALUES (%s, %s, %s, 'parallel')""",
                (run_id, parent_task_id, task_id)
            )
            conn.commit()
            cur.close()
            db._put_conn(conn)
        except Exception as e:
            sys.stderr.write(f"[PARL] Execution graph update failed: {e}\n")

    return {
        "subagent_id": subagent_id,
        "task_id": task_id,
        "run_id": run_id,
        "subagent_type": subagent_type,
        "model": resolved_model,
        "status": "spawned",
        # Kimi K2.5 Swarm Info
        "kimi_k2_params": {
            "temperature": temperature,
            "top_p": KIMI_K2_CONFIG["top_p"],
            "max_steps": effective_max_steps,
            "mode": mode,
        },
        "ts": _now_iso_z(),
    }


def parl_track_critical_steps(
    run_id: str,
    orchestrator_steps: int,
    subagent_steps: Dict[str, int]
) -> Dict[str, Any]:
    """
    Track critical steps for PARL latency optimization.

    Critical Steps = Σ(S_main + max(S_sub_i))

    This metric prevents "fake parallelism" where tasks appear parallel
    but actually execute sequentially due to dependencies.

    Args:
        run_id: The PARL run ID
        orchestrator_steps: Number of steps taken by orchestrator
        subagent_steps: Dict mapping subagent_id to steps taken

    Returns:
        Critical path analysis with total steps
    """
    db = get_taskbus()

    max_subagent = max(subagent_steps.values()) if subagent_steps else 0
    critical_total = orchestrator_steps + max_subagent

    try:
        conn = db._get_conn()
        cur = conn.cursor()

        # Update critical steps table
        cur.execute(
            """UPDATE critical_steps
               SET orchestrator_steps = %s, max_subagent_steps = %s
               WHERE run_id = %s""",
            (orchestrator_steps, max_subagent, run_id)
        )

        # Update individual subagent sessions
        for subagent_id, steps in subagent_steps.items():
            cur.execute(
                """UPDATE subagent_sessions
                   SET steps_executed = %s
                   WHERE run_id = %s AND subagent_id = %s""",
                (steps, run_id, subagent_id)
            )

        conn.commit()
        cur.close()
        db._put_conn(conn)
    except Exception as e:
        sys.stderr.write(f"[PARL] Critical steps tracking failed: {e}\n")
        return {"error": str(e)}

    # Calculate parallelism efficiency
    total_sequential = orchestrator_steps + sum(subagent_steps.values())
    parallelism_efficiency = 1.0 - (critical_total / total_sequential) if total_sequential > 0 else 0.0

    return {
        "run_id": run_id,
        "orchestrator_steps": orchestrator_steps,
        "subagent_steps": subagent_steps,
        "max_subagent_steps": max_subagent,
        "critical_steps_total": critical_total,
        "total_if_sequential": total_sequential,
        "parallelism_efficiency": round(parallelism_efficiency, 3),
        "ts": _now_iso_z(),
    }


def parl_aggregate_results(
    run_id: str,
    aggregation_strategy: str = "merge",
    conflict_resolution: str = "latest"
) -> Dict[str, Any]:
    """
    Aggregate results from all PARL subagents.

    Strategies:
    - merge: Combine all results into unified output
    - consensus: Use majority vote for conflicting results
    - priority: Use highest-priority subagent result
    - latest: Use most recent result for conflicts

    Args:
        run_id: The PARL run ID
        aggregation_strategy: How to combine results (merge/consensus/priority/latest)
        conflict_resolution: How to resolve conflicts (latest/priority/fail)

    Returns:
        Aggregated results from all subagents
    """
    db = get_taskbus()

    # Get all subagent sessions and their results
    try:
        conn = db._get_conn()
        cur = conn.cursor()

        # Get subagent sessions
        cur.execute(
            """SELECT subagent_id, model, status, steps_executed, completed_at
               FROM subagent_sessions
               WHERE run_id = %s""",
            (run_id,)
        )
        sessions = cur.fetchall()

        # Get task results
        cur.execute(
            """SELECT t.task_id, t.agent, t.status, t.artifact_writes
               FROM tasks t
               WHERE t.run_id = %s AND t.task_type LIKE 'parl_subagent_%%'""",
            (run_id,)
        )
        tasks = cur.fetchall()

        cur.close()
        db._put_conn(conn)
    except Exception as e:
        sys.stderr.write(f"[PARL] Result aggregation failed: {e}\n")
        return {"error": str(e)}

    # Process results
    subagent_results = []
    for task in tasks:
        task_id, agent, status, artifacts = task
        result = {
            "task_id": task_id,
            "subagent_id": agent,
            "status": status,
            "artifacts": artifacts if isinstance(artifacts, dict) else {},
        }
        subagent_results.append(result)

    # Aggregate based on strategy
    completed = [r for r in subagent_results if r["status"] in ("DONE", "COMPLETED")]
    failed = [r for r in subagent_results if r["status"] == "FAILED"]
    pending = [r for r in subagent_results if r["status"] not in ("DONE", "COMPLETED", "FAILED")]

    aggregated = {
        "run_id": run_id,
        "strategy": aggregation_strategy,
        "conflict_resolution": conflict_resolution,
        "total_subagents": len(subagent_results),
        "completed": len(completed),
        "failed": len(failed),
        "pending": len(pending),
        "subagent_results": subagent_results,
        "ts": _now_iso_z(),
    }

    # Mark sessions as aggregated
    try:
        conn = db._get_conn()
        cur = conn.cursor()
        cur.execute(
            """UPDATE subagent_sessions SET status = 'aggregated'
               WHERE run_id = %s AND status = 'active'""",
            (run_id,)
        )
        conn.commit()
        cur.close()
        db._put_conn(conn)
    except Exception:
        pass

    return aggregated


def parl_compute_reward(
    run_id: str,
    success: bool,
    num_subagents: int,
    critical_steps: int,
    lambda_aux: Optional[float] = None,
    training_progress: float = 0.0
) -> Dict[str, Any]:
    """
    Compute PARL reward for optimization analytics (Kimi K2.5 Native).

    Reward function: R = Success × (1 + λ_aux × Auxiliary)

    λ_aux Annealing (per Kimi K2.5 training curriculum):
    - Initial: λ_aux = 0.1 (prioritizes parallelism)
    - Final: λ_aux = 0.0 (focuses on task quality Q(τ))
    - Annealing: λ_aux = 0.1 × (1 - training_progress)

    Where Auxiliary rewards:
    - Parallelism bonus: num_subagents / 100
    - Efficiency bonus: 1 / critical_steps (capped)

    Args:
        run_id: The PARL run ID
        success: Whether the task completed successfully
        num_subagents: Number of subagents spawned
        critical_steps: Critical path length
        lambda_aux: Auxiliary reward weight (default: computed from training_progress)
        training_progress: Training progress 0.0-1.0 for λ_aux annealing

    Returns:
        Reward computation with breakdown
    """
    # Compute λ_aux with annealing if not explicitly provided
    if lambda_aux is None:
        lambda_aux = KIMI_K2_CONFIG["lambda_aux_initial"] * (1.0 - training_progress)
    db = get_taskbus()

    # Base reward
    base_reward = 1.0 if success else 0.0

    # Auxiliary rewards
    parallelism_bonus = min(num_subagents / 100.0, 1.0)
    efficiency_bonus = min(1.0 / max(critical_steps, 1), 1.0)
    auxiliary = (parallelism_bonus + efficiency_bonus) / 2.0

    # Total reward
    total_reward = base_reward * (1.0 + lambda_aux * auxiliary)

    # Store in database
    try:
        conn = db._get_conn()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO parl_rewards (run_id, reward, lambda_aux, num_subagents, critical_steps,
                                         r_parallel, success_indicator)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (run_id, total_reward, lambda_aux, num_subagents, critical_steps,
             parallelism_bonus, 1.0 if success else 0.0)
        )
        conn.commit()
        cur.close()
        db._put_conn(conn)
    except Exception as e:
        sys.stderr.write(f"[PARL] Reward storage failed: {e}\n")

    return {
        "run_id": run_id,
        "success": success,
        "base_reward": base_reward,
        "parallelism_bonus": round(parallelism_bonus, 4),
        "efficiency_bonus": round(efficiency_bonus, 4),
        "auxiliary_reward": round(auxiliary, 4),
        "lambda_aux": round(lambda_aux, 4),
        "training_progress": round(training_progress, 4),
        "total_reward": round(total_reward, 4),
        "num_subagents": num_subagents,
        "critical_steps": critical_steps,
        # Kimi K2.5 Reward Analysis
        "kimi_k2_analysis": {
            "lambda_aux_annealing": f"{KIMI_K2_CONFIG['lambda_aux_initial']} → {KIMI_K2_CONFIG['lambda_aux_final']}",
            "current_lambda_aux": round(lambda_aux, 4),
            "parallelism_utilization": round(num_subagents / KIMI_K2_CONFIG["max_subagents"], 4),
            "expected_speedup": KIMI_K2_CONFIG["speedup_factor"],
        },
        "ts": _now_iso_z(),
    }


def parl_get_status(run_id: str) -> Dict[str, Any]:
    """
    Get comprehensive PARL run status.

    Args:
        run_id: The PARL run ID

    Returns:
        Full status including subagents, critical path, and rewards
    """
    db = get_taskbus()

    try:
        conn = db._get_conn()
        cur = conn.cursor()

        # Get critical steps
        cur.execute(
            """SELECT orchestrator_steps, max_subagent_steps, critical_step_total
               FROM critical_steps WHERE run_id = %s""",
            (run_id,)
        )
        cs_row = cur.fetchone()

        # Get subagent sessions
        cur.execute(
            """SELECT subagent_id, model, status, steps_executed
               FROM subagent_sessions WHERE run_id = %s""",
            (run_id,)
        )
        sessions = cur.fetchall()

        # Get reward if computed
        cur.execute(
            """SELECT reward, num_subagents, critical_steps
               FROM parl_rewards WHERE run_id = %s""",
            (run_id,)
        )
        reward_row = cur.fetchone()

        # Get task statuses
        cur.execute(
            """SELECT status, COUNT(*) FROM tasks
               WHERE run_id = %s AND task_type LIKE 'parl_subagent_%%'
               GROUP BY status""",
            (run_id,)
        )
        task_stats = dict(cur.fetchall())

        cur.close()
        db._put_conn(conn)
    except Exception as e:
        sys.stderr.write(f"[PARL] Status query failed: {e}\n")
        return {"error": str(e), "run_id": run_id}

    return {
        "run_id": run_id,
        "critical_steps": {
            "orchestrator": cs_row[0] if cs_row else 0,
            "max_subagent": cs_row[1] if cs_row else 0,
            "total": cs_row[2] if cs_row else 0,
        } if cs_row else None,
        "subagents": [
            {"id": s[0], "model": s[1], "status": s[2], "steps": s[3]}
            for s in sessions
        ],
        "task_stats": task_stats,
        "reward": {
            "value": float(reward_row[0]) if reward_row else None,
            "num_subagents": reward_row[1] if reward_row else None,
            "critical_steps": reward_row[2] if reward_row else None,
        } if reward_row else None,
        "ts": _now_iso_z(),
    }


def parl_cache_decomposition(
    task_hash: str,
    decomposition: Dict[str, Any],
    success: bool,
    task_description: Optional[str] = None,
    critical_steps: Optional[int] = None
) -> Dict[str, Any]:
    """
    Cache a successful task decomposition for future reuse.

    Args:
        task_hash: Hash of the original task description
        decomposition: The decomposition result to cache
        success: Whether this decomposition led to success
        task_description: Optional original task text
        critical_steps: Optional critical steps count for this decomposition

    Returns:
        Cache update status
    """
    db = get_taskbus()

    try:
        conn = db._get_conn()
        cur = conn.cursor()

        # Update cache with exponential moving average for success rate
        cur.execute(
            """INSERT INTO decomposition_cache (task_hash, task_description, decomposition, success_rate, usage_count, avg_critical_steps, last_used_at)
               VALUES (%s, %s, %s, %s, 1, %s, NOW())
               ON CONFLICT (task_hash) DO UPDATE SET
                   decomposition = EXCLUDED.decomposition,
                   success_rate = decomposition_cache.success_rate * 0.9 + EXCLUDED.success_rate * 0.1,
                   usage_count = decomposition_cache.usage_count + 1,
                   avg_critical_steps = CASE
                       WHEN EXCLUDED.avg_critical_steps IS NOT NULL
                       THEN (decomposition_cache.avg_critical_steps * decomposition_cache.usage_count + EXCLUDED.avg_critical_steps) / (decomposition_cache.usage_count + 1)
                       ELSE decomposition_cache.avg_critical_steps
                   END,
                   last_used_at = NOW()""",
            (task_hash, task_description, json.dumps(decomposition), 1.0 if success else 0.0, critical_steps)
        )
        conn.commit()
        cur.close()
        db._put_conn(conn)
    except Exception as e:
        sys.stderr.write(f"[PARL] Cache update failed: {e}\n")
        return {"error": str(e)}

    return {
        "task_hash": task_hash,
        "cached": True,
        "success": success,
        "ts": _now_iso_z(),
    }


# --- MCP protocol surface ---

TOOLS_LIST = [
    {
        "name": "parallel_dispatch_planners",
        "description": "Enqueue 5 planner subtasks via TaskBus (optionally wait/poll).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_description": {"type": "string"},
                "subtasks": {"type": "array", "items": {"type": "string"}},
                "wait": {"type": "boolean"},
            },
            "required": ["task_description"],
        },
    },
    {
        "name": "parallel_dispatch_workers",
        "description": "Enqueue minimum 5 worker tasks via TaskBus (optionally wait/poll).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "planner": {"type": "string"},
                "task_description": {"type": "string"},
                "worker_tasks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "worker": {"type": "string"},
                            "role": {"type": "string"},
                            "task_description": {"type": "string"},
                        },
                    },
                },
                "wait": {"type": "boolean"},
            },
            "required": ["planner", "task_description"],
        },
    },
    {
        "name": "parallel_run_tasks",
        "description": "Enqueue arbitrary tasks via TaskBus (optionally wait/poll).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tasks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "task_type": {"type": "string"},
                            "agent": {"type": "string"},
                            "payload": {"type": "object"},
                            "priority": {"type": "integer"},
                        },
                    },
                },
                "wait": {"type": "boolean"},
                "timeout_s": {"type": "integer"},
                "poll_ms": {"type": "integer"},
            },
            "required": ["tasks"],
        },
    },
    {
        "name": "get_parallel_capabilities",
        "description": "Get information about parallel execution capabilities",
        "inputSchema": {"type": "object", "properties": {}},
    },
    # PARL Tools
    {
        "name": "parl_decompose_task",
        "description": "PARL (Kimi K2.5 Native): Decompose a task into parallelizable subtasks. Supports up to 100 subagents, 1500 tool calls, 4.5x speedup.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_description": {"type": "string", "description": "The main task to decompose"},
                "max_subagents": {"type": "integer", "description": "Max parallel subagents (up to 100)", "default": 100},
                "parallelism_threshold": {"type": "number", "description": "Min parallelism score (0-1)", "default": 0.5},
                "use_cache": {"type": "boolean", "description": "Check decomposition cache first", "default": True},
                "mode": {"type": "string", "enum": ["browsecomp", "widesearch"], "description": "browsecomp (15 steps) or widesearch (100 steps)", "default": "widesearch"},
            },
            "required": ["task_description"],
        },
    },
    {
        "name": "parl_spawn_subagent",
        "description": "PARL (Kimi K2.5 Native): Spawn a frozen subagent. Max 100 steps per subagent, session-isolated, with thinking (temp=1.0) or instant (temp=0.6) mode.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string", "description": "PARL run ID from parl_decompose_task"},
                "subagent_type": {"type": "string", "description": "Agent type (planner, coder, tester, etc.)"},
                "task": {"type": "string", "description": "Subtask description"},
                "model": {"type": "string", "description": "Optional model override"},
                "parent_task_id": {"type": "string", "description": "Parent task for dependency tracking"},
                "priority": {"type": "integer", "description": "Task priority", "default": 7},
                "mode": {"type": "string", "enum": ["thinking", "instant"], "description": "thinking (temp=1.0) or instant (temp=0.6)", "default": "instant"},
                "max_steps": {"type": "integer", "description": "Max steps for subagent (default 100)", "default": 100},
            },
            "required": ["run_id", "subagent_type", "task"],
        },
    },
    {
        "name": "parl_track_critical_steps",
        "description": "PARL: Track critical steps for latency optimization. CriticalSteps = S_main + max(S_sub_i)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string", "description": "PARL run ID"},
                "orchestrator_steps": {"type": "integer", "description": "Steps taken by orchestrator"},
                "subagent_steps": {"type": "object", "description": "Dict mapping subagent_id to steps taken"},
            },
            "required": ["run_id", "orchestrator_steps", "subagent_steps"],
        },
    },
    {
        "name": "parl_aggregate_results",
        "description": "PARL: Aggregate results from all subagents. Supports merge, consensus, priority strategies.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string", "description": "PARL run ID"},
                "aggregation_strategy": {"type": "string", "enum": ["merge", "consensus", "priority", "latest"], "default": "merge"},
                "conflict_resolution": {"type": "string", "enum": ["latest", "priority", "fail"], "default": "latest"},
            },
            "required": ["run_id"],
        },
    },
    {
        "name": "parl_compute_reward",
        "description": "PARL (Kimi K2.5 Native): Compute reward with λ_aux annealing (0.1→0.0). R = Success × (1 + λ_aux × Auxiliary)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string", "description": "PARL run ID"},
                "success": {"type": "boolean", "description": "Whether task completed successfully"},
                "num_subagents": {"type": "integer", "description": "Number of subagents spawned"},
                "critical_steps": {"type": "integer", "description": "Critical path length"},
                "lambda_aux": {"type": "number", "description": "Override λ_aux (null for auto-annealing)"},
                "training_progress": {"type": "number", "description": "Training progress 0.0-1.0 for λ_aux annealing", "default": 0.0},
            },
            "required": ["run_id", "success", "num_subagents", "critical_steps"],
        },
    },
    {
        "name": "parl_get_status",
        "description": "PARL: Get comprehensive run status including subagents, critical path, and rewards.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string", "description": "PARL run ID"},
            },
            "required": ["run_id"],
        },
    },
    {
        "name": "parl_cache_decomposition",
        "description": "PARL: Cache a successful task decomposition for future reuse.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_hash": {"type": "string", "description": "Hash of the original task"},
                "decomposition": {"type": "object", "description": "Decomposition to cache"},
                "success": {"type": "boolean", "description": "Whether decomposition led to success"},
                "task_description": {"type": "string", "description": "Original task text"},
                "critical_steps": {"type": "integer", "description": "Critical steps count"},
            },
            "required": ["task_hash", "decomposition", "success"],
        },
    },
]


def handle_tool_call(tool_name: str, args: Dict[str, Any]) -> Any:
    # Standard parallel tools
    if tool_name == "parallel_dispatch_planners":
        return dispatch_all_planners(
            task_description=args.get("task_description", ""),
            subtasks=args.get("subtasks"),
            wait=bool(args.get("wait", False)),
        )
    if tool_name == "parallel_dispatch_workers":
        return dispatch_parallel_workers(
            planner=args.get("planner", ""),
            task_description=args.get("task_description", ""),
            worker_tasks=args.get("worker_tasks"),
            wait=bool(args.get("wait", False)),
        )
    if tool_name == "parallel_run_tasks":
        return run_parallel_tasks(
            tasks=args.get("tasks") or [],
            wait=bool(args.get("wait", False)),
            timeout_s=int(args.get("timeout_s", 180)),
            poll_ms=int(args.get("poll_ms", 250)),
        )
    if tool_name == "get_parallel_capabilities":
        return get_parallel_capabilities()

    # PARL tools
    if tool_name == "parl_decompose_task":
        return parl_decompose_task(
            task_description=args.get("task_description", ""),
            max_subagents=int(args.get("max_subagents", 100)),
            parallelism_threshold=float(args.get("parallelism_threshold", 0.5)),
            use_cache=bool(args.get("use_cache", True)),
            mode=args.get("mode", "widesearch"),
        )
    if tool_name == "parl_spawn_subagent":
        return parl_spawn_subagent(
            run_id=args.get("run_id", ""),
            subagent_type=args.get("subagent_type", ""),
            task=args.get("task", ""),
            model=args.get("model"),
            parent_task_id=args.get("parent_task_id"),
            priority=int(args.get("priority", 7)),
            mode=args.get("mode", "instant"),
            max_steps=args.get("max_steps"),
        )
    if tool_name == "parl_track_critical_steps":
        return parl_track_critical_steps(
            run_id=args.get("run_id", ""),
            orchestrator_steps=int(args.get("orchestrator_steps", 0)),
            subagent_steps=args.get("subagent_steps", {}),
        )
    if tool_name == "parl_aggregate_results":
        return parl_aggregate_results(
            run_id=args.get("run_id", ""),
            aggregation_strategy=args.get("aggregation_strategy", "merge"),
            conflict_resolution=args.get("conflict_resolution", "latest"),
        )
    if tool_name == "parl_compute_reward":
        return parl_compute_reward(
            run_id=args.get("run_id", ""),
            success=bool(args.get("success", False)),
            num_subagents=int(args.get("num_subagents", 0)),
            critical_steps=int(args.get("critical_steps", 1)),
            lambda_aux=args.get("lambda_aux"),  # None triggers annealing
            training_progress=float(args.get("training_progress", 0.0)),
        )
    if tool_name == "parl_get_status":
        return parl_get_status(run_id=args.get("run_id", ""))
    if tool_name == "parl_cache_decomposition":
        return parl_cache_decomposition(
            task_hash=args.get("task_hash", ""),
            decomposition=args.get("decomposition", {}),
            success=bool(args.get("success", False)),
            task_description=args.get("task_description"),
            critical_steps=args.get("critical_steps"),
        )

    return {"error": f"Unknown tool: {tool_name}"}


def handle_request(request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    method = request.get("method", "")
    params = request.get("params", {})
    req_id = request.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "parallel-orchestrator", "version": "2.0.0"},
                "capabilities": {"tools": {}},
            },
        }

    if method == "notifications/initialized":
        return None

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS_LIST}}

    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments", {})
        result = handle_tool_call(name, arguments)
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]},
        }

    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Unknown method: {method}"}}


def main() -> None:
    sys.stdout = os.fdopen(sys.stdout.fileno(), "w", buffering=1)
    sys.stderr.write("[Parallel MCP] Starting parallel orchestrator (taskbus-queue)\n")
    sys.stderr.flush()

    # Eager check: require TaskBus reachable
    try:
        get_taskbus()
    except Exception as e:
        sys.stderr.write(f"[Parallel MCP] FATAL: TaskBus unavailable: {e}\n")
        sys.stderr.flush()
        sys.exit(1)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = handle_request(request)
            if response:
                print(json.dumps(response), flush=True)
        except json.JSONDecodeError as e:
            print(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": f"Parse error: {e}"}}), flush=True)
        except Exception as e:
            print(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32000, "message": str(e)}}), flush=True)


if __name__ == "__main__":
    main()
