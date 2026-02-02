#!/usr/bin/env python3
"""
progress_watchdog.py - keep TaskBus progress alive

Behavior:
- Logs live status every N minutes (default 10)
- If idle (no RUNNING/QUEUED tasks), dispatches planner tasks
- Never exits unless interrupted

This is intentionally lightweight and project-scoped (runs from project root).
"""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _safe_read_json(path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return dict(default)


def _safe_write_json(path: Path, data: Dict[str, Any]) -> None:
    try:
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


def _ensure_dirs(project_root: Path) -> Path:
    ai_dir = project_root / ".ai"
    logs_dir = ai_dir / "logs"
    ai_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def _build_planner_tasks(task_description: str) -> List[Dict[str, Any]]:
    planners = [
        {"name": "planner-1", "provider": "Google", "model": "gemini-3-pro"},
        {"name": "planner-2", "provider": "Anthropic", "model": "claude-sonnet"},
        {"name": "planner-3", "provider": "OpenAI", "model": "gpt-5.2"},
        {"name": "planner-4", "provider": "DeepSeek", "model": "deepseek-reasoner"},
        {"name": "planner-5", "provider": "Z.AI", "model": "glm-4.7"},
    ]
    subtasks = [
        f"[planner-1] Architecture + research: {task_description}",
        f"[planner-2] Security + validation: {task_description}",
        f"[planner-3] Workflow + coordination: {task_description}",
        f"[planner-4] Logic + algorithms: {task_description}",
        f"[planner-5] Implementation + testing: {task_description}",
    ]

    tasks: List[Dict[str, Any]] = []
    for i, p in enumerate(planners):
        tasks.append(
            {
                "task_type": f"planner_subtask_{p['name']}",
                "agent": p["name"],
                "payload": {
                    "subtask": subtasks[i],
                    "provider": p["provider"],
                    "model": p["model"],
                    "task_description": task_description,
                },
                "priority": 9,
            }
        )
    return tasks


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", type=str, default=None)
    ap.add_argument("--interval-min", type=int, default=10)
    ap.add_argument("--task", type=str, default=None)
    args = ap.parse_args()

    if args.project_root:
        os.chdir(args.project_root)

    project_root = Path(os.getcwd())
    logs_dir = _ensure_dirs(project_root)
    log_path = logs_dir / "progress_watchdog.log"
    state_path = project_root / ".ai" / "auto_continue.json"

    sys_path = Path(__file__).parent
    if str(sys_path) not in os.sys.path:
        os.sys.path.insert(0, str(sys_path))
    from postgres_mcp import TaskBusDB  # noqa: E402

    interval_s = max(1, args.interval_min) * 60
    default_task = "Research and develop this project 10x deeper; validate and test."
    task_description = args.task or os.environ.get("OPENCODE_AUTO_TASK", default_task)

    state = _safe_read_json(state_path, {"last_dispatch_ts": 0, "dispatch_count": 0})

    while True:
        try:
            db = TaskBusDB()
            status = db.get_live_status()
            now = time.time()
            idle = False

            if status.get("error"):
                idle = True
            else:
                running = int(status.get("running_count", 0))
                queued = int(status.get("queued_count", 0))
                idle = running == 0 and queued == 0

            # Log status
            with log_path.open("a", encoding="utf-8") as f:
                f.write(
                    json.dumps(
                        {
                            "ts": _utc_now(),
                            "idle": idle,
                            "status": status,
                        }
                    )
                    + "\n"
                )

            # Auto-dispatch if idle and interval elapsed
            last_dispatch = float(state.get("last_dispatch_ts", 0))
            if idle and (now - last_dispatch) >= interval_s:
                # Acquire a short-lived lock so multiple watchdog instances don't double-dispatch.
                holder = f"watchdog-{os.getpid()}"
                lock_key = f"auto_dispatch:{db.project_id}"
                lock = db.acquire_lock(lock_key=lock_key, holder=holder, ttl_seconds=int(max(30, interval_s)))
                if not lock.get("acquired"):
                    with log_path.open("a", encoding="utf-8") as f:
                        f.write(json.dumps({"ts": _utc_now(), "event": "AUTO_DISPATCH_SKIPPED_LOCKED", "held_by": lock.get("held_by")}) + "\n")
                else:
                    tasks = _build_planner_tasks(task_description)
                    result = db.push_tasks_batch(tasks)
                    state["last_dispatch_ts"] = now
                    state["dispatch_count"] = int(state.get("dispatch_count", 0)) + 1
                    _safe_write_json(state_path, state)

                    with log_path.open("a", encoding="utf-8") as f:
                        f.write(
                            json.dumps(
                                {
                                    "ts": _utc_now(),
                                    "event": "AUTO_DISPATCH",
                                    "run_id": result.get("run_id"),
                                    "task_ids": result.get("task_ids"),
                                    "task_description": task_description,
                                }
                            )
                            + "\n"
                        )

                    # Best-effort release (TTL also protects us)
                    try:
                        db.release_lock(lock_key=lock_key, holder=holder)
                    except Exception:
                        pass

        except Exception as e:
            with log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"ts": _utc_now(), "error": str(e)}) + "\n")

        time.sleep(interval_s)


if __name__ == "__main__":
    raise SystemExit(main())
