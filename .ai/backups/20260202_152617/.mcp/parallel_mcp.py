#!/usr/bin/env python3
"""parallel_mcp.py

Parallel Orchestrator MCP Server

IMPORTANT
This server is responsible for *true parallel orchestration surface area*.
In OpenCode, the LLM agents are executed by the OpenCode runtime; this MCP server
must be reliable and must integrate with the PostgreSQL TaskBus.

This implementation focuses on correctness + reliability:
- Requires TaskBus (Postgres). No silent fallback.
- Uses TaskBus to create runs and enqueue tasks (push_tasks_batch).
- Optionally waits/polls task completion via get_parallel_status.

It does NOT simulate "DONE" work. If you want local execution, build an external
worker that claims tasks from TaskBus and completes them.

Tools
- parallel_dispatch_planners
- parallel_dispatch_workers
- parallel_run_tasks
- get_parallel_capabilities
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


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
    planners = [
        {"name": "planner-1", "provider": "Google", "model": "gemini-3-pro"},
        {"name": "planner-2", "provider": "Anthropic", "model": "claude-sonnet"},
        {"name": "planner-3", "provider": "OpenAI", "model": "gpt-5.2"},
        {"name": "planner-4", "provider": "DeepSeek", "model": "deepseek-reasoner"},
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
    return {
        "parallel_execution": True,
        "mode": "taskbus-queue",
        "note": "This MCP enqueues tasks in Postgres TaskBus. Use external workers to execute/complete tasks.",
        "min_planners": 5,
        "min_workers_per_planner": 5,
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
]


def handle_tool_call(tool_name: str, args: Dict[str, Any]) -> Any:
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
