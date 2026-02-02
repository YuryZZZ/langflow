#!/usr/bin/env python3
"""OpenCode project launcher (Python replacement for oc.bat).

Drop this file into ANY project folder and run:
  python oc.py

What it does:
- Finds your global OpenCode home (e.g. %USERPROFILE%\\.config\\opencode)
- Replaces project files with global ones (with backups)
- Creates required .ai/ structure + seed persistence files
- Runs MCP preflight using global mcp_preflight.py
- Starts TaskBus workers + progress watchdog (background)
- Starts OpenCode CLI (foreground)
"""

from __future__ import annotations

import argparse
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


def _is_windows() -> bool:
    return os.name == "nt"


def _no_window_flags() -> Tuple[int, Any]:
    """Return (creationflags, startupinfo) to hide console windows on Windows."""
    if not _is_windows():
        return 0, None
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = 0  # SW_HIDE
    return subprocess.CREATE_NO_WINDOW, si


def _now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _mkdir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _log_setup(project_root: Path) -> Path:
    logs_dir = project_root / ".ai" / "logs"
    _mkdir(logs_dir)
    return logs_dir / "oc_launcher.log"


def _log(log_path: Optional[Path], msg: str) -> None:
    line = msg.rstrip("\n")
    print(line, flush=True)
    if not log_path:
        return
    try:
        _mkdir(log_path.parent)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def _pids_dir(project_root: Path) -> Path:
    return project_root / ".ai" / "pids"


def _pid_file(project_root: Path, name: str) -> Path:
    return _pids_dir(project_root) / f"{name}.json"


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if _is_windows():
        try:
            # Use CREATE_NO_WINDOW to prevent CMD flash
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = 0  # SW_HIDE
            r = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW,
                startupinfo=si,
            )
            out = (r.stdout or "") + (r.stderr or "")
            return str(pid) in out
        except Exception:
            return False
    try:
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def _count_opencode_processes() -> int:
    """Count running OpenCode-related processes (python, node) to prevent runaway."""
    if not _is_windows():
        return 0
    try:
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 0
        # Count python processes with opencode-related scripts
        r = subprocess.run(
            'wmic process where "name=\'python.exe\'" get commandline 2>nul | find /c "mcp"',
            shell=True, capture_output=True, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW, startupinfo=si,
        )
        mcp_count = int(r.stdout.strip() or "0")
        # Count node processes (OpenCode CLI spawns these)
        r2 = subprocess.run(
            'tasklist /FI "IMAGENAME eq node.exe" 2>nul | find /c "node"',
            shell=True, capture_output=True, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW, startupinfo=si,
        )
        node_count = int(r2.stdout.strip() or "0")
        return mcp_count + node_count
    except Exception:
        return 0


# Maximum allowed OpenCode processes before refusing to spawn more
MAX_OPENCODE_PROCESSES = 50


def _write_pid(
    project_root: Path,
    name: str,
    pid: int,
    cmd: Sequence[str],
    cwd: Path,
    managed: bool = True,
) -> None:
    try:
        d = _pids_dir(project_root)
        d.mkdir(parents=True, exist_ok=True)
        p = _pid_file(project_root, name)
        obj = {
            "name": name,
            "pid": int(pid),
            "managed": bool(managed),
            "cmd": [str(x) for x in cmd],
            "cwd": str(cwd),
            "written_at": _now_stamp(),
            "restart_count": 0,
        }
        tmp = p.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(obj, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
        )
        os.replace(tmp, p)
    except Exception:
        pass


def _load_pid(project_root: Path, name: str) -> Optional[Dict[str, Any]]:
    try:
        p = _pid_file(project_root, name)
        if not p.exists():
            return None
        obj = json.loads(p.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def _terminate_pid(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        if _is_windows():
            # Use CREATE_NO_WINDOW to prevent CMD flash
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = 0  # SW_HIDE
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
                startupinfo=si,
            )
            return True
        os.kill(pid, 15)
        return True
    except Exception:
        return False


def _tail_logs_loop(project_root: Path) -> int:
    """Tail key logs/events forever (until Ctrl+C)."""
    paths = [
        project_root / ".ai" / "logs" / "oc_launcher.log",
        project_root / ".ai" / "logs" / "taskbus_worker_stdout.log",
        project_root / ".ai" / "logs" / "taskbus_worker_stderr.log",
        project_root / ".ai" / "logs" / "progress_watchdog_stdout.log",
        project_root / ".ai" / "logs" / "progress_watchdog_stderr.log",
        project_root / ".ai" / "logs" / "supervisor_stdout.log",
        project_root / ".ai" / "logs" / "supervisor_stderr.log",
        project_root / ".ai" / "artifacts" / "task_events.ndjson",
    ]

    offsets: Dict[str, int] = {}

    def _read_new(p: Path) -> List[str]:
        key = str(p)
        try:
            if not p.exists():
                return []
            data = p.read_text(encoding="utf-8", errors="replace")
            old = offsets.get(key, 0)
            if old < 0:
                old = 0
            if old > len(data):
                old = 0
            offsets[key] = len(data)
            chunk = data[old:]
            if not chunk:
                return []
            return chunk.splitlines()
        except Exception:
            return []

    print("[LOG] Tailing logs. Ctrl+C to stop.")
    while True:
        any_line = False
        for p in paths:
            lines = _read_new(p)
            if not lines:
                continue
            any_line = True
            prefix = p.name
            for line in lines:
                print(f"[{prefix}] {line}")
        if not any_line:
            time.sleep(0.25)


def _maybe_start_log_window(
    log_path: Optional[Path], project_root: Path, env: Dict[str, str]
) -> None:
    """Start a dedicated log tail window (Windows)."""
    if not _is_windows():
        return

    # Hard policy: never spawn extra Windows console windows.
    # Use the regular logs under .ai/logs/ instead.
    _log(log_path, "[INFO] log tail window disabled (no extra windows policy)")
    return

    # Avoid recursion if we are the tail process.
    if env.get("OPENCODE_LOG_TAIL") == "1":
        return

    # If already running, skip.
    st = _load_pid(project_root, "log_tail")
    pid = int(st.get("pid") or 0) if st else 0
    if st and _pid_alive(pid):
        _log(log_path, f"[OK] log tail already running pid={pid}")
        return

    try:
        cmd = [
            sys.executable,
            str(Path(__file__).resolve()),
            "--tail-logs",
            "--project",
            str(project_root),
        ]
        env2 = env.copy()
        env2["OPENCODE_LOG_TAIL"] = "1"

        p = subprocess.Popen(
            cmd,
            cwd=str(project_root),
            env=env2,
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
        _write_pid(project_root, "log_tail", int(p.pid), cmd, project_root)
        _log(log_path, f"[START] log tail window pid={p.pid}")
    except Exception as e:
        _log(log_path, f"[WARN] failed to start log tail window: {e}")


def _find_global_dir(explicit: Optional[str]) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()

    env = os.environ.get("OPENCODE_GLOBAL_DIR")
    if env:
        return Path(env).expanduser().resolve()

    home = Path.home()
    userprofile = os.environ.get("USERPROFILE") or ""

    # Canonical global locations - check these FIRST (before script location)
    # This ensures project copies of oc.py always find the real global dir
    canonical = [
        home / ".config" / "opencode",
        home / ".opencode",
        Path(userprofile) / ".config" / "opencode" if userprofile else None,
        Path(userprofile) / ".opencode" if userprofile else None,
    ]

    for c in canonical:
        if c and c.exists() and (c / "opencode.json").exists():
            return c

    # Fallback: if script lives inside a directory with opencode.json, use that
    # (only if canonical locations don't exist)
    try:
        here = Path(__file__).resolve().parent
        if (here / "opencode.json").exists():
            return here
    except Exception:
        pass

    raise FileNotFoundError(
        "Global opencode.json not found. Set OPENCODE_GLOBAL_DIR or pass --global."
    )


def _load_env_file(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    out: Dict[str, str] = {}
    for raw in _read_text(path).splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip()
        if not k:
            continue
        if (len(v) >= 2) and ((v[0] == v[-1]) and v[0] in ('"', "'")):
            v = v[1:-1]
        out[k] = v
    return out


def _merged_env(global_dir: Path, project_root: Path) -> Dict[str, str]:
    env = os.environ.copy()
    env.update(_load_env_file(global_dir / ".env"))
    # Optional per-project overrides.
    env.update(_load_env_file(project_root / ".env"))
    env["OPENCODE_PROJECT_ROOT"] = str(project_root)
    env["OPENCODE_GLOBAL_DIR"] = str(global_dir)
    env.setdefault("PYTHONIOENCODING", "utf-8")

    # Ensure any MCP entries that invoke just `python` resolve to the same
    # interpreter running this launcher (opencode.json uses `python -u ...`).
    try:
        py_dir = str(Path(sys.executable).resolve().parent)
        path = env.get("PATH", "")
        parts = [p for p in path.split(os.pathsep) if p]
        if py_dir and (py_dir not in parts):
            env["PATH"] = py_dir + os.pathsep + path
    except Exception:
        pass

    # Ensure npm global shims are on PATH (Windows).
    if _is_windows():
        try:
            appdata = env.get("APPDATA") or os.environ.get("APPDATA")
            if appdata:
                npm_bin = str(Path(appdata) / "npm")
                path = env.get("PATH", "")
                parts = [p for p in path.split(os.pathsep) if p]
                if npm_bin and (npm_bin not in parts):
                    env["PATH"] = npm_bin + os.pathsep + path
        except Exception:
            pass

    return env


def _run_cmd(
    cmd: Sequence[str],
    *,
    cwd: Optional[Path] = None,
    env: Optional[Dict[str, str]] = None,
    timeout_s: int = 120,
) -> Tuple[int, str]:
    try:
        flags, si = _no_window_flags()
        p = subprocess.run(
            list(cmd),
            cwd=str(cwd) if cwd else None,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_s,
            creationflags=flags,
            startupinfo=si,
        )
        out = (p.stdout or "") + (p.stderr or "")
        return int(p.returncode), out.strip()
    except Exception as e:
        return 1, str(e)


def _run_cmd_stream(
    log_path: Optional[Path],
    cmd: Sequence[str],
    *,
    cwd: Optional[Path] = None,
    env: Optional[Dict[str, str]] = None,
    timeout_s: int = 600,
    prefix: str = "",
) -> Tuple[int, str]:
    """Run a command and stream stdout/stderr live (to console + launcher log)."""
    start = time.time()
    tail: List[str] = []

    def _push(line: str) -> None:
        nonlocal tail
        s = line.rstrip("\n")
        if prefix:
            s = prefix + s
        _log(log_path, s)
        tail.append(s)
        if len(tail) > 30:
            tail = tail[-30:]

    try:
        flags, si = _no_window_flags()
        proc = subprocess.Popen(
            list(cmd),
            cwd=str(cwd) if cwd else None,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=flags,
            startupinfo=si,
        )
    except Exception as e:
        return 1, str(e)

    q: "queue.Queue[Tuple[str, str]]" = queue.Queue()

    def _reader(which: str, stream) -> None:
        try:
            for line in stream:
                q.put((which, line))
        except Exception:
            pass

    if proc.stdout is not None:
        threading.Thread(
            target=_reader, args=("stdout", proc.stdout), daemon=True
        ).start()
    if proc.stderr is not None:
        threading.Thread(
            target=_reader, args=("stderr", proc.stderr), daemon=True
        ).start()

    try:
        while True:
            # timeout handling
            if timeout_s and (time.time() - start) > timeout_s:
                try:
                    proc.terminate()
                except Exception:
                    pass
                try:
                    proc.kill()
                except Exception:
                    pass
                return 124, "timeout"

            try:
                _which, line = q.get(timeout=0.1)
                if line:
                    _push(line)
            except Exception:
                pass

            rc = proc.poll()
            if rc is not None:
                # Drain any remaining output
                drain_deadline = time.time() + 1.0
                while time.time() < drain_deadline:
                    try:
                        _which, line = q.get(timeout=0.05)
                        if line:
                            _push(line)
                    except Exception:
                        break
                return int(rc), "\n".join(tail).strip()
    finally:
        try:
            if proc.stdout:
                proc.stdout.close()
        except Exception:
            pass
        try:
            if proc.stderr:
                proc.stderr.close()
        except Exception:
            pass


def _in_venv() -> bool:
    try:
        return hasattr(sys, "base_prefix") and sys.prefix != sys.base_prefix
    except Exception:
        return False


def _ensure_python_package(
    log_path: Optional[Path],
    *,
    module: str,
    pip_package: str,
    env: Dict[str, str],
) -> bool:
    """Best-effort install of a Python dependency into the current interpreter."""
    try:
        __import__(module)
        return True
    except Exception:
        pass

    _log(
        log_path,
        f"[FIX] missing python module '{module}' -> installing '{pip_package}'",
    )

    # ensurepip (helps on some minimal installs)
    rc, out = _run_cmd(
        [sys.executable, "-m", "pip", "--version"], env=env, timeout_s=60
    )
    if rc != 0:
        _log(log_path, f"[FIX] pip not available; trying ensurepip ({out})")
        _run_cmd(
            [sys.executable, "-m", "ensurepip", "--upgrade"], env=env, timeout_s=120
        )

    install_cmd = [sys.executable, "-m", "pip", "install", "--upgrade"]
    if not _in_venv():
        install_cmd.append("--user")
    install_cmd.append(pip_package)

    rc, out = _run_cmd(install_cmd, env=env, timeout_s=600)
    if rc != 0:
        _log(log_path, f"[ERROR] pip install failed for {pip_package}: {out}")
        return False

    try:
        __import__(module)
        _log(log_path, f"[OK] installed {pip_package}")
        return True
    except Exception as e:
        _log(log_path, f"[ERROR] installed {pip_package} but import still fails: {e}")
        return False


def _taskbus_pg_env_from_config(project_root: Path) -> Dict[str, str]:
    cfg_path = project_root / "opencode.json"
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    except Exception:
        cfg = {}
    mcp = cfg.get("mcp") if isinstance(cfg, dict) else None
    tb = mcp.get("taskbus") if isinstance(mcp, dict) else None
    env = tb.get("environment") if isinstance(tb, dict) else None
    return (
        {str(k): str(v) for k, v in (env or {}).items()}
        if isinstance(env, dict)
        else {}
    )


def _get_postgres_connection_params(pg_env: Dict[str, str], env: Dict[str, str]) -> Dict[str, Any]:
    """Get PostgreSQL connection parameters, prioritizing connection string."""
    # Priority 1: POSTGRES_CONNECTION_STRING from environment (cloud databases)
    conn_str = env.get("POSTGRES_CONNECTION_STRING", "") or pg_env.get("POSTGRES_CONNECTION_STRING", "")
    if conn_str:
        return {"dsn": conn_str}

    # Priority 2: Individual parameters
    return {
        "host": pg_env.get("POSTGRES_HOST") or env.get("POSTGRES_HOST") or "localhost",
        "port": int(pg_env.get("POSTGRES_PORT") or env.get("POSTGRES_PORT") or "5432"),
        "dbname": pg_env.get("POSTGRES_DB") or env.get("POSTGRES_DB") or "opencode_taskbus",
        "user": pg_env.get("POSTGRES_USER") or env.get("POSTGRES_USER") or "postgres",
        "password": pg_env.get("POSTGRES_PASSWORD") or env.get("POSTGRES_PASSWORD") or "postgres",
    }


def _check_postgres_connectable(
    *,
    pg_env: Dict[str, str],
    env: Dict[str, str],
    timeout_s: int = 3,
) -> Tuple[bool, str]:
    try:
        import psycopg2  # type: ignore

        params = _get_postgres_connection_params(pg_env, env)
        params["connect_timeout"] = timeout_s

        conn = psycopg2.connect(**params)

        # Check if database is in recovery mode
        cur = conn.cursor()
        cur.execute("SELECT pg_is_in_recovery()")
        in_recovery = cur.fetchone()[0]
        cur.close()
        conn.close()

        if in_recovery:
            return False, "database is in recovery mode"

        return True, "ok"
    except Exception as e:
        return False, str(e)


def _wait_for_postgres_ready(
    log_path: Optional[Path],
    pg_env: Dict[str, str],
    env: Dict[str, str],
    max_wait_s: int = 30,
) -> bool:
    """Wait for PostgreSQL to be fully ready (not in recovery mode)."""
    import time as _time
    deadline = _time.time() + max_wait_s
    attempt = 0
    while _time.time() < deadline:
        attempt += 1
        ok, err = _check_postgres_connectable(pg_env=pg_env, env=env, timeout_s=3)
        if ok:
            return True
        if "recovery" in err.lower():
            if attempt == 1:
                _log(log_path, "[WAIT] PostgreSQL is in recovery mode, waiting...")
            _time.sleep(2)
            continue
        if "connection refused" in err.lower() or "could not connect" in err.lower():
            _time.sleep(1)
            continue
        # Other errors - might not recover
        _time.sleep(1)
    return False


def _maybe_create_postgres_db(
    log_path: Optional[Path], *, pg_env: Dict[str, str], env: Dict[str, str]
) -> bool:
    """If postgres is reachable but the target DB doesn't exist, try to create it."""
    try:
        import psycopg2  # type: ignore

        # Check if using connection string (cloud) - can't create DB on cloud
        conn_str = env.get("POSTGRES_CONNECTION_STRING", "") or pg_env.get("POSTGRES_CONNECTION_STRING", "")
        if conn_str:
            _log(log_path, "[INFO] Using cloud connection string - skipping DB creation")
            return True

        host = pg_env.get("POSTGRES_HOST") or env.get("POSTGRES_HOST") or "localhost"
        port = int(pg_env.get("POSTGRES_PORT") or env.get("POSTGRES_PORT") or "5432")
        db = pg_env.get("POSTGRES_DB") or env.get("POSTGRES_DB") or "opencode_taskbus"
        user = pg_env.get("POSTGRES_USER") or env.get("POSTGRES_USER") or "postgres"
        pwd = pg_env.get("POSTGRES_PASSWORD") or env.get("POSTGRES_PASSWORD") or "postgres"

        conn = psycopg2.connect(
            host=host,
            port=port,
            dbname="postgres",
            user=user,
            password=pwd,
            connect_timeout=5,
        )
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db,))
        exists = cur.fetchone() is not None
        if not exists:
            cur.execute(f'CREATE DATABASE "{db}"')
            _log(log_path, f"[FIX] created postgres database '{db}'")
        cur.close()
        conn.close()
        return True
    except Exception as e:
        _log(log_path, f"[WARN] could not auto-create postgres DB: {e}")
        return False


def _ensure_postgres_tables(
    log_path: Optional[Path], *, pg_env: Dict[str, str], env: Dict[str, str], global_dir: Path
) -> bool:
    """Ensure TaskBus tables exist in the database."""
    try:
        import psycopg2  # type: ignore

        params = _get_postgres_connection_params(pg_env, env)
        params["connect_timeout"] = 10
        conn = psycopg2.connect(**params)
        conn.autocommit = True
        cur = conn.cursor()

        # Check if runs table exists (primary TaskBus table)
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'runs'
            )
        """)
        tables_exist = cur.fetchone()[0]

        if not tables_exist:
            _log(log_path, "[FIX] TaskBus tables missing, initializing schema...")
            sql_file = global_dir / "parl_tables.sql"
            if sql_file.exists():
                sql = sql_file.read_text(encoding="utf-8")
                cur.execute(sql)
                _log(log_path, "[OK] TaskBus tables created from parl_tables.sql")
            else:
                # Minimal schema if SQL file not found
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS runs (
                        id TEXT PRIMARY KEY,
                        project_id TEXT,
                        status TEXT DEFAULT 'running',
                        current_gate TEXT DEFAULT 'A',
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        completed_at TIMESTAMPTZ
                    );
                    CREATE TABLE IF NOT EXISTS tasks (
                        id TEXT PRIMARY KEY,
                        run_id TEXT REFERENCES runs(id),
                        gate TEXT,
                        task_type TEXT,
                        description TEXT,
                        status TEXT DEFAULT 'queued',
                        assigned_to TEXT,
                        priority INTEGER DEFAULT 5,
                        progress_pct INTEGER DEFAULT 0,
                        result JSONB,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        started_at TIMESTAMPTZ,
                        completed_at TIMESTAMPTZ
                    );
                    CREATE TABLE IF NOT EXISTS events (
                        id SERIAL PRIMARY KEY,
                        run_id TEXT,
                        task_id TEXT,
                        event_type TEXT,
                        agent TEXT,
                        message TEXT,
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    );
                    CREATE INDEX IF NOT EXISTS idx_tasks_run_status ON tasks(run_id, status);
                    CREATE INDEX IF NOT EXISTS idx_events_run ON events(run_id);
                """)
                _log(log_path, "[OK] TaskBus tables created (minimal schema)")
        else:
            _log(log_path, "[OK] TaskBus tables exist")

        cur.close()
        conn.close()
        return True
    except Exception as e:
        _log(log_path, f"[WARN] could not ensure TaskBus tables: {e}")
        return False


def _ensure_opencode_cli(log_path: Optional[Path], env: Dict[str, str]) -> bool:
    """Ensure the actual OpenCode CLI binary/shim is installed (best-effort)."""
    oc_cmd, label = _resolve_opencode_cmd()
    if oc_cmd:
        _log(log_path, f"[OK] OpenCode CLI present ({label})")
        return True

    npm = shutil.which("npm") or shutil.which("npm.cmd") or shutil.which("npm.exe")
    if not npm:
        _log(
            log_path,
            "[WARN] OpenCode CLI missing and npm not found. Install Node.js + npm.",
        )
        return False

    _log(log_path, "[FIX] installing OpenCode CLI via npm (opencode-ai@latest)")
    rc, out = _run_cmd([npm, "i", "-g", "opencode-ai@latest"], env=env, timeout_s=900)
    if rc != 0:
        _log(log_path, f"[ERROR] npm install failed: {out}")
        return False

    oc_cmd, label = _resolve_opencode_cmd()
    if oc_cmd:
        _log(log_path, f"[OK] OpenCode CLI installed ({label})")
        return True

    _log(
        log_path,
        "[ERROR] npm install succeeded but OpenCode CLI still not found on PATH",
    )
    return False


def _maybe_disable_apify_if_unconfigured(
    log_path: Optional[Path], project_root: Path, env: Dict[str, str]
) -> None:
    """Disable the apify MCP if no token is configured.

    apify server hard-fails when APIFY_TOKEN is missing, and mcp_preflight treats
    enabled MCP failures as blocking. This makes fresh installs exit before the
    CLI launches.
    """
    try:
        token = (env.get("APIFY_TOKEN") or os.environ.get("APIFY_TOKEN") or "").strip()
        auth_file = Path.home() / ".apify" / "auth.json"
        has_token = bool(token) or auth_file.exists()

        cfg_path = project_root / "opencode.json"
        if not cfg_path.exists():
            return
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        if not isinstance(cfg, dict):
            return
        mcp = cfg.get("mcp")
        if not isinstance(mcp, dict):
            return
        ap = mcp.get("apify")
        if not isinstance(ap, dict):
            return
        if not ap.get("enabled"):
            return
        if has_token:
            return

        # Backup current config
        try:
            bdir = project_root / ".ai" / "backups" / _now_stamp()
            bdir.mkdir(parents=True, exist_ok=True)
            (bdir / "opencode.json").write_text(
                cfg_path.read_text(encoding="utf-8", errors="replace"), encoding="utf-8"
            )
        except Exception:
            pass

        ap["enabled"] = False
        mcp["apify"] = ap
        cfg["mcp"] = mcp
        cfg_path.write_text(
            json.dumps(cfg, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
        )
        _log(
            log_path,
            "[FIX] disabled mcp.apify (APIFY_TOKEN not set). Set APIFY_TOKEN to re-enable.",
        )
    except Exception:
        return


def _maybe_toggle_postgres_dependent_mcps(
    log_path: Optional[Path], project_root: Path, enabled: bool
) -> None:
    """Disable or enable MCP servers that depend on Postgres (TaskBus/Parallel/Context-Compactor)."""
    try:
        cfg_path = project_root / "opencode.json"
        if not cfg_path.exists():
            return
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        if not isinstance(cfg, dict):
            return
        mcp = cfg.get("mcp")
        if not isinstance(mcp, dict):
            return

        # These MCPs require Postgres
        postgres_dependent = {"taskbus", "parallel", "context-compactor"}
        changed = False
        for name in postgres_dependent:
            if name in mcp:
                mcp_entry = mcp[name]
                if isinstance(mcp_entry, dict):
                    current = mcp_entry.get("enabled", True)
                    if bool(current) != enabled:
                        mcp_entry["enabled"] = enabled
                        changed = True
                        action = "enabled" if enabled else "disabled"
                        _log(
                            log_path, f"[FIX] {action} mcp.{name} (Postgres dependent)"
                        )

        if changed:
            # Backup current config
            try:
                bdir = project_root / ".ai" / "backups" / _now_stamp()
                bdir.mkdir(parents=True, exist_ok=True)
                (bdir / "opencode.json").write_text(
                    cfg_path.read_text(encoding="utf-8", errors="replace"),
                    encoding="utf-8",
                )
            except Exception:
                pass

            cfg["mcp"] = mcp
            cfg_path.write_text(
                json.dumps(cfg, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
            )
    except Exception as e:
        _log(log_path, f"[WARN] could not update Postgres-dependent MCP config: {e}")


def _start_local_postgres_windows(
    log_path: Optional[Path], env: Dict[str, str]
) -> bool:
    """Try to start PostgreSQL via Windows service or pg_ctl."""
    if not _is_windows():
        return False

    # Method 1: Try Windows service (postgresql-x64-16, postgresql-x64-15, etc.)
    service_names = [
        "postgresql-x64-16", "postgresql-x64-17", "postgresql-x64-15",
        "postgresql-x64-14", "postgresql-16", "postgresql-15", "postgresql"
    ]
    for svc in service_names:
        rc, out = _run_cmd(["sc", "query", svc], env=env, timeout_s=10)
        if rc == 0 and "RUNNING" in out:
            _log(log_path, f"[OK] PostgreSQL service '{svc}' already running")
            return True
        if rc == 0:  # Service exists but not running
            _log(log_path, f"[FIX] Starting PostgreSQL service '{svc}'...")
            rc2, out2 = _run_cmd(["net", "start", svc], env=env, timeout_s=60)
            if rc2 == 0:
                _log(log_path, f"[OK] PostgreSQL service '{svc}' started")
                time.sleep(2)  # Give it time to accept connections
                return True
            _log(log_path, f"[WARN] Failed to start service '{svc}': {out2}")

    # Method 2: Try pg_ctl directly for common PostgreSQL installations
    pg_dirs = [
        Path(r"C:\Program Files\PostgreSQL\17"),
        Path(r"C:\Program Files\PostgreSQL\16"),
        Path(r"C:\Program Files\PostgreSQL\15"),
        Path(r"C:\Program Files\PostgreSQL\14"),
        Path(r"C:\Program Files (x86)\PostgreSQL\16"),
    ]

    for pg_dir in pg_dirs:
        pg_ctl = pg_dir / "bin" / "pg_ctl.exe"
        data_dir = pg_dir / "data"
        if pg_ctl.exists() and data_dir.exists():
            _log(log_path, f"[FIX] Found PostgreSQL at {pg_dir}, starting via pg_ctl...")

            # Check if already running
            rc, out = _run_cmd(
                [str(pg_ctl), "status", "-D", str(data_dir)],
                env=env, timeout_s=10
            )
            if rc == 0 and "server is running" in out.lower():
                _log(log_path, f"[OK] PostgreSQL already running at {pg_dir}")
                return True

            # Try to start
            rc, out = _run_cmd(
                [str(pg_ctl), "start", "-D", str(data_dir), "-w", "-t", "30"],
                env=env, timeout_s=60
            )
            if rc == 0:
                _log(log_path, f"[OK] PostgreSQL started via pg_ctl at {pg_dir}")
                time.sleep(2)
                return True
            _log(log_path, f"[WARN] pg_ctl start failed: {out}")

    return False


def _ensure_postgres_running(
    log_path: Optional[Path], project_root: Path, env: Dict[str, str], global_dir: Optional[Path] = None
) -> bool:
    """Comprehensive PostgreSQL startup - handles ALL failure scenarios."""
    pg_env = _taskbus_pg_env_from_config(project_root)

    # Check if using cloud connection string
    conn_str = env.get("POSTGRES_CONNECTION_STRING", "") or pg_env.get("POSTGRES_CONNECTION_STRING", "")
    if conn_str:
        _log(log_path, "[INFO] Using cloud PostgreSQL connection string")
        ok, err = _check_postgres_connectable(pg_env=pg_env, env=env, timeout_s=5)
        if ok:
            _log(log_path, "[OK] cloud postgres reachable")
            return True
        _log(log_path, f"[ERROR] cloud postgres not reachable: {err}")
        return False

    # Initial connection check
    ok, err = _check_postgres_connectable(pg_env=pg_env, env=env, timeout_s=2)
    if ok:
        _log(log_path, "[OK] postgres reachable")
        return True

    host = (pg_env.get("POSTGRES_HOST") or env.get("POSTGRES_HOST") or "localhost").strip().lower()
    port = (pg_env.get("POSTGRES_PORT") or env.get("POSTGRES_PORT") or "5432").strip()
    db = (pg_env.get("POSTGRES_DB") or env.get("POSTGRES_DB") or "opencode_taskbus").strip()

    _log(log_path, f"[WARN] postgres not reachable ({host}:{port}/{db}): {err}")

    # Handle recovery mode - just wait
    if "recovery" in err.lower():
        _log(log_path, "[WAIT] PostgreSQL in recovery mode, waiting up to 30s...")
        if _wait_for_postgres_ready(log_path, pg_env, env, max_wait_s=30):
            _log(log_path, "[OK] postgres recovered")
            _maybe_create_postgres_db(log_path, pg_env=pg_env, env=env)
            return True

    # Only attempt local auto-start for localhost
    if host not in {"localhost", "127.0.0.1"}:
        _log(log_path, "[WARN] POSTGRES_HOST is not local; skipping auto-start")
        return False

    # Method 1: Try to start local PostgreSQL installation (Windows service or pg_ctl)
    if _is_windows():
        started = _start_local_postgres_windows(log_path, env)
        if started:
            # Wait for PostgreSQL to be fully ready (handles recovery mode)
            if _wait_for_postgres_ready(log_path, pg_env, env, max_wait_s=30):
                _log(log_path, "[OK] postgres ready (local installation)")
                _maybe_create_postgres_db(log_path, pg_env=pg_env, env=env)
                return True
            else:
                # Server started but not accepting connections to target DB - create it
                _maybe_create_postgres_db(log_path, pg_env=pg_env, env=env)
                if _wait_for_postgres_ready(log_path, pg_env, env, max_wait_s=10):
                    _log(log_path, "[OK] postgres ready (after db creation)")
                    return True

    # Try creating database (server might be up but DB missing)
    _maybe_create_postgres_db(log_path, pg_env=pg_env, env=env)
    ok, _err2 = _check_postgres_connectable(pg_env=pg_env, env=env, timeout_s=3)
    if ok:
        _log(log_path, "[OK] postgres reachable (db ready)")
        return True

    # Method 2: Docker fallback
    rc, out = _run_cmd(["docker", "--version"], env=env, timeout_s=30)
    if rc != 0:
        _log(
            log_path, f"[WARN] docker not available; cannot auto-start postgres ({out})"
        )
        return False

    name = "opencode-postgres"

    # If container exists, start it; else create.
    rc, names_out = _run_cmd(
        ["docker", "ps", "-a", "--format", "{{.Names}}"], env=env, timeout_s=60
    )
    exists = (rc == 0) and any(
        line.strip() == name for line in (names_out or "").splitlines()
    )

    if exists:
        _log(log_path, f"[FIX] starting existing docker container '{name}'")
        _run_cmd(["docker", "start", name], env=env, timeout_s=120)
    else:
        _log(log_path, f"[FIX] creating postgres docker container '{name}'")
        run_cmd = [
            "docker",
            "run",
            "-d",
            "--name",
            name,
            "--restart",
            "unless-stopped",
            "-p",
            f"{port}:5432",
            "-e",
            f"POSTGRES_USER={user}",
            "-e",
            f"POSTGRES_PASSWORD={pwd}",
            "-e",
            f"POSTGRES_DB={db}",
            "postgres:16",
        ]
        rc, out = _run_cmd(run_cmd, env=env, timeout_s=600)
        if rc != 0:
            _log(log_path, f"[ERROR] failed to start postgres container: {out}")
            return False

    # Wait for it to accept connections
    deadline = time.time() + 45
    while time.time() < deadline:
        ok, _ = _check_postgres_connectable(pg_env=pg_env, env=env, timeout_s=2)
        if ok:
            _log(log_path, "[OK] postgres reachable (docker)")
            return True
        time.sleep(1)

    ok, err = _check_postgres_connectable(pg_env=pg_env, env=env, timeout_s=3)
    if not ok:
        _log(
            log_path, f"[ERROR] postgres still not reachable after docker start: {err}"
        )
        return False
    return True


def _backup_root(project_root: Path) -> Path:
    return project_root / ".ai" / "backups" / _now_stamp()


def _backup_path(backup_root: Path, project_root: Path, target: Path) -> Path:
    try:
        rel = target.relative_to(project_root)
    except Exception:
        rel = Path(target.name)
    return backup_root / rel


def _backup_if_exists(
    log_path: Optional[Path], backup_root: Path, project_root: Path, target: Path
) -> None:
    if not target.exists():
        return
    dst = _backup_path(backup_root, project_root, target)
    _mkdir(dst.parent)
    try:
        if target.is_dir():
            shutil.copytree(target, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(target, dst)
        _log(log_path, f"[BACKUP] {target} -> {dst}")
    except Exception as e:
        _log(log_path, f"[WARN] backup failed for {target}: {e}")


def _replace_file(
    log_path: Optional[Path],
    backup_root: Path,
    project_root: Path,
    src: Path,
    dst: Path,
) -> None:
    if not src.exists():
        _log(log_path, f"[WARN] missing global file: {src}")
        return
    _backup_if_exists(log_path, backup_root, project_root, dst)
    _mkdir(dst.parent)
    shutil.copy2(src, dst)
    _log(log_path, f"[SYNC] {src.name} -> {dst}")


def _replace_dir(
    log_path: Optional[Path],
    backup_root: Path,
    project_root: Path,
    src: Path,
    dst: Path,
) -> None:
    if not src.exists() or not src.is_dir():
        _log(log_path, f"[WARN] missing global dir: {src}")
        return

    if dst.exists():
        _backup_if_exists(log_path, backup_root, project_root, dst)
        try:
            shutil.rmtree(dst)
        except Exception as e:
            _log(log_path, f"[WARN] failed to remove {dst}: {e}")

    _mkdir(dst.parent)
    shutil.copytree(src, dst)
    _log(log_path, f"[SYNC] {src.name}{os.sep} -> {dst}")


def _ensure_ai_layout(project_root: Path) -> None:
    dirs = [
        project_root / ".ai",
        project_root / ".ai" / "logs",
        project_root / ".ai" / "artifacts",
        project_root / ".ai" / "artifacts" / "planner_plans",
        project_root / ".ai" / "artifacts" / "agent_results",
        project_root / ".ai" / "tasks",
        project_root / ".ai" / "memory",
        project_root / ".ai" / "mcp",
        project_root / ".ai" / "pids",
        project_root / ".mcp",
    ]
    for d in dirs:
        _mkdir(d)

    kg = project_root / ".ai" / "knowledge-graph.json"
    if not kg.exists():
        _write_text(kg, '{"entities": [], "relations": []}\n')

    st = project_root / ".ai" / "sequential-thinking.json"
    if not st.exists():
        _write_text(st, '{"chains": {}, "current_chain_id": null, "updated_at": ""}\n')

    cb = project_root / ".ai" / "codebase-map.db"
    if not cb.exists():
        cb.write_bytes(b"")

    session_state = project_root / ".ai" / "SESSION_STATE.json"
    if not session_state.exists():
        _write_text(
            session_state,
            json.dumps({"status": "new", "updated_at": _now_stamp()}, indent=2) + "\n",
        )


def _detect_bash_shell(env: Dict[str, str]) -> Tuple[Optional[str], str]:
    """Detect a bash-compatible shell on Windows.

    OpenCode's internal command tool uses SHELL (or /bin/bash). Windows doesn't have /bin/bash
    by default, so we prefer Git Bash/MSYS2 if present.
    """

    if not _is_windows():
        return None, "non-windows"

    # Explicit override
    override = (env.get("OPENCODE_SHELL") or "").strip()
    if override and Path(override).exists():
        return override, "env-OPENCODE_SHELL"

    existing = (env.get("SHELL") or "").strip()
    if existing and Path(existing).exists():
        return existing, "env-SHELL"

    userprofile = os.environ.get("USERPROFILE") or str(Path.home())
    candidates = [
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files\Git\usr\bin\bash.exe",
        r"C:\Program Files (x86)\Git\bin\bash.exe",
        r"C:\Program Files (x86)\Git\usr\bin\bash.exe",
        str(
            Path(userprofile)
            / "scoop"
            / "apps"
            / "git"
            / "current"
            / "bin"
            / "bash.exe"
        ),
        r"C:\msys64\usr\bin\bash.exe",
        r"C:\msys32\usr\bin\bash.exe",
    ]

    for p in candidates:
        try:
            if Path(p).exists():
                return p, "auto"
        except Exception:
            continue

    return None, "missing"


def _ensure_shell_env(log_path: Optional[Path], env: Dict[str, str]) -> None:
    if not _is_windows():
        return
    bash, label = _detect_bash_shell(env)
    if bash:
        env.setdefault("SHELL", bash)
        # Some tools look at MSYSTEM for Git Bash; set a safe default.
        env.setdefault("MSYSTEM", "MINGW64")
        _log(log_path, f"[SHELL] bash={bash} ({label})")
    else:
        _log(
            log_path,
            "[WARN] No bash shell found on Windows. Install Git for Windows (Git Bash) or MSYS2 and restart.",
        )


def _resolve_opencode_cmd() -> Tuple[Optional[List[str]], str]:
    # On Windows, prefer the direct .exe over .cmd shims to avoid new window issues
    appdata = os.environ.get("APPDATA")
    if appdata and _is_windows():
        regular = (
            Path(appdata)
            / "npm"
            / "node_modules"
            / "opencode-ai"
            / "node_modules"
            / "opencode-windows-x64"
            / "bin"
            / "opencode.exe"
        )
        baseline = (
            Path(appdata)
            / "npm"
            / "node_modules"
            / "opencode-ai"
            / "node_modules"
            / "opencode-windows-x64-baseline"
            / "bin"
            / "opencode.exe"
        )
        if regular.exists():
            return [str(regular)], "npm-exe-regular"
        if baseline.exists():
            return [str(baseline)], "npm-exe-baseline"

    # Fallback to PATH (may return .cmd on Windows)
    p = shutil.which("opencode")
    if p:
        # If it's a .cmd file on Windows, wrap with cmd /c to keep in same window
        if _is_windows() and p.lower().endswith(".cmd"):
            return ["cmd", "/c", p], "path-opencode-cmd"
        return [p], "path-opencode"
    p = shutil.which("ocode")
    if p:
        if _is_windows() and p.lower().endswith(".cmd"):
            return ["cmd", "/c", p], "path-ocode-cmd"
        return [p], "path-ocode"

    # Last resort: npm shim
    if appdata and _is_windows():
        shim = Path(appdata) / "npm" / "opencode.cmd"
        if shim.exists():
            return ["cmd", "/c", str(shim)], "npm-opencode-cmd"

    return None, "missing"


def _run_preflight(
    log_path: Optional[Path], global_dir: Path, project_root: Path, env: Dict[str, str]
) -> bool:
    preflight = global_dir / "mcp_preflight.py"
    if not preflight.exists():
        _log(
            log_path,
            f"[WARN] mcp_preflight.py not found at {preflight}; skipping preflight",
        )
        return True

    cmd = [sys.executable, str(preflight)]
    _log(log_path, "[PREFLIGHT] checking MCP servers...")
    flags, si = _no_window_flags()
    proc = subprocess.run(
        cmd,
        cwd=str(project_root),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=flags,
        startupinfo=si,
    )
    if proc.stdout.strip():
        _log(log_path, proc.stdout.rstrip("\n"))
    if proc.stderr.strip():
        _log(log_path, proc.stderr.rstrip("\n"))
    ok = proc.returncode == 0
    _log(log_path, f"[PREFLIGHT] {'PASSED' if ok else 'FAILED'}")
    return ok


def _start_bg_process(
    *,
    log_path: Optional[Path],
    name: str,
    cmd: Sequence[str],
    cwd: Path,
    env: Dict[str, str],
    windows: bool,
    stdout_path: Path,
    stderr_path: Path,
) -> Optional[subprocess.Popen]:
    try:
        # Hard policy: never spawn extra Windows console windows.
        creationflags = 0
        if _is_windows():
            creationflags = (
                subprocess.CREATE_NEW_PROCESS_GROUP
                | subprocess.DETACHED_PROCESS
                | subprocess.CREATE_NO_WINDOW
            )

        _mkdir(stdout_path.parent)
        stdout = open(stdout_path, "a", encoding="utf-8")
        stderr = open(stderr_path, "a", encoding="utf-8")

        p = subprocess.Popen(
            list(cmd),
            cwd=str(cwd),
            env=env,
            stdout=stdout,
            stderr=stderr,
            creationflags=creationflags,
            start_new_session=(not _is_windows()),
        )

        if stdout is not None:
            stdout.close()
        if stderr is not None:
            stderr.close()

        _log(log_path, f"[START] {name} pid={p.pid}")
        return p
    except Exception as e:
        _log(log_path, f"[ERROR] failed to start {name}: {e}")
        return None


def _init_project(
    *,
    log_path: Optional[Path],
    global_dir: Path,
    project_root: Path,
    replace_project_knowledge: bool,
) -> None:
    _ensure_ai_layout(project_root)

    # If this is the global OpenCode directory, do not self-sync (matches oc.bat behavior).
    try:
        if project_root.resolve().samefile(global_dir.resolve()):
            _log(log_path, "[OK] project_root == global_dir; skipping sync")
            return
    except Exception:
        pass

    backup_root = _backup_root(project_root)
    _mkdir(backup_root)

    _replace_file(
        log_path,
        backup_root,
        project_root,
        global_dir / "opencode.json",
        project_root / "opencode.json",
    )
    _replace_file(
        log_path,
        backup_root,
        project_root,
        global_dir / "SYSTEM.md",
        project_root / "SYSTEM.md",
    )
    _replace_file(
        log_path,
        backup_root,
        project_root,
        global_dir / "MODELS.md",
        project_root / "MODELS.md",
    )
    _replace_file(
        log_path,
        backup_root,
        project_root,
        global_dir / "oc.bat",
        project_root / "oc.bat",
    )
    _replace_file(
        log_path,
        backup_root,
        project_root,
        global_dir / "oc.cmd",
        project_root / "oc.cmd",
    )
    _replace_file(
        log_path,
        backup_root,
        project_root,
        global_dir / "oc.py",
        project_root / "oc.py",
    )

    src_kg = global_dir / ".ai" / "PROJECT_KNOWLEDGE.md"
    dst_kg = project_root / ".ai" / "PROJECT_KNOWLEDGE.md"
    if replace_project_knowledge:
        _replace_file(log_path, backup_root, project_root, src_kg, dst_kg)
    else:
        if src_kg.exists() and not dst_kg.exists():
            _replace_file(log_path, backup_root, project_root, src_kg, dst_kg)
        elif dst_kg.exists():
            _log(log_path, f"[OK] keeping existing {dst_kg}")

    _replace_dir(
        log_path, backup_root, project_root, global_dir / ".mcp", project_root / ".mcp"
    )
    _replace_dir(
        log_path,
        backup_root,
        project_root,
        global_dir / ".ai" / "mcp",
        project_root / ".ai" / "mcp",
    )

    # Sync agent definitions (kimi.md, orchestrator.md, planners, coders, etc.)
    _replace_dir(
        log_path,
        backup_root,
        project_root,
        global_dir / ".ai" / "agent",
        project_root / ".ai" / "agent",
    )

    # Sync agents.json (agent registry)
    _replace_file(
        log_path,
        backup_root,
        project_root,
        global_dir / ".ai" / "agents.json",
        project_root / ".ai" / "agents.json",
    )

    # Sync core Python scripts required for system operation
    core_scripts = [
        "taskbus_worker.py",
        "progress_watchdog.py",
        "supervisor_daemon.py",
        "validate_system.py",
        "mcp_preflight.py",
        "repair_knowledge_graph.py",
        "context_compactor.py",
        "event_emitter.py",
        "logutil.py",
    ]
    for script in core_scripts:
        src = global_dir / script
        if src.exists():
            _replace_file(log_path, backup_root, project_root, src, project_root / script)

    # Sync PARL documentation and SQL schema
    parl_docs = [
        "PARL_ARCHITECTURE.md",
        "PARL_IMPLEMENTATION_GUIDE.md",
        "parl_tables.sql",
    ]
    for doc in parl_docs:
        src = global_dir / doc
        if src.exists():
            _replace_file(log_path, backup_root, project_root, src, project_root / doc)

    legacy = project_root / ".mcp" / "enforcer_mcp.py"
    if legacy.exists():
        try:
            legacy.unlink()
            _log(log_path, f"[CLEAN] removed legacy {legacy}")
        except Exception:
            pass

    _log(log_path, "[OK] initialization complete")

    # Ensure knowledge graph schema is canonical (prevents memory_read_graph schema errors).
    repair = global_dir / "repair_knowledge_graph.py"
    if repair.exists():
        try:
            flags, si = _no_window_flags()
            subprocess.run(
                [
                    sys.executable,
                    str(repair),
                    "--project-root",
                    str(project_root),
                    "--quiet",
                ],
                cwd=str(project_root),
                env=_merged_env(global_dir, project_root),
                check=False,
                creationflags=flags,
                startupinfo=si,
            )
            _log(log_path, "[OK] knowledge graph checked")
        except Exception as e:
            _log(log_path, f"[WARN] knowledge graph check failed: {e}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument(
        "--global", dest="global_dir", default=None, help="Global OpenCode dir"
    )
    ap.add_argument(
        "--project",
        dest="project_root",
        default=None,
        help="Project root (defaults to cwd)",
    )
    ap.add_argument("--tail-logs", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--init", action="store_true", help="Initialize project only")
    ap.add_argument(
        "--test", action="store_true", help="Run available tests (best-effort)"
    )

    ap.add_argument(
        "--status", action="store_true", help="Show background process status"
    )
    ap.add_argument(
        "--stop",
        action="store_true",
        help="Stop background processes (workers/watchdog/supervisor)",
    )
    ap.add_argument(
        "--restart-workers", action="store_true", help="Restart TaskBus workers"
    )
    ap.add_argument(
        "--restart-watchdog", action="store_true", help="Restart progress watchdog"
    )
    ap.add_argument(
        "--restart-supervisor", action="store_true", help="Restart supervisor daemon"
    )

    ap.add_argument(
        "--no-supervisor", action="store_true", help="Do not start supervisor daemon"
    )
    ap.add_argument(
        "--supervisor-interval-sec",
        type=int,
        default=10,
        help="Supervisor check interval",
    )

    ap.add_argument(
        "--skip-doctor",
        action="store_true",
        help="Skip self-validation (not recommended)",
    )

    ap.add_argument(
        "--require-postgres",
        action="store_true",
        help="Fail fast if Postgres/TaskBus is unavailable (default: degrade gracefully)",
    )
    ap.add_argument("--no-preflight", action="store_true", help="Skip MCP preflight")
    ap.add_argument(
        "--preflight-only", action="store_true", help="Run MCP preflight and exit"
    )
    ap.add_argument(
        "--no-workers", action="store_true", help="Do not start TaskBus workers"
    )

    # By default we run workers in real execution mode (they invoke the OpenCode CLI).
    # Set OPENCODE_WORKERS_RUN_OPENCODE=0 to keep workers in planner-only NOOP mode.
    ap.add_argument(
        "--workers-no-opencode",
        action="store_true",
        help="Start workers in NOOP mode (do not invoke OpenCode CLI)",
    )
    ap.add_argument(
        "--no-watchdog", action="store_true", help="Do not start progress watchdog"
    )
    ap.add_argument(
        "--monitor", action="store_true", help="Run the live status monitor"
    )
    ap.add_argument(
        "--no-monitor", action="store_true", help="Do not start the monitor window"
    )
    ap.set_defaults(no_monitor=True)

    # Default to: no extra windows for background processes
    win_default = False
    win_group = ap.add_mutually_exclusive_group()
    win_group.add_argument(
        "--windows",
        dest="windows",
        action="store_true",
        help="Start workers/watchdog in new console windows",
    )
    win_group.add_argument(
        "--no-windows",
        dest="windows",
        action="store_false",
        help="Run workers/watchdog detached (no new windows)",
    )
    ap.set_defaults(windows=win_default)

    # Default: do NOT spawn extra windows (users often find the flashing consoles annoying).
    # If you want a dedicated tail window, opt in via --log-window.
    ap.set_defaults(log_window=False)
    log_group = ap.add_mutually_exclusive_group()
    log_group.add_argument(
        "--log-window",
        dest="log_window",
        action="store_true",
        help="Start a dedicated log tail window (Windows only)",
    )
    log_group.add_argument(
        "--no-log-window",
        dest="log_window",
        action="store_false",
        help="Do not start the dedicated log tail window",
    )
    ap.add_argument("--workers", type=int, default=10, help="Number of TaskBus workers (10x speed target)")
    ap.add_argument(
        "--watchdog-min",
        type=int,
        default=10,
        help="Progress watchdog interval (minutes)",
    )
    ap.add_argument(
        "--keep-project-knowledge",
        action="store_true",
        help="Do not overwrite .ai/PROJECT_KNOWLEDGE.md if it exists",
    )
    ap.add_argument(
        "opencode_args", nargs=argparse.REMAINDER, help="Args forwarded to opencode"
    )
    args = ap.parse_args(list(argv) if argv is not None else None)

    project_root = (
        Path(args.project_root).expanduser().resolve()
        if args.project_root
        else Path.cwd().resolve()
    )

    if args.tail_logs:
        try:
            return _tail_logs_loop(project_root)
        except KeyboardInterrupt:
            return 130
    _mkdir(project_root)
    log_path = _log_setup(project_root)

    try:
        global_dir = _find_global_dir(args.global_dir)
    except Exception as e:
        _log(log_path, f"[ERROR] {e}")
        return 1

    env = _merged_env(global_dir, project_root)
    _ensure_shell_env(log_path, env)

    if args.log_window:
        _maybe_start_log_window(log_path, project_root, env)

    _log(log_path, "")
    _log(log_path, "======================================")
    _log(log_path, " OPENCODE PROJECT LAUNCHER (PYTHON)")
    _log(log_path, "======================================")
    _log(log_path, f" Project: {project_root}")
    _log(log_path, f" Global : {global_dir}")
    _log(log_path, "======================================")

    replace_project_knowledge = not args.keep_project_knowledge

    def _print_proc(name: str) -> None:
        st = _load_pid(project_root, name)
        if not st:
            _log(log_path, f"[STATUS] {name}: not found")
            return
        pid = int(st.get("pid") or 0)
        alive = _pid_alive(pid)
        _log(
            log_path,
            f"[STATUS] {name}: pid={pid} alive={alive} restarts={st.get('restart_count')}",
        )

    def _stop_proc(name: str) -> None:
        st = _load_pid(project_root, name)
        if not st:
            _log(log_path, f"[STOP] {name}: not found")
            return
        pid = int(st.get("pid") or 0)
        if _pid_alive(pid):
            ok = _terminate_pid(pid)
            _log(log_path, f"[STOP] {name}: pid={pid} ok={ok}")
        else:
            _log(log_path, f"[STOP] {name}: pid={pid} already-dead")

    if args.status:
        _ensure_ai_layout(project_root)
        for n in ["supervisor", "taskbus_worker", "progress_watchdog", "log_tail"]:
            _print_proc(n)
        return 0

    if args.monitor:
        _ensure_ai_layout(project_root)
        # Monitor loop logic (similar to oc.bat)
        while True:
            try:
                if _is_windows():
                    os.system("cls")
                else:
                    os.system("clear")
                print(
                    "====================================================================="
                )
                print(
                    f"  OPENCODE MONITOR - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                print(f"  Project: {project_root}")
                print(
                    "====================================================================="
                )

                # Check background procs
                for n in [
                    "supervisor",
                    "taskbus_worker",
                    "progress_watchdog",
                    "log_tail",
                ]:
                    st = _load_pid(project_root, n)
                    alive = _pid_alive(int(st.get("pid", 0))) if st else False
                    print(
                        f"  [{'OK' if alive else '!!'}] {n:<20} pid={st.get('pid') if st else 'N/A'}"
                    )

                print(
                    "---------------------------------------------------------------------"
                )
                # Quick TaskBus status via postgres_mcp
                try:
                    sys.path.insert(0, str(global_dir))
                    from postgres_mcp import TaskBusDB

                    db = TaskBusDB()
                    s = db.get_live_status()
                    print(
                        f"  [TASKBUS] Run: {s.get('run_id')} | Gate: {s.get('current_gate')}"
                    )
                    print(
                        f"  [STATS]   Running: {s.get('running_count')} | Queued: {s.get('queued_count')} | Done: {s.get('done_count')}"
                    )
                except Exception as e:
                    print(f"  [WARN] TaskBus unavailable: {e}")

                print(
                    "---------------------------------------------------------------------"
                )
                # Recent logs
                log_file = project_root / ".ai" / "logs" / "opencode.log"
                if log_file.exists():
                    print("  [RECENT LOGS]")
                    lines = log_file.read_text(
                        encoding="utf-8", errors="replace"
                    ).splitlines()[-5:]
                    for l in lines:
                        print(f"    {l}")

                print(
                    "====================================================================="
                )
                print("  Refreshing in 10s... (Ctrl+C to stop)")
                time.sleep(10)
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Monitor error: {e}")
                time.sleep(5)
        return 0

    if args.stop:
        _ensure_ai_layout(project_root)
        for n in ["log_tail", "progress_watchdog", "taskbus_worker", "supervisor"]:
            _stop_proc(n)
        return 0

    if args.restart_workers or args.restart_watchdog or args.restart_supervisor:
        _ensure_ai_layout(project_root)

        if args.restart_workers:
            _stop_proc("taskbus_worker")
            worker_py = global_dir / "taskbus_worker.py"
            cmd = [
                sys.executable,
                str(worker_py),
                "--project-root",
                str(project_root),
                "--workers",
                str(max(1, args.workers)),
            ]

            workers_run_opencode = (not args.workers_no_opencode) and (
                env.get("OPENCODE_WORKERS_RUN_OPENCODE", "1").strip().lower()
                in ("1", "true", "yes", "on")
            )
            if workers_run_opencode:
                cmd.append("--run-opencode")
            p = _start_bg_process(
                log_path=log_path,
                name="taskbus_worker",
                cmd=cmd,
                cwd=project_root,
                env=env,
                windows=args.windows,
                stdout_path=project_root / ".ai" / "logs" / "taskbus_worker_stdout.log",
                stderr_path=project_root / ".ai" / "logs" / "taskbus_worker_stderr.log",
            )
            if p:
                _write_pid(project_root, "taskbus_worker", p.pid, cmd, project_root)

        if args.restart_watchdog:
            _stop_proc("progress_watchdog")
            watchdog_py = global_dir / "progress_watchdog.py"
            cmd = [
                sys.executable,
                str(watchdog_py),
                "--project-root",
                str(project_root),
                "--interval-min",
                str(max(1, args.watchdog_min)),
            ]
            p = _start_bg_process(
                log_path=log_path,
                name="progress_watchdog",
                cmd=cmd,
                cwd=project_root,
                env=env,
                windows=args.windows,
                stdout_path=project_root
                / ".ai"
                / "logs"
                / "progress_watchdog_stdout.log",
                stderr_path=project_root
                / ".ai"
                / "logs"
                / "progress_watchdog_stderr.log",
            )
            if p:
                _write_pid(project_root, "progress_watchdog", p.pid, cmd, project_root)

        if args.restart_supervisor:
            _stop_proc("supervisor")
            supervisor_py = global_dir / "supervisor_daemon.py"
            cmd = [
                sys.executable,
                str(supervisor_py),
                "--project-root",
                str(project_root),
                "--interval-sec",
                str(max(1, int(args.supervisor_interval_sec))),
            ]
            p = _start_bg_process(
                log_path=log_path,
                name="supervisor",
                cmd=cmd,
                cwd=project_root,
                env=env,
                windows=False,
                stdout_path=project_root / ".ai" / "logs" / "supervisor_stdout.log",
                stderr_path=project_root / ".ai" / "logs" / "supervisor_stderr.log",
            )
            if p:
                _write_pid(project_root, "supervisor", p.pid, cmd, project_root)

        return 0

    # Default behavior: init + run.
    if args.init or (not args.test and not args.preflight_only):
        _init_project(
            log_path=log_path,
            global_dir=global_dir,
            project_root=project_root,
            replace_project_knowledge=replace_project_knowledge,
        )

    if args.init:
        return 0

    if args.test:
        tests = [global_dir / "test_compliance.py", global_dir / "test_enforcer.py"]
        any_test = False
        flags, si = _no_window_flags()
        for t in tests:
            if t.exists():
                any_test = True
                _log(log_path, f"[TEST] {t.name}")
                r = subprocess.run(
                    [sys.executable, str(t)], cwd=str(project_root), env=env,
                    creationflags=flags, startupinfo=si,
                )
                if r.returncode != 0:
                    return int(r.returncode)
            else:
                _log(log_path, f"[WARN] test script not found: {t}")

        # Run bundled unittest suite (no external deps)
        suite_dir = global_dir / "tests"
        if suite_dir.exists():
            any_test = True
            _log(log_path, "[TEST] unittest discover")
            r = subprocess.run(
                [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
                cwd=str(global_dir),
                env=env,
                creationflags=flags, startupinfo=si,
            )
            if r.returncode != 0:
                return int(r.returncode)

        if not any_test:
            _log(log_path, "[WARN] no test scripts found; nothing to run")
        return 0

    # Self-heal: TaskBus/Parallel/Context-Compactor require psycopg2 + a reachable Postgres.
    # Do NOT hard-require Postgres: OpenCode should start in any folder even on machines
    # without Postgres/Docker. We'll attempt best-effort enablement; otherwise we fall back
    # to a reduced feature set (TaskBus/Parallel/Context-Compactor disabled).
    postgres_ready = False
    psycopg2_ready = False
    try:
        psycopg2_ready = _ensure_python_package(
            log_path, module="psycopg2", pip_package="psycopg2-binary", env=env
        )
    except Exception as e:
        _log(log_path, f"[WARN] psycopg2 check/install failed: {e}")
        psycopg2_ready = False

    if psycopg2_ready:
        try:
            postgres_ready = _ensure_postgres_running(log_path, project_root, env, global_dir)
            # Ensure tables exist if PostgreSQL is ready
            if postgres_ready:
                pg_env = _taskbus_pg_env_from_config(project_root)
                _ensure_postgres_tables(log_path, pg_env=pg_env, env=env, global_dir=global_dir)
        except Exception as e:
            _log(log_path, f"[WARN] postgres startup check failed: {e}")
            postgres_ready = False
    else:
        _log(
            log_path,
            "[WARN] psycopg2 not available; TaskBus/Parallel/Context-Compactor will be disabled",
        )

    if (not postgres_ready) and args.require_postgres:
        _log(
            log_path,
            "[FATAL] Postgres not available (install/start Postgres or install Docker Desktop)",
        )
        return 1

    # Keep config aligned with runtime availability so preflight doesn't fail hard.
    try:
        _maybe_toggle_postgres_dependent_mcps(
            log_path, project_root, enabled=postgres_ready
        )
    except Exception as e:
        _log(log_path, f"[WARN] could not update Postgres-dependent MCP config: {e}")

    if not _ensure_opencode_cli(log_path, env):
        _log(log_path, "[FATAL] OpenCode CLI not installed (auto-install failed)")
        return 1

    # apify is optional; disable it automatically if unconfigured so doctor/preflight
    # don't abort before launching the CLI.
    _maybe_disable_apify_if_unconfigured(log_path, project_root, env)

    # Doctor is useful, but on machines without Postgres it fails noisily and slows startup.
    # In that case, skip it automatically (unless --require-postgres is set, which already
    # fails above).
    if (not args.skip_doctor) and postgres_ready:
        validate_py = global_dir / "validate_system.py"
        if validate_py.exists():
            _log(log_path, "[DOCTOR] validate_system.py")
            try:
                rc, _tail = _run_cmd_stream(
                    log_path,
                    [
                        sys.executable,
                        str(validate_py),
                        "--project-root",
                        str(project_root),
                        "--global-dir",
                        str(global_dir),
                    ],
                    cwd=project_root,
                    env=env,
                    timeout_s=600,
                    prefix="",
                )
                if rc != 0:
                    _log(
                        log_path,
                        "[WARN] doctor failed; continuing to launch CLI (use --skip-doctor to bypass)",
                    )
            except Exception as e:
                _log(log_path, f"[WARN] doctor failed to run: {e}")
        else:
            _log(log_path, "[WARN] validate_system.py not found; skipping doctor")

    preflight_ok = True
    if not args.no_preflight:
        preflight_ok = _run_preflight(log_path, global_dir, project_root, env)

    if args.preflight_only:
        return 0 if preflight_ok else 1

    if not preflight_ok:
        _log(log_path, "[WARN] preflight failed; continuing to launch CLI")

    # Start CMD window hider on Windows to suppress transient console windows
    if _is_windows():
        hide_script = global_dir / "hide_cmd_windows.pyw"
        if hide_script.exists():
            try:
                flags, si = _no_window_flags()
                subprocess.Popen(
                    ["pythonw", str(hide_script)],
                    cwd=str(project_root),
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=flags,
                    startupinfo=si,
                )
                _log(log_path, "[OK] CMD window hider started")
            except Exception as e:
                _log(log_path, f"[WARN] failed to start CMD window hider: {e}")

    if (not args.no_workers) and postgres_ready:
        # Safety check: don't spawn if too many processes already running
        current_procs = _count_opencode_processes()
        if current_procs >= MAX_OPENCODE_PROCESSES:
            _log(log_path, f"[WARN] Too many OpenCode processes ({current_procs}), skipping worker spawn")
            _log(log_path, "[INFO] Run 'taskkill /F /IM python.exe' and 'taskkill /F /IM node.exe' to clean up")
        else:
            worker_py = global_dir / "taskbus_worker.py"
            cmd = [
                sys.executable,
                str(worker_py),
                "--project-root",
                str(project_root),
                "--workers",
                str(max(1, args.workers)),
            ]

            workers_run_opencode = (not args.workers_no_opencode) and (
                env.get("OPENCODE_WORKERS_RUN_OPENCODE", "1").strip().lower()
                in ("1", "true", "yes", "on")
            )
            if workers_run_opencode:
                cmd.append("--run-opencode")
            p = _start_bg_process(
                log_path=log_path,
                name="taskbus_worker",
                cmd=cmd,
                cwd=project_root,
                env=env,
                windows=args.windows,
                stdout_path=project_root / ".ai" / "logs" / "taskbus_worker_stdout.log",
                stderr_path=project_root / ".ai" / "logs" / "taskbus_worker_stderr.log",
            )
            if p:
                _write_pid(project_root, "taskbus_worker", p.pid, cmd, project_root)
                _log(log_path, f"[INFO] Running {current_procs + 1} OpenCode processes (max: {MAX_OPENCODE_PROCESSES})")

    if (not args.no_watchdog) and postgres_ready:
        watchdog_py = global_dir / "progress_watchdog.py"
        cmd = [
            sys.executable,
            str(watchdog_py),
            "--project-root",
            str(project_root),
            "--interval-min",
            str(max(1, args.watchdog_min)),
        ]
        p = _start_bg_process(
            log_path=log_path,
            name="progress_watchdog",
            cmd=cmd,
            cwd=project_root,
            env=env,
            windows=args.windows,
            stdout_path=project_root / ".ai" / "logs" / "progress_watchdog_stdout.log",
            stderr_path=project_root / ".ai" / "logs" / "progress_watchdog_stderr.log",
        )
        if p:
            _write_pid(project_root, "progress_watchdog", p.pid, cmd, project_root)

    if not args.no_supervisor:
        st = _load_pid(project_root, "supervisor")
        pid = int(st.get("pid") or 0) if st else 0
        if st and _pid_alive(pid):
            _log(log_path, f"[OK] supervisor already running pid={pid}")
        else:
            supervisor_py = global_dir / "supervisor_daemon.py"
            if supervisor_py.exists():
                cmd = [
                    sys.executable,
                    str(supervisor_py),
                    "--project-root",
                    str(project_root),
                    "--interval-sec",
                    str(max(1, int(args.supervisor_interval_sec))),
                ]
                p = _start_bg_process(
                    log_path=log_path,
                    name="supervisor",
                    cmd=cmd,
                    cwd=project_root,
                    env=env,
                    windows=False,
                    stdout_path=project_root / ".ai" / "logs" / "supervisor_stdout.log",
                    stderr_path=project_root / ".ai" / "logs" / "supervisor_stderr.log",
                )
                if p:
                    _write_pid(project_root, "supervisor", p.pid, cmd, project_root)
            else:
                _log(
                    log_path,
                    f"[WARN] supervisor_daemon.py not found at {supervisor_py}",
                )

    # Monitor window is disabled by default to avoid spawning extra terminals.
    # Use: python oc.py --monitor

    oc_cmd, oc_label = _resolve_opencode_cmd()
    _log(log_path, f"[OPENCODE] {oc_label}")
    if not oc_cmd:
        _log(log_path, "[ERROR] OpenCode not found (resolve failed).")
        return 1

    try:
        _log(log_path, "[OPENCODE_CMD] " + " ".join(str(x) for x in oc_cmd))
    except Exception:
        pass

    # Non-interactive sanity check so failures are visible even if the window closes.
    try:
        rc, out = _run_cmd(
            list(oc_cmd) + ["--version"], cwd=project_root, env=env, timeout_s=30
        )
        _log(log_path, f"[OPENCODE] --version rc={rc}")
        if out:
            _log(log_path, out)
    except Exception as e:
        _log(log_path, f"[WARN] opencode --version check failed: {e}")

    forwarded = list(args.opencode_args)
    if forwarded and forwarded[0] == "--":
        forwarded = forwarded[1:]

    def _cleanup_all_processes(log_p: Optional[Path], proj: Path) -> None:
        """Kill all OpenCode-related processes when exiting."""
        _log(log_p, "[CLEANUP] Stopping all background processes...")

        # Stop managed processes via PID files
        for name in ["taskbus_worker", "progress_watchdog", "supervisor", "log_tail"]:
            st = _load_pid(proj, name)
            if st:
                pid = int(st.get("pid") or 0)
                if pid and _pid_alive(pid):
                    _terminate_pid(pid)
                    _log(log_p, f"[CLEANUP] Stopped {name} (pid={pid})")

        # Kill any orphan MCP processes spawned by this session
        if _is_windows():
            try:
                # Kill python processes running MCP servers
                mcp_patterns = ["postgres_mcp", "parallel_mcp", "memory_mcp", "codebase_mcp"]
                for pattern in mcp_patterns:
                    si = subprocess.STARTUPINFO()
                    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    si.wShowWindow = 0
                    subprocess.run(
                        f'wmic process where "commandline like \'%{pattern}%\'" delete',
                        shell=True, capture_output=True,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                        startupinfo=si,
                    )
            except Exception:
                pass

        _log(log_p, "[CLEANUP] Done")

    _log(log_path, "[START] OpenCode CLI")
    exit_code = 0
    try:
        r = subprocess.call(list(oc_cmd) + forwarded, cwd=str(project_root), env=env)
        _log(log_path, f"[DONE] OpenCode exit_code={r}")
        exit_code = int(r)
    except KeyboardInterrupt:
        _log(log_path, "[INFO] interrupted")
        exit_code = 130
    finally:
        time.sleep(0.2)
        # Always cleanup when OpenCode exits
        _cleanup_all_processes(log_path, project_root)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
