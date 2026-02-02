#!/usr/bin/env python3
"""validate_system.py - local self-test for OpenCode system config.

Validates the parts that historically break:
- Memory MCP schema compatibility
- Knowledge graph canonical file format
- MCP preflight sanity
- TaskBus connectivity (Postgres)

Usage:
  python validate_system.py
  python validate_system.py --project-root C:/path/to/project

Exit codes:
  0 = pass
  1 = fail
"""

from __future__ import annotations

import argparse
import json
import os
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _fail(msg: str) -> Tuple[bool, str]:
    return False, msg


def _ok(msg: str) -> Tuple[bool, str]:
    return True, msg


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _is_canonical_kg(obj: Any) -> bool:
    if not isinstance(obj, dict):
        return False
    ents = obj.get("entities")
    rels = obj.get("relations")
    if not isinstance(ents, list) or not isinstance(rels, list):
        return False
    for e in ents:
        if not isinstance(e, dict):
            return False
        if set(e.keys()) - {"name", "entityType", "observations"}:
            return False
    for r in rels:
        if not isinstance(r, dict):
            return False
        if set(r.keys()) - {"from", "to", "relationType"}:
            return False
    return True


def _project_env_from_global(global_dir: Path) -> Dict[str, str]:
    # Keep it simple: reuse current env and load global .env if present.
    env = os.environ.copy()
    env_path = global_dir / ".env"
    if env_path.exists():
        for raw in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip()
            if not k:
                continue
            env.setdefault(k, v)
    env.setdefault("OPENCODE_PROJECT_ROOT", str(Path.cwd()))
    env.setdefault("OPENCODE_GLOBAL_DIR", str(global_dir))
    return env


def check_shell_windows(global_dir: Path) -> Tuple[bool, str]:
    if os.name != "nt":
        return _ok("shell check skipped (non-windows)")

    env_shell = (os.environ.get("SHELL") or "").strip()
    if env_shell and Path(env_shell).exists():
        return _ok(f"SHELL set: {env_shell}")

    # Try typical Git Bash locations
    candidates = [
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files\Git\usr\bin\bash.exe",
        r"C:\Program Files (x86)\Git\bin\bash.exe",
        r"C:\Program Files (x86)\Git\usr\bin\bash.exe",
        r"C:\msys64\usr\bin\bash.exe",
    ]
    for c in candidates:
        if Path(c).exists():
            return _ok(f"bash found: {c} (set SHELL to enable command exec)")

    return _fail("No bash found on Windows. Install Git for Windows (Git Bash) and restart OpenCode.")


def check_opencode_json(project_root: Path) -> Tuple[bool, str]:
    cfg_path = project_root / "opencode.json"
    if not cfg_path.exists():
        return _fail("opencode.json missing")
    try:
        cfg = _load_json(cfg_path)
    except Exception as e:
        return _fail(f"opencode.json parse error: {e}")

    mcp = cfg.get("mcp")
    if not isinstance(mcp, dict):
        return _fail("opencode.json missing mcp block")

    mem = mcp.get("memory")
    if not isinstance(mem, dict):
        return _fail("opencode.json missing mcp.memory")
    cmd = mem.get("command")
    if not isinstance(cmd, list) or not cmd:
        return _fail("opencode.json mcp.memory.command invalid")

    joined = " ".join(str(x) for x in cmd)
    if "memory_mcp.py" not in joined:
        return _fail("mcp.memory.command does not point to memory_mcp.py")

    return _ok("opencode.json OK")


def check_knowledge_graph(project_root: Path) -> Tuple[bool, str]:
    kg = project_root / ".ai" / "knowledge-graph.json"
    if not kg.exists():
        return _fail(".ai/knowledge-graph.json missing")
    try:
        obj = _load_json(kg)
    except Exception as e:
        return _fail(f"knowledge graph parse error: {e}")
    if not _is_canonical_kg(obj):
        return _fail("knowledge graph is not canonical (schema mismatch)")
    return _ok("knowledge graph canonical")


def check_repair_script(global_dir: Path, project_root: Path) -> Tuple[bool, str]:
    rp = global_dir / "repair_knowledge_graph.py"
    if not rp.exists():
        return _fail("repair_knowledge_graph.py missing")

    try:
        sys.path.insert(0, str(global_dir))
        import repair_knowledge_graph as rkg  # type: ignore

        rkg.repair(project_root, verbose=False)
    except Exception as e:
        return _fail(f"repair_knowledge_graph failed: {e}")

    return _ok("repair_knowledge_graph OK")


def check_taskbus_connect(project_root: Path) -> Tuple[bool, str]:
    cfg_path = project_root / "opencode.json"
    try:
        cfg = _load_json(cfg_path)
    except Exception as e:
        return _fail(f"cannot read opencode.json: {e}")

    mcp = cfg.get("mcp")
    tb = mcp.get("taskbus") if isinstance(mcp, dict) else None
    env = tb.get("environment") if isinstance(tb, dict) else None
    if not isinstance(env, dict):
        return _fail("opencode.json mcp.taskbus.environment missing")

    host = str(env.get("POSTGRES_HOST", "localhost"))
    port = int(env.get("POSTGRES_PORT", 5432))
    db = str(env.get("POSTGRES_DB", "opencode_taskbus"))
    user = str(env.get("POSTGRES_USER", "postgres"))
    pwd = str(env.get("POSTGRES_PASSWORD", ""))

    try:
        import psycopg2  # type: ignore

        conn = psycopg2.connect(host=host, port=port, dbname=db, user=user, password=pwd, connect_timeout=3)
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        cur.close()
        conn.close()
        return _ok("taskbus postgres connect OK")
    except Exception as e:
        return _fail(f"taskbus postgres connect failed: {e}")


def _rpc_exchange(proc: subprocess.Popen, send_obj: Dict[str, Any], timeout_s: float) -> Dict[str, Any]:
    # Write JSON line
    assert proc.stdin is not None
    proc.stdin.write(json.dumps(send_obj) + "\n")
    proc.stdin.flush()

    # Read response lines until matching id
    deadline = time.time() + timeout_s
    want_id = send_obj.get("id")
    while time.time() < deadline:
        try:
            line = proc.stdout.readline()  # type: ignore
        except Exception:
            break
        if not line:
            time.sleep(0.01)
            continue
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            msg = json.loads(line)
        except Exception:
            continue
        if want_id is None:
            return msg
        if msg.get("id") == want_id:
            return msg
    raise TimeoutError(f"rpc timeout after {timeout_s}s")


def check_memory_mcp_rpc(global_dir: Path, project_root: Path) -> Tuple[bool, str]:
    mp = global_dir / "memory_mcp.py"
    if not mp.exists():
        return _fail("memory_mcp.py missing")

    try:
        # Use CREATE_NO_WINDOW on Windows to prevent CMD flash
        creationflags = 0
        if os.name == "nt":
            creationflags = subprocess.CREATE_NO_WINDOW
        proc = subprocess.Popen(
            [sys.executable, "-u", str(mp)],
            cwd=str(project_root),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=creationflags,
        )
    except Exception as e:
        return _fail(f"failed to start memory_mcp: {e}")

    try:
        _rpc_exchange(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2024-11-05", "clientInfo": {"name": "validate", "version": "1.0"}, "capabilities": {}},
            },
            5.0,
        )
        # tools/list
        tools_msg = _rpc_exchange(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}, 5.0)
        if "result" not in tools_msg:
            return _fail("memory_mcp tools/list failed")

        # tools/call read_graph
        read_msg = _rpc_exchange(
            proc,
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "read_graph", "arguments": {}}},
            5.0,
        )
        content = (((read_msg.get("result") or {}).get("content") or [])[0] if isinstance((read_msg.get("result") or {}).get("content"), list) and (read_msg.get("result") or {}).get("content") else None)
        if not isinstance(content, dict) or "text" not in content:
            return _fail("memory_mcp read_graph returned no text content")
        try:
            graph = json.loads(content.get("text") or "{}")
        except Exception as e:
            return _fail(f"memory_mcp read_graph invalid json text: {e}")
        if not _is_canonical_kg(graph):
            return _fail("memory_mcp read_graph output not canonical")

        # create_entities smoke
        _rpc_exchange(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {
                    "name": "create_entities",
                    "arguments": {"entities": [{"name": "_validate", "entityType": "test", "observations": ["ok"]}]},
                },
            },
            5.0,
        )

        read2 = _rpc_exchange(
            proc,
            {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "search_nodes", "arguments": {"query": "_validate"}}},
            5.0,
        )
        content2 = (((read2.get("result") or {}).get("content") or [])[0] if isinstance((read2.get("result") or {}).get("content"), list) and (read2.get("result") or {}).get("content") else None)
        if not isinstance(content2, dict) or "text" not in content2:
            return _fail("memory_mcp search_nodes returned no text content")
        graph2 = json.loads(content2.get("text") or "{}")
        if not _is_canonical_kg(graph2):
            return _fail("memory_mcp search_nodes output not canonical")

        return _ok("memory_mcp RPC OK")
    except Exception as e:
        return _fail(f"memory_mcp RPC failed: {e}")
    finally:
        try:
            proc.terminate()
        except Exception:
            pass
        try:
            proc.kill()
        except Exception:
            pass


def check_preflight(global_dir: Path, project_root: Path) -> Tuple[bool, str]:
    try:
        sys.path.insert(0, str(global_dir))
        import mcp_preflight  # type: ignore

        cwd = os.getcwd()
        try:
            os.chdir(str(project_root))
            rc = int(mcp_preflight.main())
        finally:
            os.chdir(cwd)
        if rc != 0:
            return _fail(f"mcp_preflight failed rc={rc}")
        return _ok("mcp_preflight OK")
    except Exception as e:
        return _fail(f"mcp_preflight import/run failed: {e}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", default=None)
    ap.add_argument("--global-dir", default=None)
    args = ap.parse_args()

    project_root = Path(args.project_root).expanduser().resolve() if args.project_root else Path.cwd().resolve()

    if args.global_dir:
        global_dir = Path(args.global_dir).expanduser().resolve()
    else:
        global_dir = Path(__file__).resolve().parent

    (project_root / ".ai").mkdir(parents=True, exist_ok=True)

    checks: List[Tuple[str, Tuple[bool, str]]] = []
    checks.append(("shell_windows", check_shell_windows(global_dir)))
    checks.append(("opencode.json", check_opencode_json(project_root)))
    checks.append(("repair_knowledge_graph", check_repair_script(global_dir, project_root)))
    checks.append(("knowledge_graph", check_knowledge_graph(project_root)))
    checks.append(("taskbus_connect", check_taskbus_connect(project_root)))
    checks.append(("memory_mcp_rpc", check_memory_mcp_rpc(global_dir, project_root)))
    checks.append(("mcp_preflight", check_preflight(global_dir, project_root)))

    failed = 0
    results: List[Dict[str, Any]] = []
    for name, (ok, msg) in checks:
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {name}: {msg}")
        results.append({"check": name, "ok": bool(ok), "message": msg})
        if not ok:
            failed += 1

    # Persist a machine-readable report + update session state and KG (best-effort).
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    artifacts_dir = project_root / ".ai" / "artifacts" / "validation"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "ts": ts,
        "project_root": str(project_root),
        "global_dir": str(global_dir),
        "passed": failed == 0,
        "failed_count": failed,
        "results": results,
    }
    (artifacts_dir / "doctor_latest.json").write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    # Update SESSION_STATE.json if present
    try:
        ss = project_root / ".ai" / "SESSION_STATE.json"
        if ss.exists():
            obj = json.loads(ss.read_text(encoding="utf-8"))
            if isinstance(obj, dict):
                obj["last_updated"] = ts
                obj["VALIDATION_STATUS"] = ("DOCTOR PASS " if failed == 0 else "DOCTOR FAIL ") + ts
                ss.write_text(json.dumps(obj, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    except Exception:
        pass

    # Update canonical knowledge graph (strict schema)
    try:
        kg = project_root / ".ai" / "knowledge-graph.json"
        if kg.exists():
            kg_obj = json.loads(kg.read_text(encoding="utf-8"))
        else:
            kg_obj = {"entities": [], "relations": []}
        if isinstance(kg_obj, dict):
            ents = kg_obj.get("entities")
            rels = kg_obj.get("relations")
            if not isinstance(ents, list):
                ents = []
            if not isinstance(rels, list):
                rels = []
            ent_name = f"doctor_run_{ts}"
            ents.append({
                "name": ent_name,
                "entityType": "validation",
                "observations": [
                    "passed=" + str(failed == 0).lower(),
                    "failed_count=" + str(failed),
                    "report=.ai/artifacts/validation/doctor_latest.json",
                ],
            })
            kg_obj["entities"] = ents
            kg_obj["relations"] = rels
            kg.write_text(json.dumps(kg_obj, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    except Exception:
        pass

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
