import os
import sys
import json
import asyncpg
from datetime import datetime
from typing import Optional, Dict, Any, Union
from contextlib import asynccontextmanager
import pathlib

# Platform-specific file locking
if sys.platform == "win32":
    import msvcrt

    def file_lock(f):
        msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)

    def file_unlock(f):
        f.seek(0)
        msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
else:
    import fcntl

    def file_lock(f):
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)

    def file_unlock(f):
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)


class EventEmitter:
    def __init__(self, postgres_pool: asyncpg.Pool, project_id: str):
        self.postgres_pool = postgres_pool
        self.project_id = project_id
        self.ndjson_path = pathlib.Path(".ai/artifacts/task_events.ndjson")
        self.ndjson_path.parent.mkdir(parents=True, exist_ok=True)

    async def emit(
        self,
        event_type: str,
        payload: Dict[str, Any],
        run_id: Optional[str] = None,
        task_id: Optional[str] = None,
        agent: Optional[str] = None,
        worker_pid: Optional[int] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
    ) -> str:
        timestamp = datetime.utcnow()

        event = {
            "event_type": event_type,
            "project_id": self.project_id,
            "run_id": run_id,
            "task_id": task_id,
            "agent": agent,
            "worker_pid": worker_pid,
            "model": model,
            "provider": provider,
            "payload": payload,
            "ts": timestamp.isoformat(),
        }

        event_id = await self._write_to_postgres(event)
        await self._write_to_ndjson(event)

        return event_id

    async def _write_to_postgres(self, event: Dict[str, Any]) -> str:
        async with self.postgres_pool.acquire() as conn:
            result = await conn.execute(
                """
                INSERT INTO task_events 
                (event_type, project_id, run_id, task_id, agent, worker_pid, model, provider, payload, ts)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                RETURNING id
                """,
                event["event_type"],
                event["project_id"],
                event["run_id"],
                event["task_id"],
                event["agent"],
                event["worker_pid"],
                event["model"],
                event["provider"],
                json.dumps(event["payload"]),
                event["ts"],
            )

            return str(result.split(" ")[-1])

    async def _write_to_ndjson(self, event: Dict[str, Any]) -> None:
        line = json.dumps(event) + "\n"

        with open(self.ndjson_path, "a") as f:
            try:
                file_lock(f)
                f.write(line)
                f.flush()
                os.fsync(f.fileno())
            finally:
                file_unlock(f)

    async def get_recent_events(
        self,
        limit: int = 100,
        event_type: Optional[str] = None,
        run_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> list:
        async with self.postgres_pool.acquire() as conn:
            conditions = ["project_id = $1"]
            params = [self.project_id]
            param_idx = 2

            if event_type:
                conditions.append(f"event_type = ${param_idx}")
                params.append(event_type)
                param_idx += 1

            if run_id:
                conditions.append(f"run_id = ${param_idx}")
                params.append(run_id)
                param_idx += 1

            if task_id:
                conditions.append(f"task_id = ${param_idx}")
                params.append(task_id)
                param_idx += 1

            where_clause = " AND ".join(conditions)

            rows = await conn.fetch(
                f"""
                SELECT * FROM task_events
                WHERE {where_clause}
                ORDER BY ts DESC
                LIMIT ${param_idx}
                """,
                *params,
                limit,
            )

            return [dict(r) for r in rows]

    async def get_run_timeline(self, run_id: str) -> list:
        async with self.postgres_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM task_events
                WHERE project_id = $1 AND run_id = $2
                ORDER BY ts ASC
                """,
                self.project_id,
                run_id,
            )

            return [dict(r) for r in rows]

    async def get_worker_status(self) -> list:
        async with self.postgres_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT DISTINCT ON (worker_pid)
                    worker_pid, agent, MAX(ts) as last_heartbeat,
                    COUNT(*) as event_count
                FROM task_events
                WHERE project_id = $1 AND worker_pid IS NOT NULL
                GROUP BY worker_pid, agent
                ORDER BY worker_pid
                """,
                self.project_id,
            )

            return [dict(r) for r in rows]


class Redactor:
    SENSITIVE_KEYS = [
        "api_key",
        "token",
        "password",
        "secret",
        "private_key",
        "credential",
        "auth",
        "cookie",
        "session",
    ]

    @staticmethod
    def redact(data: Union[Dict[str, Any], list]) -> Union[Dict[str, Any], list]:
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                if any(
                    sensitive in key.lower() for sensitive in Redactor.SENSITIVE_KEYS
                ):
                    result[key] = "[REDACTED]"
                elif isinstance(value, (dict, list)):
                    result[key] = Redactor.redact(value)
                else:
                    result[key] = value
            return result
        elif isinstance(data, list):
            return [
                Redactor.redact(item) if isinstance(item, dict) else item
                for item in data
            ]
        else:
            return data
