#!/usr/bin/env python3
"""taskbus_worker.py - TaskBus Worker Runtime (Postgres)

Goals
- Claim tasks from Postgres TaskBus and mark them DONE/FAILED.
- Be gate-aware via TaskBus enforcement (workers/coders are blocked in Gate A/B/D).
- Avoid API mismatches: use TaskBusDB.complete_task(task_id, status, artifact_writes, error).

Important design note
- In TaskBus schema, `tasks.agent` is used as the *claimer/holder* field.
  When a worker claims a task, agent is overwritten with the holder id.
  Therefore, the intended executor must be derived from task_type/role/payload.

Safe defaults
- By default, this worker runs in NO-OP mode and only claims planner tasks.
  This unblocks `parallel_dispatch_planners(wait=true)` without executing LLM agents.
- Enable real execution with: --run-opencode

OpenCode CLI
- `opencode --help` indicates the non-interactive command is: `opencode run ...`
- There is no global `--task-id` flag; we embed task_id in the message.

Usage
  python taskbus_worker.py --workers 5
  python taskbus_worker.py --workers 5 --run-opencode
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

TaskBusDB = None


def _get_taskbus_db():
    """Lazy import so project root can be set before TaskBusDB initializes."""
    global TaskBusDB
    if TaskBusDB is None:
        sys.path.insert(0, str(Path(__file__).parent))
        from postgres_mcp import TaskBusDB as _TaskBusDB  # noqa: E402

        TaskBusDB = _TaskBusDB
    return TaskBusDB()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _safe_json_loads(v: Any, default: Any) -> Any:
    if v is None:
        return default
    if isinstance(v, (dict, list)):
        return v
    try:
        return json.loads(v)
    except Exception:
        return default


def _extract_payload(task: Dict[str, Any]) -> Dict[str, Any]:
    # In this TaskBus implementation, tasks.deps may hold a dict payload.
    deps = task.get("deps")
    parsed = _safe_json_loads(deps, {})
    return parsed if isinstance(parsed, dict) else {}


def _infer_executor(task: Dict[str, Any]) -> str:
    """Infer the intended executor agent for a task.

    Priority:
    - task_type prefixes used by parallel_mcp.py:
      - planner_subtask_planner-1 -> planner-1
      - worker_coder -> coder
    - agent field if it doesn't look like a holder (worker-*)
    - role fallback
    """
    task_type = (task.get("task_type") or "").strip()
    if task_type.startswith("planner_subtask_"):
        return task_type[len("planner_subtask_") :]
    if task_type.startswith("worker_"):
        return task_type[len("worker_") :]

    agent = (task.get("agent") or "").strip()
    if agent and not agent.lower().startswith("worker-"):
        return agent

    role = (task.get("role") or "").strip()
    return role or "coder"


def _is_planner_task(task: Dict[str, Any]) -> bool:
    return (task.get("task_type") or "").startswith("planner_subtask_")


class TaskBusWorker:
    def __init__(
        self, worker_id: str, poll_ms: int, run_opencode: bool, opencode_timeout_s: int
    ):
        self.worker_id = worker_id
        self.poll_ms = poll_ms
        self.run_opencode = run_opencode
        self.opencode_timeout_s = opencode_timeout_s
        self.db = _get_taskbus_db()
        self.running = False
        self.stats = {
            "claimed": 0,
            "completed": 0,
            "failed": 0,
            "started_at": _utc_now_iso(),
        }

    def _log(self, msg: str, level: str = "INFO") -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] [{self.worker_id}] {level}: {msg}", flush=True)

    def _claim_next_task_atomic(self) -> Optional[Dict[str, Any]]:
        """Atomically claim next task.

        In NO-OP mode we only claim planner tasks using a SQL pattern filter.
        We do not rely on TaskBusDB.claim_next_task() because it cannot pattern-match task_type.
        """
        conn = self.db._get_conn()
        try:
            conn.autocommit = False
            cur = conn.cursor()

            where_extra = ""
            params: List[Any] = [self.db.project_id]

            if not self.run_opencode:
                where_extra = " AND task_type LIKE 'planner_subtask_%%'"

            cur.execute(
                f"""
                SELECT task_id, run_id, gate, task_type, role, agent, status, priority, complexity, deps, artifact_writes, timeout_ms, attempts, max_attempts, last_error, created_at, updated_at
                FROM tasks
                WHERE project_id = %s
                  AND status IN ('QUEUED','RETRY','PENDING')
                  {where_extra}
                ORDER BY priority DESC, created_at ASC
                LIMIT 1
                FOR UPDATE SKIP LOCKED
                """,
                tuple(params),
            )
            row = cur.fetchone()
            if not row:
                conn.rollback()
                cur.close()
                return None

            cols = [
                "task_id",
                "run_id",
                "gate",
                "task_type",
                "role",
                "agent",
                "status",
                "priority",
                "complexity",
                "deps",
                "artifact_writes",
                "timeout_ms",
                "attempts",
                "max_attempts",
                "last_error",
                "created_at",
                "updated_at",
            ]
            task = {}
            for i, col in enumerate(cols):
                if i < len(row):
                    task[col] = row[i]

            # Claim: set RUNNING and record holder in agent (matches TaskBus schema).
            now = self.db._now()
            cur.execute(
                """
                UPDATE tasks
                SET status='RUNNING', agent=%s, attempts=attempts+1, updated_at=%s
                WHERE task_id=%s
                """,
                (self.worker_id, now, task["task_id"]),
            )
            conn.commit()
            cur.close()

            task["status"] = "RUNNING"
            task["agent"] = self.worker_id
            try:
                task["attempts"] = int(task.get("attempts") or 0) + 1
            except Exception:
                pass
            task["updated_at"] = now

            self.stats["claimed"] += 1
            return task

        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            raise
        finally:
            try:
                self.db._put_conn(conn)
            except Exception:
                pass

    def _store_artifact(
        self, run_id: str, content: str, meta: Dict[str, Any]
    ) -> Optional[str]:
        try:
            art = self.db.store_artifact(
                run_id=run_id,
                artifact_type="agent_results",
                content=content,
                metadata=meta,
            )
            if isinstance(art, dict):
                return art.get("path")
        except Exception as e:
            self._log(f"store_artifact failed: {e}", "WARN")
        return None

    def _execute(self, task: Dict[str, Any]) -> Tuple[str, Optional[str], List[str]]:
        task_id = task["task_id"]
        run_id = task.get("run_id")
        if not run_id:
            return "FAILED", "Missing run_id", []

        executor = _infer_executor(task)
        payload = _extract_payload(task)
        desc = (
            payload.get("subtask")
            or payload.get("task_description")
            or f"{task.get('task_type')}"
        )

        # Fast-complete mode: mark tasks DONE without LLM execution (for development/testing)
        # Enable with OPENCODE_WORKER_FAST_COMPLETE=1
        fast_complete = os.environ.get(
            "OPENCODE_WORKER_FAST_COMPLETE", "0"
        ).strip().lower() in ("1", "true", "yes", "on")

        if not self.run_opencode or fast_complete:
            mode = "fast-complete" if fast_complete else "noop"
            msg = f"{mode.upper()} complete: {executor} :: {desc}"
            path = self._store_artifact(
                run_id,
                msg + "\n",
                {
                    "task_id": task_id,
                    "executor": executor,
                    "worker_id": self.worker_id,
                    "mode": mode,
                    "ts": _utc_now_iso(),
                },
            )
            return "DONE", None, [p for p in [path] if p]

        # Real execution mode
        # Resolve opencode command from PATH or npm shim.
        def _resolve_opencode_cmd() -> List[str]:
            import shutil

            p = shutil.which("opencode")
            if p:
                return [p]
            p = shutil.which("ocode")
            if p:
                return [p]

            appdata = os.environ.get("APPDATA")
            if appdata and os.name == "nt":
                shim = Path(appdata) / "npm" / "opencode.cmd"
                if shim.exists():
                    return ["cmd", "/c", str(shim)]
            return ["opencode"]

        oc_cmd = _resolve_opencode_cmd()
        cmd = [
            *oc_cmd,
            "run",
            "--agent",
            executor,
            f"[task_id={task_id}] {desc}",
        ]

        timeout_s = self.opencode_timeout_s
        try:
            task_timeout_ms = int(task.get("timeout_ms") or 0)
            if task_timeout_ms > 0:
                timeout_s = max(1, int(task_timeout_ms / 1000))
        except Exception:
            pass

        try:
            # Force UTF-8 encoding and replace errors to avoid UnicodeDecodeError on Windows
            # Also set environment variable to force UTF-8 for the subprocess
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            # Ensure we don't inherit weird locale settings
            env["LANG"] = "en_US.UTF-8"

            # Ensure bash on Windows for OpenCode's internal command execution.
            if os.name == "nt" and not (
                env.get("SHELL") and Path(env.get("SHELL")).exists()
            ):
                for c in [
                    r"C:\Program Files\Git\bin\bash.exe",
                    r"C:\Program Files\Git\usr\bin\bash.exe",
                    r"C:\Program Files (x86)\Git\bin\bash.exe",
                    r"C:\msys64\usr\bin\bash.exe",
                ]:
                    if Path(c).exists():
                        env["SHELL"] = c
                        env.setdefault("MSYSTEM", "MINGW64")
                        break

            # Explicitly specify encoding and error handling for all stdio
            # On Windows, prevent console windows from flashing for each subprocess.
            creationflags = 0
            startupinfo = None
            if os.name == "nt":
                try:
                    creationflags = subprocess.CREATE_NO_WINDOW
                    si = subprocess.STARTUPINFO()
                    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    si.wShowWindow = 0  # SW_HIDE
                    startupinfo = si
                except Exception:
                    creationflags = 0
                    startupinfo = None

            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_s,
                cwd=os.environ.get("OPENCODE_PROJECT_ROOT", os.getcwd()),
                encoding="utf-8",
                errors="replace",
                env=env,
                stdin=subprocess.DEVNULL,
                creationflags=creationflags,
                startupinfo=startupinfo,
            )
            stdout = proc.stdout or ""
            stderr = proc.stderr or ""

            meta = {
                "task_id": task_id,
                "executor": executor,
                "worker_id": self.worker_id,
                "mode": "opencode",
                "exit_code": proc.returncode,
                "ts": _utc_now_iso(),
            }
            p_out = self._store_artifact(run_id, stdout, {**meta, "stream": "stdout"})
            p_err = self._store_artifact(run_id, stderr, {**meta, "stream": "stderr"})
            paths = [p for p in [p_out, p_err] if p]

            if proc.returncode == 0:
                return "DONE", None, paths

            # Windows: 0xC000013A = STATUS_CONTROL_C_EXIT (often shows up as 3221225786).
            if proc.returncode in (3221225786, -1073741510):
                return "FAILED", "opencode interrupted (Ctrl+C / termination)", paths

            return (
                "FAILED",
                (
                    stderr.strip()
                    or stdout.strip()
                    or f"opencode exited {proc.returncode}"
                ),
                paths,
            )

        except subprocess.TimeoutExpired:
            path = self._store_artifact(
                run_id,
                f"Timeout after {timeout_s}s\n",
                {
                    "task_id": task_id,
                    "executor": executor,
                    "worker_id": self.worker_id,
                    "mode": "timeout",
                    "ts": _utc_now_iso(),
                },
            )
            return "FAILED", f"Timeout after {timeout_s}s", [p for p in [path] if p]
        except FileNotFoundError:
            return "FAILED", "opencode not found on PATH", []
        except Exception as e:
            return "FAILED", str(e), []

    def run(self) -> None:
        self.running = True
        self._log(f"Started (poll_ms={self.poll_ms}, run_opencode={self.run_opencode})")

        while self.running:
            try:
                task = self._claim_next_task_atomic()
                if not task:
                    time.sleep(self.poll_ms / 1000.0)
                    continue

                task_id = task["task_id"]
                run_id = task.get("run_id")
                self._log(f"Claimed {task_id} (run={run_id})")

                status, err, artifact_paths = self._execute(task)

                if status == "DONE":
                    self.db.complete_task(
                        task_id=task_id,
                        status="DONE",
                        artifact_writes=artifact_paths,
                        error=None,
                    )
                    self.stats["completed"] += 1
                else:
                    self.db.complete_task(
                        task_id=task_id,
                        status="FAILED",
                        artifact_writes=artifact_paths,
                        error=err,
                    )
                    self.stats["failed"] += 1

            except KeyboardInterrupt:
                break
            except Exception as e:
                self._log(f"Loop error: {e}", "ERROR")
                time.sleep(1.0)

        self._log(f"Stopped. Stats={json.dumps(self.stats)}")

    def stop(self) -> None:
        self.running = False


class WorkerPool:
    def __init__(
        self,
        workers: int,
        poll_ms: int,
        run_opencode: bool,
        opencode_timeout_s: int,
        daemon: bool = False,
    ):
        self.workers = workers
        self.poll_ms = poll_ms
        self.run_opencode = run_opencode
        self.opencode_timeout_s = opencode_timeout_s
        self.daemon = daemon
        self.instances: List[TaskBusWorker] = []
        self.threads: List[threading.Thread] = []

    def start(self) -> None:
        print(
            f"Starting worker pool: workers={self.workers} poll_ms={self.poll_ms} run_opencode={self.run_opencode}"
        )
        for i in range(self.workers):
            w = TaskBusWorker(
                f"worker-{i + 1}",
                self.poll_ms,
                self.run_opencode,
                self.opencode_timeout_s,
            )
            t = threading.Thread(target=w.run, daemon=self.daemon)
            self.instances.append(w)
            self.threads.append(t)
            t.start()
            time.sleep(0.05)

    def stop(self) -> None:
        for w in self.instances:
            w.stop()
        for t in self.threads:
            t.join(timeout=5)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--project-root",
        type=str,
        default=None,
        help="Marker for process management; does not change behavior.",
    )
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--poll-ms", type=int, default=500)
    ap.add_argument("--run-opencode", action="store_true")
    ap.add_argument(
        "--fast-complete",
        action="store_true",
        help="Mark tasks DONE without LLM execution (dev/testing)",
    )
    ap.add_argument("--opencode-timeout-s", type=int, default=300)
    args = ap.parse_args()

    if args.project_root:
        try:
            os.chdir(args.project_root)
        except Exception:
            pass

    # Fast-complete mode can be set via CLI or environment variable
    if args.fast_complete:
        os.environ["OPENCODE_WORKER_FAST_COMPLETE"] = "1"

    # NOTE: We intentionally do not chdir here. oc.bat launches this worker from the project directory.
    # The --project-root flag exists only so oc.bat can identify/kill workers per project.

    pool = WorkerPool(
        args.workers, args.poll_ms, args.run_opencode, args.opencode_timeout_s
    )

    def _sigint(_sig, _frame):
        pool.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _sigint)

    pool.start()
    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
