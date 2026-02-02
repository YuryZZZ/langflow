#!/usr/bin/env python3
"""supervisor_daemon.py - keep OpenCode background processes alive.

Responsibilities
- Track PIDs for background processes (workers/watchdog/supervisor)
- Restart managed processes if they die (with backoff + max restarts)
- Provide a single place to check health via pid files

Pid files live in: .ai/pids/<name>.json
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _safe_read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def _safe_write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _is_windows() -> bool:
    return os.name == "nt"


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


def _start_detached(cmd: list[str], cwd: str, env: Dict[str, str]) -> Optional[int]:
    try:
        creationflags = 0
        if _is_windows():
            creationflags = (
                subprocess.CREATE_NEW_PROCESS_GROUP
                | subprocess.DETACHED_PROCESS
                | subprocess.CREATE_NO_WINDOW
            )
        p = subprocess.Popen(
            cmd,
            cwd=cwd,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
            start_new_session=(not _is_windows()),
        )
        return int(p.pid)
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", required=True)
    ap.add_argument("--interval-sec", type=int, default=10)
    ap.add_argument("--max-restarts", type=int, default=10)
    args = ap.parse_args()

    project_root = Path(args.project_root).resolve()
    os.chdir(str(project_root))

    ai_dir = project_root / ".ai"
    logs_dir = ai_dir / "logs"
    pids_dir = ai_dir / "pids"
    logs_dir.mkdir(parents=True, exist_ok=True)
    pids_dir.mkdir(parents=True, exist_ok=True)

    log_path = logs_dir / "supervisor.log"

    def log(msg: str) -> None:
        try:
            with log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"ts": _now_iso(), "msg": msg}) + "\n")
        except Exception:
            pass

    # Write our own pid file
    sup_pid_file = pids_dir / "supervisor.json"
    _safe_write_json(
        sup_pid_file,
        {
            "name": "supervisor",
            "pid": os.getpid(),
            "managed": True,
            "cmd": [sys.executable, str(Path(__file__).resolve()), "--project-root", str(project_root)],
            "cwd": str(project_root),
            "started_at": _now_iso(),
            "restart_count": 0,
        },
    )

    log("supervisor started")

    interval = max(1, int(args.interval_sec))
    env = os.environ.copy()
    env["OPENCODE_PROJECT_ROOT"] = str(project_root)

    while True:
        try:
            for pid_file in sorted(pids_dir.glob("*.json")):
                if pid_file.name == "supervisor.json":
                    continue

                state = _safe_read_json(pid_file)
                if not state:
                    continue
                if not state.get("managed"):
                    continue

                pid = int(state.get("pid") or 0)
                alive = _pid_alive(pid)

                if alive:
                    state["last_seen"] = _now_iso()
                    _safe_write_json(pid_file, state)
                    continue

                # restart
                restart_count = int(state.get("restart_count") or 0)
                if restart_count >= int(args.max_restarts):
                    log(f"max restarts reached for {pid_file.name}")
                    continue

                cmd = state.get("cmd")
                cwd = state.get("cwd") or str(project_root)
                if not isinstance(cmd, list) or not cmd:
                    log(f"cannot restart {pid_file.name}: missing cmd")
                    continue

                new_pid = _start_detached([str(x) for x in cmd], cwd=str(cwd), env=env)
                if not new_pid:
                    log(f"restart failed for {pid_file.name}")
                    continue

                state["pid"] = new_pid
                state["restart_count"] = restart_count + 1
                state["restarted_at"] = _now_iso()
                _safe_write_json(pid_file, state)
                log(f"restarted {pid_file.name} pid={new_pid}")

        except Exception as e:
            log(f"loop error: {e}")

        time.sleep(interval)


if __name__ == "__main__":
    raise SystemExit(main())
