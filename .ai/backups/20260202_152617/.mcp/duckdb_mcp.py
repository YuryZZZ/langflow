#!/usr/bin/env python3
"""
DuckDB Task Bus MCP Server - Production Configuration
=====================================================
Project-isolated task/gate management.
This is the 'duckdb' MCP referenced in ORCHESTRATOR.md

33 Agents | 7 Providers | GLM-4.7 Primary Coder

Tools provided:
- create_run, get_current_run, complete_run, get_next_planner
- get_gate, get_all_gates, freeze_gate, can_proceed_to_gate
- create_task, claim_task, complete_task, retry_task, get_next_task, list_tasks
- register_artifact, get_artifact, verify_artifact
- acquire_lock, release_lock
- validate_cross_model, get_valid_validators, get_recommended_coder
- track_cost, get_cost_summary, get_stats, get_project_info
"""

import json
import sys
import os
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import threading

# Thread lock for DuckDB operations
_db_lock = threading.Lock()

# Lazy import duckdb to catch import errors
duckdb = None

def get_duckdb():
    global duckdb
    if duckdb is None:
        import duckdb as _duckdb
        duckdb = _duckdb
    return duckdb

# Global paths - single DB in global config, project tables inside
GLOBAL_DIR = Path.home() / ".config" / "opencode"
DB_PATH = GLOBAL_DIR / "task_bus.db"

# Project paths - for logs and artifacts only
PROJECT_DIR = Path(os.getcwd())
AI_DIR = PROJECT_DIR / ".ai"
NDJSON_PATH = AI_DIR / "artifacts" / "task_events.ndjson"

# Project identifier for table prefixes (hash of project path)
def get_project_id():
    """Get short project identifier from current directory"""
    return hashlib.md5(str(PROJECT_DIR).encode()).hexdigest()[:8]

# Gate configuration - SIMPLE WORKFLOW (no blocking)
GATES = {
    "A": {"name": "Architecture Freeze", "requires": [], "produces": ["architecture.yaml"], "blocked_agents": [], "validators": ["validator"]},
    "B": {"name": "Contract Freeze", "requires": [], "produces": ["contracts.yaml"], "blocked_agents": [], "validators": ["validator"]},
    "C": {"name": "Merge Freeze", "requires": [], "produces": ["merge_report.json"], "blocked_agents": [], "validators": ["validator"]},
    "D": {"name": "Integration Gate", "requires": [], "produces": ["integration_report.json"], "blocked_agents": [], "validators": ["validator"]}
}

# Model families for cross-validation - matches opencode.json providers
MODEL_FAMILIES = {
    "zai": ["glm", "glm-4.6", "glm-4.7", "coder", "coder-ts", "tester", "reviewer", "researcher", "planner-5"],
    "google": ["gemini", "gemini-3-flash", "gemini-3-pro", "planner-1", "validator", "coder-fast", "debugger", "analyst", "gemini-pro", "gemini-flash"],
    "openai": ["gpt", "gpt-5.2", "gpt-5.1", "gpt-5.1-codex", "orchestrator", "planner-3", "build"],
    "anthropic": ["claude", "claude-sonnet", "claude-haiku", "claude-opus", "planner-2", "security", "validator-anthropic"],
    "deepseek": ["deepseek", "deepseek-chat", "deepseek-reasoner", "planner-4", "coder-deepseek", "deepseek-think"],
    "groq": ["llama", "llama-3.3", "llama-3.1", "kimi", "gpt-oss", "mass-worker", "cheap-worker", "reasoner", "coder-groq"],
    "perplexity": ["sonar", "sonar-pro", "search"]
}

# Valid cross-validation pairs
VALID_VALIDATION_PAIRS = {
    "coder": ["validator", "claude-haiku", "gemini-flash"],
    "coder-ts": ["validator", "claude-haiku", "gemini-flash"],
    "tester": ["validator", "claude-haiku"],
    "reviewer": ["validator", "claude-haiku"],
    "coder-fast": ["reviewer", "claude-haiku", "tester"],
    "validator": ["reviewer", "claude-haiku"],
    "coder-deepseek": ["validator", "reviewer", "gemini-flash"],
    "deepseek-think": ["validator", "reviewer"],
    "mass-worker": ["validator", "reviewer", "claude-haiku"],
    "cheap-worker": ["validator", "reviewer"],
    "kimi": ["validator", "reviewer", "claude-haiku"],
    "reasoner": ["validator", "reviewer", "claude-haiku"],
    "build": ["validator", "reviewer", "claude-haiku", "deepseek-think"],
    "coder-groq": ["validator", "reviewer", "claude-haiku"]
}

NON_CODING_AGENTS = ["cheap-worker", "orchestrator", "search"]


class TaskBusDB:
    """Global task bus database using DuckDB - single DB, project isolation via project_id"""

    def __init__(self):
        self.conn = None
        self._lock = _db_lock
        self.project_id = get_project_id()
        self.project_path = str(PROJECT_DIR)
        self._ensure_directories()
        self._connect()
        self._init_schema()
        self._register_project()

    def _ensure_directories(self):
        """Create required directories - global and project-local"""
        try:
            # Global directory for DB
            GLOBAL_DIR.mkdir(parents=True, exist_ok=True)
            # Project directory for logs/artifacts
            AI_DIR.mkdir(parents=True, exist_ok=True)
            (AI_DIR / "artifacts").mkdir(exist_ok=True)
            (AI_DIR / "artifacts" / "planner_plans").mkdir(exist_ok=True)
            (AI_DIR / "artifacts" / "agent_results").mkdir(exist_ok=True)
            (AI_DIR / "logs").mkdir(exist_ok=True)
        except Exception as e:
            raise RuntimeError(f"Failed to create directories: {e}")

    def _connect(self):
        """Connect to global DuckDB with multi-process support

        Strategy: Use fresh connection per operation for true concurrent access.
        DuckDB supports multiple readers but only one writer at a time.
        """
        import time
        duckdb_module = get_duckdb()

        max_retries = 10
        for attempt in range(max_retries):
            try:
                # Close existing connection if any
                if self.conn is not None:
                    try:
                        self.conn.close()
                    except:
                        pass
                    self.conn = None

                # Connect with read_write mode - allows concurrent access
                self.conn = duckdb_module.connect(str(DB_PATH), read_only=False)
                return
            except Exception as e:
                error_msg = str(e).lower()
                if "being used by another process" in error_msg or "locked" in error_msg or "cannot open" in error_msg:
                    if attempt < max_retries - 1:
                        time.sleep(0.2 * (attempt + 1))  # Exponential backoff
                        continue
                raise RuntimeError(f"Failed to connect to DuckDB at {DB_PATH}: {e}\nFile is already open in another process. Kill stale processes or wait.")

    def _reconnect_if_needed(self):
        """Reconnect if connection is stale or closed"""
        try:
            # Quick test query
            self.conn.execute("SELECT 1")
        except:
            self._connect()

    def _safe_execute(self, query: str, params: list = None, fetch: str = None):
        """Execute query with auto-reconnect and retry for concurrent access

        Args:
            query: SQL query
            params: Query parameters
            fetch: 'one', 'all', or None
        Returns:
            Query result or None
        """
        import time
        max_retries = 5

        for attempt in range(max_retries):
            try:
                with self._lock:
                    self._reconnect_if_needed()
                    if params:
                        result = self.conn.execute(query, params)
                    else:
                        result = self.conn.execute(query)

                    if fetch == 'one':
                        return result.fetchone()
                    elif fetch == 'all':
                        return result.fetchall()
                    return result
            except Exception as e:
                error_msg = str(e).lower()
                if ("locked" in error_msg or "another process" in error_msg) and attempt < max_retries - 1:
                    time.sleep(0.2 * (attempt + 1))
                    self._connect()  # Force reconnect
                    continue
                raise

    def _init_schema(self):
        """Initialize database schema - single global DB with project_id for isolation"""
        try:
            # Projects registry table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    project_id TEXT PRIMARY KEY,
                    project_path TEXT,
                    created_at TEXT,
                    last_accessed TEXT
                )
            """)

            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    project_id TEXT,
                    created_at TEXT,
                    status TEXT DEFAULT 'RUNNING',
                    current_gate TEXT DEFAULT 'A',
                    cts_hash TEXT,
                    updated_at TEXT,
                    planner_index INTEGER DEFAULT 0
                )
            """)

            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS gates (
                    gate_id TEXT PRIMARY KEY,
                    project_id TEXT,
                    run_id TEXT,
                    gate_name TEXT,
                    status TEXT DEFAULT 'PENDING',
                    frozen_hashes TEXT DEFAULT '{}',
                    validated_by TEXT DEFAULT '[]',
                    frozen_at TEXT
                )
            """)

            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    project_id TEXT,
                    run_id TEXT,
                    gate TEXT,
                    task_type TEXT,
                    role TEXT,
                    agent TEXT,
                    status TEXT DEFAULT 'QUEUED',
                    priority INTEGER DEFAULT 5,
                    complexity INTEGER DEFAULT 3,
                    deps TEXT DEFAULT '[]',
                    artifact_writes TEXT DEFAULT '[]',
                    timeout_ms INTEGER DEFAULT 60000,
                    attempts INTEGER DEFAULT 0,
                    max_attempts INTEGER DEFAULT 3,
                    last_error TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)

            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    event_id INTEGER PRIMARY KEY,
                    project_id TEXT,
                    run_id TEXT,
                    task_id TEXT,
                    ts TEXT,
                    event_type TEXT,
                    payload TEXT
                )
            """)

            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS artifacts (
                    artifact_id TEXT PRIMARY KEY,
                    project_id TEXT,
                    run_id TEXT,
                    task_id TEXT,
                    path TEXT,
                    hash TEXT,
                    created_at TEXT
                )
            """)

            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS locks (
                    lock_key TEXT PRIMARY KEY,
                    holder TEXT,
                    expires_at TEXT
                )
            """)

            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS blocked (
                    id INTEGER PRIMARY KEY,
                    project_id TEXT,
                    ts TEXT,
                    run_id TEXT,
                    agent TEXT,
                    gate TEXT,
                    reason TEXT
                )
            """)

            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS cost_tracking (
                    id INTEGER PRIMARY KEY,
                    project_id TEXT,
                    run_id TEXT,
                    agent TEXT,
                    model TEXT,
                    tokens_in INTEGER,
                    tokens_out INTEGER,
                    cost_usd REAL,
                    ts TEXT
                )
            """)

            # Create indexes (ignore if exist)
            for idx in [
                "CREATE INDEX IF NOT EXISTS idx_runs_project ON runs(project_id)",
                "CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_id)",
                "CREATE INDEX IF NOT EXISTS idx_tasks_run ON tasks(run_id)",
                "CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)",
                "CREATE INDEX IF NOT EXISTS idx_gates_project ON gates(project_id)",
                "CREATE INDEX IF NOT EXISTS idx_gates_run ON gates(run_id)",
                "CREATE INDEX IF NOT EXISTS idx_events_project ON events(project_id)",
                "CREATE INDEX IF NOT EXISTS idx_cost_project ON cost_tracking(project_id)",
                "CREATE INDEX IF NOT EXISTS idx_cost_run ON cost_tracking(run_id)"
            ]:
                try:
                    self.conn.execute(idx)
                except:
                    pass
        except Exception as e:
            raise RuntimeError(f"Failed to initialize schema: {e}")

    def _register_project(self):
        """Register current project in the projects table"""
        now = self._now()
        try:
            with self._lock:
                # Check if project exists
                result = self.conn.execute("SELECT project_id FROM projects WHERE project_id = ?", [self.project_id])
                if result.fetchone() is None:
                    # New project - insert
                    self.conn.execute(
                        "INSERT INTO projects (project_id, project_path, created_at, last_accessed) VALUES (?, ?, ?, ?)",
                        [self.project_id, self.project_path, now, now]
                    )
                else:
                    # Update last_accessed
                    self.conn.execute(
                        "UPDATE projects SET last_accessed = ?, project_path = ? WHERE project_id = ?",
                        [now, self.project_path, self.project_id]
                    )
        except:
            pass  # Non-fatal if registration fails

    def _now(self):
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def _uuid(self):
        return str(uuid.uuid4())[:8]

    def _hash(self, content: str) -> str:
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _row_to_dict(self, row, columns: list) -> Optional[Dict]:
        if row is None:
            return None
        return dict(zip(columns, row))

    def _log_event(self, run_id: str, task_id: Optional[str], event_type: str, payload: Dict):
        now = self._now()
        try:
            with self._lock:
                result = self.conn.execute("SELECT COALESCE(MAX(event_id), 0) + 1 FROM events").fetchone()
                event_id = result[0] if result else 1
                self.conn.execute("""
                    INSERT INTO events (event_id, project_id, run_id, task_id, ts, event_type, payload)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, [event_id, self.project_id, run_id, task_id, now, event_type, json.dumps(payload)])
        except:
            pass

        # NDJSON fallback (project-local)
        try:
            NDJSON_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(NDJSON_PATH, "a") as f:
                f.write(json.dumps({"project_id": self.project_id, "run_id": run_id, "task_id": task_id, "ts": now, "event_type": event_type, "payload": payload}) + "\n")
        except:
            pass

    # === RUN MANAGEMENT ===

    def create_run(self, cts_hash: Optional[str] = None) -> Dict:
        run_id = f"run_{self._uuid()}"
        now = self._now()
        self.conn.execute("INSERT INTO runs (run_id, project_id, created_at, updated_at, cts_hash, current_gate, planner_index) VALUES (?, ?, ?, ?, ?, 'A', 0)", [run_id, self.project_id, now, now, cts_hash])
        for gate_name in ["A", "B", "C", "D"]:
            self.conn.execute("INSERT INTO gates (gate_id, project_id, run_id, gate_name, status) VALUES (?, ?, ?, ?, 'PENDING')", [f"gate_{gate_name}_{self._uuid()}", self.project_id, run_id, gate_name])
        self._log_event(run_id, None, "RUN_CREATED", {"cts_hash": cts_hash})
        return {"run_id": run_id, "project_id": self.project_id, "created_at": now, "gates_created": ["A", "B", "C", "D"]}

    def get_current_run(self) -> Optional[Dict]:
        """Get current run for THIS project only"""
        row = self._safe_execute(
            "SELECT run_id, project_id, created_at, status, current_gate, cts_hash, updated_at, planner_index FROM runs WHERE project_id = ? AND status = 'RUNNING' ORDER BY created_at DESC LIMIT 1",
            [self.project_id], fetch='one'
        )
        return self._row_to_dict(row, ["run_id", "project_id", "created_at", "status", "current_gate", "cts_hash", "updated_at", "planner_index"]) if row else None

    def complete_run(self, run_id: str, status: str = "COMPLETED") -> Dict:
        self._safe_execute("UPDATE runs SET status = ?, updated_at = ? WHERE run_id = ? AND project_id = ?", [status, self._now(), run_id, self.project_id])
        self._log_event(run_id, None, "RUN_COMPLETED", {"status": status})
        return {"run_id": run_id, "status": status}

    def get_next_planner(self, run_id: str) -> Dict:
        planners = ["planner-1", "planner-2", "planner-3", "planner-4", "planner-5"]
        row = self._safe_execute("SELECT planner_index FROM runs WHERE run_id = ?", [run_id], fetch='one')
        if not row:
            return {"error": "Run not found"}
        current_idx = row[0] or 0
        next_idx = (current_idx + 1) % 5
        self._safe_execute("UPDATE runs SET planner_index = ? WHERE run_id = ?", [next_idx, run_id])
        return {"planner": planners[current_idx], "next_planner": planners[next_idx], "index": current_idx}

    # === GATE MANAGEMENT ===

    def get_gate(self, run_id: str, gate_name: str) -> Dict:
        row = self._safe_execute(
            "SELECT gate_id, run_id, gate_name, status, frozen_hashes, validated_by, frozen_at FROM gates WHERE run_id = ? AND gate_name = ?",
            [run_id, gate_name], fetch='one'
        )
        if not row:
            return {"status": "NOT_FOUND", "gate_name": gate_name}
        cols = ["gate_id", "run_id", "gate_name", "status", "frozen_hashes", "validated_by", "frozen_at"]
        result_dict = self._row_to_dict(row, cols)
        result_dict["frozen_hashes"] = json.loads(result_dict.get("frozen_hashes", "{}") or "{}")
        result_dict["validated_by"] = json.loads(result_dict.get("validated_by", "[]") or "[]")
        result_dict["config"] = GATES.get(gate_name, {})
        return result_dict

    def get_all_gates(self, run_id: str) -> Dict:
        gates = {g: self.get_gate(run_id, g) for g in ["A", "B", "C", "D"]}
        row = self._safe_execute("SELECT current_gate, planner_index FROM runs WHERE run_id = ?", [run_id], fetch='one')
        return {"gates": gates, "current_gate": row[0] if row else "A", "planner_index": row[1] if row else 0}

    def freeze_gate(self, run_id: str, gate_name: str, frozen_hashes: Dict, validated_by: list) -> Dict:
        now = self._now()
        can_proceed, reason = self.can_proceed_to_gate(run_id, gate_name)
        if not can_proceed:
            return {"error": reason}
        self._safe_execute("UPDATE gates SET status = 'FROZEN', frozen_hashes = ?, validated_by = ?, frozen_at = ? WHERE run_id = ? AND gate_name = ?", [json.dumps(frozen_hashes), json.dumps(validated_by), now, run_id, gate_name])
        gate_order = ["A", "B", "C", "D"]
        idx = gate_order.index(gate_name)
        if idx < 3:
            self._safe_execute("UPDATE runs SET current_gate = ?, updated_at = ? WHERE run_id = ?", [gate_order[idx + 1], now, run_id])
        self._log_event(run_id, None, "GATE_FROZEN", {"gate": gate_name, "hashes": frozen_hashes, "validators": validated_by})
        return {"gate": gate_name, "status": "FROZEN", "frozen_at": now, "next_gate": gate_order[idx + 1] if idx < 3 else None}

    def can_proceed_to_gate(self, run_id: str, gate_name: str) -> Tuple[bool, str]:
        gate_order = ["A", "B", "C", "D"]
        target_idx = gate_order.index(gate_name)
        for i in range(target_idx):
            gate = self.get_gate(run_id, gate_order[i])
            if gate.get("status") != "FROZEN":
                return False, f"Gate {gate_order[i]} must be FROZEN before Gate {gate_name}"
        return True, "OK"

    # === AGENT BLOCKING ===

    def is_agent_allowed(self, run_id: str, agent: str) -> Tuple[bool, str]:
        row = self._safe_execute("SELECT current_gate FROM runs WHERE run_id = ?", [run_id], fetch='one')
        if not row:
            return False, "Run not found"
        current_gate = row[0]
        gate_config = GATES.get(current_gate, {})
        blocked_agents = gate_config.get("blocked_agents", [])
        agent_lower = agent.lower().replace("-", "_").replace("_", "-")
        for blocked in blocked_agents:
            if blocked.lower() in agent_lower or agent_lower in blocked.lower():
                reason = f"Agent '{agent}' is BLOCKED at Gate {current_gate}"
                try:
                    result = self._safe_execute("SELECT COALESCE(MAX(id), 0) + 1 FROM blocked", fetch='one')
                    self._safe_execute("INSERT INTO blocked (id, ts, run_id, agent, gate, reason) VALUES (?, ?, ?, ?, ?, ?)", [result[0], self._now(), run_id, agent, current_gate, reason])
                except:
                    pass
                return False, reason
        return True, "OK"

    def is_coding_allowed(self, agent: str) -> Tuple[bool, str]:
        agent_lower = agent.lower().replace("-", "_").replace("_", "-")
        for non_coder in NON_CODING_AGENTS:
            if non_coder in agent_lower:
                return False, f"Agent '{agent}' is NOT allowed to write code"
        return True, "OK"

    # === TASK MANAGEMENT ===

    TASK_COLS = ["task_id", "project_id", "run_id", "gate", "task_type", "role", "agent", "status", "priority", "complexity", "deps", "artifact_writes", "timeout_ms", "attempts", "max_attempts", "last_error", "created_at", "updated_at"]

    def create_task(self, run_id: str, task_type: str, role: str, priority: int = 5, complexity: int = 3, deps: list = None, timeout_ms: int = 60000) -> Dict:
        task_id = f"task_{self._uuid()}"
        now = self._now()
        with self._lock:
            result = self.conn.execute("SELECT current_gate FROM runs WHERE run_id = ? AND project_id = ?", [run_id, self.project_id])
            row = result.fetchone()
            current_gate = row[0] if row else "A"
            self.conn.execute("INSERT INTO tasks (task_id, project_id, run_id, gate, task_type, role, priority, complexity, deps, timeout_ms, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", [task_id, self.project_id, run_id, current_gate, task_type, role, priority, complexity, json.dumps(deps or []), timeout_ms, now, now])
        self._log_event(run_id, task_id, "TASK_CREATED", {"task_type": task_type, "role": role, "complexity": complexity})
        return {"task_id": task_id, "project_id": self.project_id, "run_id": run_id, "gate": current_gate, "status": "QUEUED", "complexity": complexity}

    def claim_task(self, task_id: str, holder: str) -> Dict:
        now = self._now()
        with self._lock:
            self.conn.execute("UPDATE tasks SET status = 'RUNNING', agent = ?, attempts = attempts + 1, updated_at = ? WHERE task_id = ? AND status IN ('QUEUED', 'RETRY')", [holder, now, task_id])
            result = self.conn.execute("SELECT run_id, status FROM tasks WHERE task_id = ?", [task_id])
            row = result.fetchone()
        if not row or row[1] != 'RUNNING':
            return {"error": "Task not available or already claimed"}
        self._log_event(row[0], task_id, "TASK_CLAIMED", {"holder": holder})
        return {"task_id": task_id, "status": "RUNNING", "holder": holder}

    def complete_task(self, task_id: str, status: str = "DONE", artifact_writes: list = None, error: str = None) -> Dict:
        self._safe_execute("UPDATE tasks SET status = ?, artifact_writes = ?, last_error = ?, updated_at = ? WHERE task_id = ?", [status, json.dumps(artifact_writes or []), error, self._now(), task_id])
        row = self._safe_execute("SELECT run_id FROM tasks WHERE task_id = ?", [task_id], fetch='one')
        if row:
            self._log_event(row[0], task_id, "TASK_COMPLETED", {"status": status})
        return {"task_id": task_id, "status": status}

    def retry_task(self, task_id: str, error: str) -> Dict:
        row = self._safe_execute("SELECT run_id, attempts, max_attempts FROM tasks WHERE task_id = ?", [task_id], fetch='one')
        if not row:
            return {"error": "Task not found"}
        if row[1] >= row[2]:
            return self.complete_task(task_id, "FAILED", error=error)
        self._safe_execute("UPDATE tasks SET status = 'RETRY', last_error = ?, updated_at = ? WHERE task_id = ?", [error, self._now(), task_id])
        self._log_event(row[0], task_id, "TASK_RETRY", {"attempt": row[1], "error": error})
        return {"task_id": task_id, "status": "RETRY", "attempts": row[1]}

    def get_next_task(self, run_id: str, role: str = None) -> Optional[Dict]:
        query = "SELECT task_id, project_id, run_id, gate, task_type, role, agent, status, priority, complexity, deps, artifact_writes, timeout_ms, attempts, max_attempts, last_error, created_at, updated_at FROM tasks WHERE run_id = ? AND project_id = ? AND status = 'QUEUED'"
        params = [run_id, self.project_id]
        if role:
            query += " AND role = ?"
            params.append(role)
        query += " ORDER BY priority DESC, created_at ASC LIMIT 1"
        row = self._safe_execute(query, params, fetch='one')
        return self._row_to_dict(row, self.TASK_COLS) if row else None

    def list_tasks(self, run_id: str, status: str = None) -> list:
        query = "SELECT task_id, project_id, run_id, gate, task_type, role, agent, status, priority, complexity, deps, artifact_writes, timeout_ms, attempts, max_attempts, last_error, created_at, updated_at FROM tasks WHERE run_id = ? AND project_id = ?"
        params = [run_id, self.project_id]
        if status:
            query += " AND status = ?"
            params.append(status)
        rows = self._safe_execute(query, params, fetch='all')
        return [self._row_to_dict(r, self.TASK_COLS) for r in (rows or [])]

    # === ARTIFACT MANAGEMENT ===

    ARTIFACT_COLS = ["artifact_id", "run_id", "task_id", "path", "hash", "created_at"]

    def register_artifact(self, run_id: str, task_id: Optional[str], path: str, content_hash: str) -> Dict:
        artifact_id = f"art_{self._uuid()}"
        now = self._now()
        self.conn.execute("DELETE FROM artifacts WHERE path = ?", [path])
        self.conn.execute("INSERT INTO artifacts (artifact_id, run_id, task_id, path, hash, created_at) VALUES (?, ?, ?, ?, ?, ?)", [artifact_id, run_id, task_id, path, content_hash, now])
        self._log_event(run_id, task_id, "ARTIFACT_REGISTERED", {"path": path, "hash": content_hash})
        return {"artifact_id": artifact_id, "path": path, "hash": content_hash}

    def get_artifact(self, path: str) -> Optional[Dict]:
        result = self.conn.execute("SELECT artifact_id, run_id, task_id, path, hash, created_at FROM artifacts WHERE path = ? ORDER BY created_at DESC LIMIT 1", [path])
        row = result.fetchone()
        return self._row_to_dict(row, self.ARTIFACT_COLS) if row else None

    def verify_artifact(self, path: str, expected_hash: str) -> Dict:
        artifact = self.get_artifact(path)
        if not artifact:
            return {"valid": False, "error": "Artifact not found"}
        return {"valid": artifact["hash"] == expected_hash, "current_hash": artifact["hash"]}

    # === LOCK MANAGEMENT ===

    def acquire_lock(self, lock_key: str, holder: str, ttl_seconds: int = 300) -> Dict:
        now = datetime.now(timezone.utc)
        expires = (now + timedelta(seconds=ttl_seconds)).isoformat().replace("+00:00", "Z")
        self.conn.execute("DELETE FROM locks WHERE expires_at < ?", [now.isoformat().replace("+00:00", "Z")])
        result = self.conn.execute("SELECT holder FROM locks WHERE lock_key = ?", [lock_key])
        existing = result.fetchone()
        if existing:
            return {"acquired": False, "held_by": existing[0]}
        try:
            self.conn.execute("INSERT INTO locks (lock_key, holder, expires_at) VALUES (?, ?, ?)", [lock_key, holder, expires])
            return {"acquired": True, "lock_key": lock_key, "expires_at": expires}
        except:
            result = self.conn.execute("SELECT holder FROM locks WHERE lock_key = ?", [lock_key])
            existing = result.fetchone()
            return {"acquired": False, "held_by": existing[0] if existing else None}

    def release_lock(self, lock_key: str, holder: str) -> Dict:
        result = self.conn.execute("SELECT holder FROM locks WHERE lock_key = ? AND holder = ?", [lock_key, holder])
        if result.fetchone():
            self.conn.execute("DELETE FROM locks WHERE lock_key = ? AND holder = ?", [lock_key, holder])
            return {"released": True}
        return {"released": False}

    # === CROSS-MODEL VALIDATION ===

    def get_model_family(self, agent: str) -> Optional[str]:
        agent_lower = agent.lower().replace("_", "-")
        for family, agents in MODEL_FAMILIES.items():
            for a in agents:
                if a.lower().replace("_", "-") == agent_lower:
                    return family
        for family, agents in MODEL_FAMILIES.items():
            for a in agents:
                a_norm = a.lower().replace("_", "-")
                if a_norm in agent_lower or agent_lower in a_norm:
                    return family
        return None

    def validate_cross_model(self, coder: str, validator: str) -> Dict:
        coder_family = self.get_model_family(coder)
        validator_family = self.get_model_family(validator)
        if coder_family and validator_family and coder_family == validator_family:
            return {"valid": False, "error": f"Cross-model violation: {coder} and {validator} are same family ({coder_family})", "coder_family": coder_family, "validator_family": validator_family}
        return {"valid": True, "coder_family": coder_family, "validator_family": validator_family}

    def get_valid_validators(self, coder: str) -> list:
        return VALID_VALIDATION_PAIRS.get(coder.lower().replace("_", "-"), [])

    def get_recommended_coder(self, complexity: int) -> Dict:
        if complexity <= 2:
            return {"coder": "coder-fast", "validator": None, "reason": "Low complexity"}
        elif complexity <= 4:
            return {"coder": "coder", "validator": "validator", "reason": "Standard task"}
        elif complexity <= 6:
            return {"coder": "coder", "validator": "validator", "secondary_validator": "reviewer", "reason": "Medium complexity"}
        elif complexity <= 8:
            return {"coder": "coder-ts", "validator": "claude-haiku", "secondary_validator": "validator", "reason": "High complexity"}
        else:
            return {"coder": "coder-deepseek", "validator": "validator", "escalation": "claude-sonnet", "reason": "Critical complexity"}

    # === COST TRACKING ===

    def track_cost(self, run_id: str, agent: str, model: str, tokens_in: int, tokens_out: int, cost_usd: float) -> Dict:
        result = self.conn.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM cost_tracking").fetchone()
        self.conn.execute("INSERT INTO cost_tracking (id, run_id, agent, model, tokens_in, tokens_out, cost_usd, ts) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", [result[0], run_id, agent, model, tokens_in, tokens_out, cost_usd, self._now()])
        return {"tracked": True, "cost_usd": cost_usd}

    def get_cost_summary(self, run_id: str) -> Dict:
        result = self.conn.execute("SELECT SUM(tokens_in), SUM(tokens_out), SUM(cost_usd), COUNT(*) FROM cost_tracking WHERE run_id = ?", [run_id])
        row = result.fetchone()
        return {"run_id": run_id, "total_tokens_in": row[0] or 0, "total_tokens_out": row[1] or 0, "total_cost_usd": row[2] or 0.0, "api_calls": row[3] or 0}

    # === STATS ===

    def get_stats(self, run_id: str) -> Dict:
        stats = {"run_id": run_id, "tasks": {}, "gates": {}, "blocked_count": 0, "cost": self.get_cost_summary(run_id)}
        for status in ["QUEUED", "RUNNING", "DONE", "FAILED", "RETRY"]:
            result = self.conn.execute("SELECT COUNT(*) FROM tasks WHERE run_id = ? AND status = ?", [run_id, status])
            stats["tasks"][status.lower()] = result.fetchone()[0] or 0
        for gate in ["A", "B", "C", "D"]:
            stats["gates"][gate] = self.get_gate(run_id, gate).get("status", "PENDING")
        result = self.conn.execute("SELECT COUNT(*) FROM blocked WHERE run_id = ?", [run_id])
        stats["blocked_count"] = result.fetchone()[0] or 0
        return stats

    def get_project_info(self) -> Dict:
        """Get project info - shows current project stats from global DB"""
        project_runs = self._safe_execute("SELECT COUNT(*) FROM runs WHERE project_id = ?", [self.project_id], fetch='one')
        project_tasks = self._safe_execute("SELECT COUNT(*) FROM tasks WHERE project_id = ?", [self.project_id], fetch='one')
        total_projects = self._safe_execute("SELECT COUNT(*) FROM projects", fetch='one')
        total_runs = self._safe_execute("SELECT COUNT(*) FROM runs", fetch='one')

        return {
            "project_id": self.project_id,
            "project_dir": str(PROJECT_DIR),
            "db_path": str(DB_PATH),
            "db_engine": "DuckDB (Global)",
            "global_dir": str(GLOBAL_DIR),
            "ai_dir": str(AI_DIR),
            "project_runs": (project_runs[0] if project_runs else 0) or 0,
            "project_tasks": (project_tasks[0] if project_tasks else 0) or 0,
            "total_projects": (total_projects[0] if total_projects else 0) or 0,
            "total_runs": (total_runs[0] if total_runs else 0) or 0,
            "model_families": list(MODEL_FAMILIES.keys()),
            "agents_count": 33
        }

    # === GATE WORKFLOW OPERATIONS ===

    def start_gate(self, run_id: str, gate: str) -> Dict:
        """Start a gate (mark as IN_PROGRESS)"""
        now = self._now()
        self._safe_execute("UPDATE gates SET status = 'IN_PROGRESS' WHERE run_id = ? AND gate_name = ?", [run_id, gate])
        self._safe_execute("UPDATE runs SET current_gate = ?, updated_at = ? WHERE run_id = ?", [gate, now, run_id])
        self._log_event(run_id, None, "GATE_STARTED", {"gate": gate})
        return {"success": True, "gate": gate, "status": "IN_PROGRESS"}

    def complete_gate(self, run_id: str, gate: str, result: Dict = None) -> Dict:
        """Complete a gate (freeze it)"""
        now = self._now()
        self._safe_execute("UPDATE gates SET status = 'FROZEN', frozen_at = ?, frozen_hashes = ? WHERE run_id = ? AND gate_name = ?",
                        [now, json.dumps(result or {}), run_id, gate])
        # Advance to next gate if not D
        gate_order = ["A", "B", "C", "D"]
        idx = gate_order.index(gate)
        if idx < 3:
            self._safe_execute("UPDATE runs SET current_gate = ?, updated_at = ? WHERE run_id = ?", [gate_order[idx + 1], now, run_id])
        self._log_event(run_id, None, "GATE_COMPLETED", {"gate": gate, "result": result})
        return {"success": True, "gate": gate, "status": "FROZEN"}

    # === SIMPLIFIED TASK QUEUE OPERATIONS ===

    def push_task(self, task_type: str, payload: Dict, priority: int = 5) -> Dict:
        """Push a task to the queue (simplified interface)"""
        current_run = self.get_current_run()
        if not current_run:
            # Create a run if none exists
            run_result = self.create_run()
            run_id = run_result["run_id"]
        else:
            run_id = current_run["run_id"]

        task_id = f"task_{self._uuid()}"
        now = self._now()
        row = self._safe_execute("SELECT current_gate FROM runs WHERE run_id = ?", [run_id], fetch='one')
        current_gate = row[0] if row else "A"
        self._safe_execute("""
            INSERT INTO tasks (task_id, project_id, run_id, gate, task_type, role, priority, deps, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [task_id, self.project_id, run_id, current_gate, task_type, task_type, priority, json.dumps(payload), now, now])
        self._log_event(run_id, task_id, "TASK_PUSHED", {"task_type": task_type, "priority": priority})
        return {"task_id": task_id, "run_id": run_id, "status": "QUEUED"}

    def push_tasks_batch(self, tasks: list) -> Dict:
        """Push multiple tasks in parallel (batch operation for orchestrator/planners)

        Args:
            tasks: List of task dicts with keys: task_type, payload (optional), priority (optional), agent (optional)

        Returns:
            Dict with task_ids list and run_id
        """
        current_run = self.get_current_run()
        if not current_run:
            run_result = self.create_run()
            run_id = run_result["run_id"]
        else:
            run_id = current_run["run_id"]

        now = self._now()
        row = self._safe_execute("SELECT current_gate FROM runs WHERE run_id = ?", [run_id], fetch='one')
        current_gate = row[0] if row else "A"

        task_ids = []
        for task in tasks:
            task_id = f"task_{self._uuid()}"
            task_type = task.get("task_type", "unknown")
            payload = task.get("payload", {})
            priority = task.get("priority", 5)
            agent = task.get("agent")

            self._safe_execute("""
                INSERT INTO tasks (task_id, project_id, run_id, gate, task_type, role, agent, priority, deps, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [task_id, self.project_id, run_id, current_gate, task_type, task_type, agent, priority, json.dumps(payload), now, now])

            task_ids.append(task_id)
            self._log_event(run_id, task_id, "TASK_CREATED", {"task_type": task_type, "agent": agent, "priority": priority})

        self._log_event(run_id, None, "BATCH_TASKS_CREATED", {"count": len(tasks), "task_ids": task_ids})
        return {"task_ids": task_ids, "run_id": run_id, "count": len(tasks), "status": "QUEUED"}

    def get_parallel_status(self, task_ids: list) -> Dict:
        """Get status of multiple tasks (for monitoring parallel execution)

        Args:
            task_ids: List of task IDs to check

        Returns:
            Dict with status counts and individual task statuses
        """
        results = {"task_ids": task_ids, "statuses": {}, "summary": {"running": 0, "done": 0, "failed": 0, "queued": 0}}

        for task_id in task_ids:
            row = self._safe_execute(
                "SELECT status, agent, updated_at FROM tasks WHERE task_id = ?",
                [task_id], fetch='one'
            )
            if row:
                status = row[0]
                results["statuses"][task_id] = {"status": status, "agent": row[1], "updated_at": row[2]}
                if status == "RUNNING":
                    results["summary"]["running"] += 1
                elif status == "DONE":
                    results["summary"]["done"] += 1
                elif status == "FAILED":
                    results["summary"]["failed"] += 1
                else:
                    results["summary"]["queued"] += 1

        results["all_complete"] = results["summary"]["running"] == 0 and results["summary"]["queued"] == 0
        return results

    def claim_task_by_type(self, task_type: str, agent: str) -> Dict:
        """Claim the next available task of a given type"""
        current_run = self.get_current_run()
        if not current_run:
            return {"error": "No active run"}
        run_id = current_run["run_id"]

        now = self._now()
        row = self._safe_execute("""
            SELECT task_id FROM tasks
            WHERE run_id = ? AND project_id = ? AND task_type = ? AND status = 'QUEUED'
            ORDER BY priority DESC, created_at ASC LIMIT 1
        """, [run_id, self.project_id, task_type], fetch='one')
        if not row:
            return {"task_id": None, "message": "No tasks available"}
        task_id = row[0]
        self._safe_execute("UPDATE tasks SET status = 'RUNNING', agent = ?, attempts = attempts + 1, updated_at = ? WHERE task_id = ?", [agent, now, task_id])
        self._log_event(run_id, task_id, "TASK_CLAIMED", {"agent": agent})
        return {"task_id": task_id, "status": "RUNNING", "agent": agent}

    # === EVENT AND ARTIFACT LOGGING ===

    def log_event(self, run_id: str, event_type: str, agent: str, details: Dict = None) -> Dict:
        """Log an event to the event table"""
        self._log_event(run_id, None, event_type, {"agent": agent, "details": details or {}})
        return {"success": True, "event_type": event_type}

    def store_artifact(self, run_id: str, artifact_type: str, content: str, metadata: Dict = None) -> Dict:
        """Store an artifact"""
        artifact_id = f"art_{self._uuid()}"
        content_hash = self._hash(content)
        path = f".ai/artifacts/{artifact_type}/{artifact_id}"

        # Register in DB
        self.register_artifact(run_id, None, path, content_hash)

        # Try to write to file
        try:
            artifact_path = AI_DIR / "artifacts" / artifact_type
            artifact_path.mkdir(parents=True, exist_ok=True)
            with open(artifact_path / f"{artifact_id}.json", "w") as f:
                json.dump({"content": content, "metadata": metadata or {}, "hash": content_hash}, f, indent=2)
        except:
            pass

        return {"artifact_id": artifact_id, "path": path, "hash": content_hash}

    def get_run_history(self, limit: int = 10) -> Dict:
        """Get run history for current project"""
        with self._lock:
            result = self.conn.execute("""
                SELECT run_id, created_at, status, current_gate, cts_hash, updated_at
                FROM runs WHERE project_id = ?
                ORDER BY created_at DESC LIMIT ?
            """, [self.project_id, limit])
            rows = result.fetchall()

        runs = []
        for row in rows:
            runs.append({
                "run_id": row[0],
                "created_at": row[1],
                "status": row[2],
                "current_gate": row[3],
                "cts_hash": row[4],
                "updated_at": row[5]
            })
        return {"runs": runs, "count": len(runs)}

    # === LIVE MONITORING ===

    def get_live_status(self, run_id: Optional[str] = None) -> Dict:
        """Get real-time status of all running agents and tasks"""
        now = self._now()

        # Get current run if not specified
        if not run_id:
            current = self.get_current_run()
            run_id = current.get("run_id") if current else None

        if not run_id:
            return {"error": "No active run", "ts": now}

        with self._lock:
            # Get running tasks with agent info (project-filtered)
            result = self.conn.execute("""
                SELECT task_id, task_type, role, agent, status, complexity, updated_at, gate
                FROM tasks
                WHERE run_id = ? AND project_id = ? AND status = 'RUNNING'
                ORDER BY updated_at DESC
            """, [run_id, self.project_id])
            running = []
            for row in result.fetchall():
                running.append({
                    "task_id": row[0],
                    "task_type": row[1],
                    "role": row[2],
                    "agent": row[3],
                    "status": row[4],
                    "complexity": row[5],
                    "started": row[6],
                    "gate": row[7]
                })

            # Get queued tasks (project-filtered)
            result = self.conn.execute("SELECT COUNT(*) FROM tasks WHERE run_id = ? AND project_id = ? AND status = 'QUEUED'", [run_id, self.project_id])
            queued_count = result.fetchone()[0] or 0

            # Get done tasks (project-filtered)
            result = self.conn.execute("SELECT COUNT(*) FROM tasks WHERE run_id = ? AND project_id = ? AND status = 'DONE'", [run_id, self.project_id])
            done_count = result.fetchone()[0] or 0

            # Get current gate (project-filtered)
            result = self.conn.execute("SELECT current_gate, planner_index FROM runs WHERE run_id = ? AND project_id = ?", [run_id, self.project_id])
            row = result.fetchone()
            current_gate = row[0] if row else "A"
            planner_idx = row[1] if row else 0

        planners = ["planner-1", "planner-2", "planner-3", "planner-4", "planner-5"]

        # Get gate statuses
        gates = {}
        for g in ["A", "B", "C", "D"]:
            gate = self.get_gate(run_id, g)
            gates[g] = gate.get("status", "PENDING")

        return {
            "run_id": run_id,
            "ts": now,
            "current_gate": current_gate,
            "next_planner": planners[planner_idx],
            "running_agents": running,
            "running_count": len(running),
            "queued_count": queued_count,
            "done_count": done_count,
            "gates": gates
        }

    def get_recent_events(self, limit: int = 20, run_id: Optional[str] = None) -> Dict:
        """Get recent events from the event log (project-filtered)"""
        query = "SELECT event_id, run_id, task_id, ts, event_type, payload FROM events WHERE project_id = ?"
        params = [self.project_id]
        if run_id:
            query += " AND run_id = ?"
            params.append(run_id)
        query += " ORDER BY event_id DESC LIMIT ?"
        params.append(limit)

        with self._lock:
            result = self.conn.execute(query, params)
            rows = result.fetchall()

        events = []
        for row in rows:
            events.append({
                "event_id": row[0],
                "run_id": row[1],
                "task_id": row[2],
                "ts": row[3],
                "event_type": row[4],
                "payload": json.loads(row[5]) if row[5] else {}
            })

        return {"events": events, "count": len(events), "project_id": self.project_id}

    def log_agent_activity(self, run_id: str, agent: str, activity: str, details: Dict = None) -> Dict:
        """Log agent activity for real-time monitoring"""
        now = self._now()
        event_type = f"AGENT_{activity.upper()}"
        payload = {
            "agent": agent,
            "activity": activity,
            "details": details or {},
            "ts": now
        }
        self._log_event(run_id, None, event_type, payload)

        # Also write to live status file for external monitoring
        live_file = AI_DIR / "live_status.json"
        try:
            status = self.get_live_status(run_id)
            status["last_activity"] = {"agent": agent, "activity": activity, "ts": now}
            with open(live_file, "w") as f:
                json.dump(status, f, indent=2)
        except:
            pass

        return {"logged": True, "event_type": event_type, "ts": now}


# === MCP SERVER ===

# Lazy initialization - only create DB when needed
_db = None

def get_db():
    global _db
    if _db is None:
        _db = TaskBusDB()
    return _db


def handle_tool_call(tool_name: str, args: Dict) -> Any:
    db = get_db()
    handlers = {
        "create_run": lambda: db.create_run(args.get("cts_hash")),
        "get_current_run": lambda: db.get_current_run() or {"error": "No active run"},
        "complete_run": lambda: db.complete_run(args["run_id"], args.get("status", "COMPLETED")),
        "get_next_planner": lambda: db.get_next_planner(args["run_id"]),
        "get_gate": lambda: db.get_gate(args["run_id"], args["gate_name"]),
        "get_all_gates": lambda: db.get_all_gates(args["run_id"]),
        "freeze_gate": lambda: db.freeze_gate(args["run_id"], args["gate_name"], args.get("frozen_hashes", {}), args.get("validated_by", [])),
        "can_proceed_to_gate": lambda: {"can_proceed": db.can_proceed_to_gate(args["run_id"], args["gate_name"])[0], "reason": db.can_proceed_to_gate(args["run_id"], args["gate_name"])[1]},
        "is_agent_allowed": lambda: {"allowed": db.is_agent_allowed(args["run_id"], args["agent"])[0], "reason": db.is_agent_allowed(args["run_id"], args["agent"])[1]},
        "is_coding_allowed": lambda: {"allowed": db.is_coding_allowed(args["agent"])[0], "reason": db.is_coding_allowed(args["agent"])[1]},
        "create_task": lambda: db.create_task(args["run_id"], args["task_type"], args["role"], args.get("priority", 5), args.get("complexity", 3), args.get("deps"), args.get("timeout_ms", 60000)),
        "claim_task": lambda: db.claim_task(args["task_id"], args["holder"]),
        "complete_task": lambda: db.complete_task(args["task_id"], args.get("status", "DONE"), args.get("artifact_writes"), args.get("error")),
        "retry_task": lambda: db.retry_task(args["task_id"], args["error"]),
        "get_next_task": lambda: db.get_next_task(args["run_id"], args.get("role")),
        "list_tasks": lambda: db.list_tasks(args["run_id"], args.get("status")),
        "register_artifact": lambda: db.register_artifact(args["run_id"], args.get("task_id"), args["path"], args["content_hash"]),
        "get_artifact": lambda: db.get_artifact(args["path"]),
        "verify_artifact": lambda: db.verify_artifact(args["path"], args["expected_hash"]),
        "acquire_lock": lambda: db.acquire_lock(args["lock_key"], args["holder"], args.get("ttl_seconds", 300)),
        "release_lock": lambda: db.release_lock(args["lock_key"], args["holder"]),
        "validate_cross_model": lambda: db.validate_cross_model(args["coder"], args["validator"]),
        "get_valid_validators": lambda: {"validators": db.get_valid_validators(args["coder"])},
        "get_recommended_coder": lambda: db.get_recommended_coder(args.get("complexity", 3)),
        "track_cost": lambda: db.track_cost(args["run_id"], args["agent"], args["model"], args.get("tokens_in", 0), args.get("tokens_out", 0), args.get("cost_usd", 0.0)),
        "get_cost_summary": lambda: db.get_cost_summary(args["run_id"]),
        "get_stats": lambda: db.get_stats(args["run_id"]),
        "get_project_info": lambda: db.get_project_info(),
        "get_live_status": lambda: db.get_live_status(args.get("run_id")),
        "get_recent_events": lambda: db.get_recent_events(args.get("limit", 20), args.get("run_id")),
        "log_agent_activity": lambda: db.log_agent_activity(args["run_id"], args["agent"], args["activity"], args.get("details")),
        # New workflow tools
        "start_gate": lambda: db.start_gate(args["run_id"], args["gate"]),
        "complete_gate": lambda: db.complete_gate(args["run_id"], args["gate"], args.get("result")),
        "push_task": lambda: db.push_task(args["task_type"], args.get("payload", {}), args.get("priority", 5)),
        "push_tasks_batch": lambda: db.push_tasks_batch(args["tasks"]),
        "get_parallel_status": lambda: db.get_parallel_status(args["task_ids"]),
        "claim_task_by_type": lambda: db.claim_task_by_type(args["task_type"], args["agent"]),
        "log_event": lambda: db.log_event(args["run_id"], args["event_type"], args["agent"], args.get("details")),
        "store_artifact": lambda: db.store_artifact(args["run_id"], args["artifact_type"], args["content"], args.get("metadata")),
        "get_run_history": lambda: db.get_run_history(args.get("limit", 10))
    }
    return handlers[tool_name]() if tool_name in handlers else {"error": f"Unknown tool: {tool_name}"}


TOOLS_LIST = [
    {"name": "create_run", "description": "Create new run with gates A-D", "inputSchema": {"type": "object", "properties": {"cts_hash": {"type": "string"}}}},
    {"name": "get_current_run", "description": "Get current active run", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "complete_run", "description": "Complete a run", "inputSchema": {"type": "object", "properties": {"run_id": {"type": "string"}, "status": {"type": "string"}}, "required": ["run_id"]}},
    {"name": "get_next_planner", "description": "Get next planner in round-robin", "inputSchema": {"type": "object", "properties": {"run_id": {"type": "string"}}, "required": ["run_id"]}},
    {"name": "get_gate", "description": "Get gate status", "inputSchema": {"type": "object", "properties": {"run_id": {"type": "string"}, "gate_name": {"type": "string", "enum": ["A", "B", "C", "D"]}}, "required": ["run_id", "gate_name"]}},
    {"name": "get_all_gates", "description": "Get all gates status", "inputSchema": {"type": "object", "properties": {"run_id": {"type": "string"}}, "required": ["run_id"]}},
    {"name": "freeze_gate", "description": "Freeze gate after validation", "inputSchema": {"type": "object", "properties": {"run_id": {"type": "string"}, "gate_name": {"type": "string"}, "frozen_hashes": {"type": "object"}, "validated_by": {"type": "array", "items": {"type": "string"}}}, "required": ["run_id", "gate_name"]}},
    {"name": "can_proceed_to_gate", "description": "Check if can proceed to gate", "inputSchema": {"type": "object", "properties": {"run_id": {"type": "string"}, "gate_name": {"type": "string"}}, "required": ["run_id", "gate_name"]}},
    {"name": "is_agent_allowed", "description": "Check if agent allowed at current gate", "inputSchema": {"type": "object", "properties": {"run_id": {"type": "string"}, "agent": {"type": "string"}}, "required": ["run_id", "agent"]}},
    {"name": "is_coding_allowed", "description": "Check if agent can write code", "inputSchema": {"type": "object", "properties": {"agent": {"type": "string"}}, "required": ["agent"]}},
    {"name": "create_task", "description": "Create task with complexity", "inputSchema": {"type": "object", "properties": {"run_id": {"type": "string"}, "task_type": {"type": "string"}, "role": {"type": "string"}, "priority": {"type": "integer"}, "complexity": {"type": "integer"}}, "required": ["run_id", "task_type", "role"]}},
    {"name": "claim_task", "description": "Claim task for execution", "inputSchema": {"type": "object", "properties": {"task_id": {"type": "string"}, "holder": {"type": "string"}}, "required": ["task_id", "holder"]}},
    {"name": "complete_task", "description": "Complete task", "inputSchema": {"type": "object", "properties": {"task_id": {"type": "string"}, "status": {"type": "string"}}, "required": ["task_id"]}},
    {"name": "retry_task", "description": "Retry failed task", "inputSchema": {"type": "object", "properties": {"task_id": {"type": "string"}, "error": {"type": "string"}}, "required": ["task_id", "error"]}},
    {"name": "get_next_task", "description": "Get next queued task", "inputSchema": {"type": "object", "properties": {"run_id": {"type": "string"}, "role": {"type": "string"}}, "required": ["run_id"]}},
    {"name": "list_tasks", "description": "List tasks", "inputSchema": {"type": "object", "properties": {"run_id": {"type": "string"}, "status": {"type": "string"}}, "required": ["run_id"]}},
    {"name": "register_artifact", "description": "Register artifact with hash", "inputSchema": {"type": "object", "properties": {"run_id": {"type": "string"}, "path": {"type": "string"}, "content_hash": {"type": "string"}}, "required": ["run_id", "path", "content_hash"]}},
    {"name": "get_artifact", "description": "Get artifact by path", "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "verify_artifact", "description": "Verify artifact hash", "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}, "expected_hash": {"type": "string"}}, "required": ["path", "expected_hash"]}},
    {"name": "acquire_lock", "description": "Acquire lock", "inputSchema": {"type": "object", "properties": {"lock_key": {"type": "string"}, "holder": {"type": "string"}}, "required": ["lock_key", "holder"]}},
    {"name": "release_lock", "description": "Release lock", "inputSchema": {"type": "object", "properties": {"lock_key": {"type": "string"}, "holder": {"type": "string"}}, "required": ["lock_key", "holder"]}},
    {"name": "validate_cross_model", "description": "Validate coder/validator are different families", "inputSchema": {"type": "object", "properties": {"coder": {"type": "string"}, "validator": {"type": "string"}}, "required": ["coder", "validator"]}},
    {"name": "get_valid_validators", "description": "Get valid validators for a coder", "inputSchema": {"type": "object", "properties": {"coder": {"type": "string"}}, "required": ["coder"]}},
    {"name": "get_recommended_coder", "description": "Get recommended coder for complexity", "inputSchema": {"type": "object", "properties": {"complexity": {"type": "integer"}}, "required": ["complexity"]}},
    {"name": "track_cost", "description": "Track API cost", "inputSchema": {"type": "object", "properties": {"run_id": {"type": "string"}, "agent": {"type": "string"}, "model": {"type": "string"}}, "required": ["run_id", "agent", "model"]}},
    {"name": "get_cost_summary", "description": "Get cost summary for run", "inputSchema": {"type": "object", "properties": {"run_id": {"type": "string"}}, "required": ["run_id"]}},
    {"name": "get_stats", "description": "Get run statistics", "inputSchema": {"type": "object", "properties": {"run_id": {"type": "string"}}, "required": ["run_id"]}},
    {"name": "get_project_info", "description": "Get project info", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "get_live_status", "description": "Get real-time status of running agents and tasks", "inputSchema": {"type": "object", "properties": {"run_id": {"type": "string"}}}},
    {"name": "get_recent_events", "description": "Get recent events from event log", "inputSchema": {"type": "object", "properties": {"limit": {"type": "integer"}, "run_id": {"type": "string"}}}},
    {"name": "log_agent_activity", "description": "Log agent activity (START/PROGRESS/DONE/ERROR)", "inputSchema": {"type": "object", "properties": {"run_id": {"type": "string"}, "agent": {"type": "string"}, "activity": {"type": "string"}, "details": {"type": "object"}}, "required": ["run_id", "agent", "activity"]}},
    # New workflow tools
    {"name": "start_gate", "description": "Start a gate (mark as IN_PROGRESS)", "inputSchema": {"type": "object", "properties": {"run_id": {"type": "string"}, "gate": {"type": "string", "enum": ["A", "B", "C", "D"]}}, "required": ["run_id", "gate"]}},
    {"name": "complete_gate", "description": "Complete a gate (freeze it)", "inputSchema": {"type": "object", "properties": {"run_id": {"type": "string"}, "gate": {"type": "string", "enum": ["A", "B", "C", "D"]}, "result": {"type": "object"}}, "required": ["run_id", "gate"]}},
    {"name": "push_task", "description": "Push a task to the queue (simplified)", "inputSchema": {"type": "object", "properties": {"task_type": {"type": "string"}, "payload": {"type": "object"}, "priority": {"type": "integer"}}, "required": ["task_type"]}},
    {"name": "push_tasks_batch", "description": "Push multiple tasks in parallel (for orchestrator/planners)", "inputSchema": {"type": "object", "properties": {"tasks": {"type": "array", "items": {"type": "object", "properties": {"task_type": {"type": "string"}, "payload": {"type": "object"}, "priority": {"type": "integer"}, "agent": {"type": "string"}}}}}, "required": ["tasks"]}},
    {"name": "get_parallel_status", "description": "Get status of multiple tasks (for monitoring parallel execution)", "inputSchema": {"type": "object", "properties": {"task_ids": {"type": "array", "items": {"type": "string"}}}, "required": ["task_ids"]}},
    {"name": "claim_task_by_type", "description": "Claim next task of given type", "inputSchema": {"type": "object", "properties": {"task_type": {"type": "string"}, "agent": {"type": "string"}}, "required": ["task_type", "agent"]}},
    {"name": "log_event", "description": "Log an event", "inputSchema": {"type": "object", "properties": {"run_id": {"type": "string"}, "event_type": {"type": "string"}, "agent": {"type": "string"}, "details": {"type": "object"}}, "required": ["run_id", "event_type", "agent"]}},
    {"name": "store_artifact", "description": "Store an artifact", "inputSchema": {"type": "object", "properties": {"run_id": {"type": "string"}, "artifact_type": {"type": "string"}, "content": {"type": "string"}, "metadata": {"type": "object"}}, "required": ["run_id", "artifact_type", "content"]}},
    {"name": "get_run_history", "description": "Get run history for current project", "inputSchema": {"type": "object", "properties": {"limit": {"type": "integer"}}}}
]


def handle_request(request: Dict) -> Optional[Dict]:
    method = request.get("method", "")
    params = request.get("params", {})
    req_id = request.get("id")

    try:
        if method == "initialize":
            return {"jsonrpc": "2.0", "id": req_id, "result": {"protocolVersion": "2024-11-05", "serverInfo": {"name": "duckdb-task-bus", "version": "1.0.0"}, "capabilities": {"tools": {}}}}
        elif method == "tools/list":
            return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS_LIST}}
        elif method == "tools/call":
            result = handle_tool_call(params.get("name"), params.get("arguments", {}))
            return {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}}
        elif method == "notifications/initialized":
            return None
        else:
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Unknown method: {method}"}}
    except Exception as e:
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32000, "message": str(e)}}


def main():
    """MCP server main loop - reads JSON-RPC from stdin, writes to stdout"""
    import traceback

    # Ensure stdout is unbuffered for MCP protocol
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)

    # Log startup to stderr (doesn't interfere with MCP protocol on stdout)
    log_file = AI_DIR / "logs" / "duckdb_mcp.log"
    try:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(log_file, "a") as f:
            f.write(f"[{datetime.now(timezone.utc).isoformat()}] MCP Server starting...\n")
            f.write(f"[DuckDB] Project: {PROJECT_DIR}\n")
            f.write(f"[DuckDB] Database: {DB_PATH}\n")
    except:
        pass

    # Pre-initialize DB on startup to avoid lazy init delays
    try:
        get_db()
        sys.stderr.write(f"[DuckDB MCP] Ready - DB at {DB_PATH}\n")
        sys.stderr.flush()
    except Exception as e:
        sys.stderr.write(f"[DuckDB MCP] Init warning: {e}\n")
        sys.stderr.flush()

    # Main request loop
    try:
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
                # Log error to file
                try:
                    with open(log_file, "a") as f:
                        f.write(f"[ERROR] {e}\n{traceback.format_exc()}\n")
                except:
                    pass
                print(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32000, "message": str(e)}}), flush=True)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        # Fatal error - log and exit
        try:
            with open(log_file, "a") as f:
                f.write(f"[FATAL] {e}\n{traceback.format_exc()}\n")
        except:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
