#!/usr/bin/env python3
"""mcp_preflight.py - ULTRA-FAST PARALLEL MCP CHECKER

Optimizations:
1. All checks run in parallel (ThreadPoolExecutor)
2. Micro-polling (10ms) for JSON-RPC responses
3. Quick-check mode (skips tool listing/smoke tests)
4. Redacted error reporting
"""

import json
import os
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


REQUIRED_ALWAYS = {
    "taskbus",
    "parallel",
    "filesystem",
    "memory",
    "sequential-thinking",
    "context-compactor",
}
# These are slow to start but non-blocking failures
OPTIONAL_SLOW_START = {"codebase-map", "playwright", "fetch"}
OPTIONAL_IF_ENABLED = {
    "computer-use",
    "computer-control",
    "postgres",
    "github",
    "tavily",
    "perplexity",
    "apify",
}

# Aggressive but safe timeouts (taskbus/parallel need more time for DB + workers)
DEFAULT_TIMEOUTS = {
    "taskbus": 20,
    "parallel": 20,
    "postgres": 15,
    "codebase-map": 30,
    "filesystem": 15,
    "memory": 15,
    "sequential-thinking": 15,
    "fetch": 30,
    "context-compactor": 10,
    "github": 15,
    "tavily": 15,
    "perplexity": 15,
    "apify": 30,
    "playwright": 30,
    "computer-control": 20,
    "computer-use": 20,
}


class MCPProcess:
    def __init__(self, name: str, cmd: List[str], env: Dict[str, str], timeout_s: int):
        self.name = name
        self.cmd = cmd
        self.env = env
        self.timeout_s = timeout_s
        self.proc = None
        self._q = queue.Queue()
        self._stderr = []

    def start(self):
        merged_env = os.environ.copy()
        merged_env.update({k: str(v) for k, v in self.env.items() if v is not None})
        self.proc = subprocess.Popen(
            self.cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=merged_env,
            bufsize=1,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )

        def _reader():
            try:
                for line in self.proc.stdout:
                    self._q.put(line)
            except:
                pass

        def _err_reader():
            try:
                for line in self.proc.stderr:
                    self._stderr.append(line)
                    if len(self._stderr) > 20:
                        self._stderr.pop(0)
            except:
                pass

        threading.Thread(target=_reader, daemon=True).start()
        threading.Thread(target=_err_reader, daemon=True).start()

    def stop(self):
        if self.proc:
            try:
                self.proc.terminate()
            except:
                pass
            try:
                self.proc.kill()
            except:
                pass

    def send(self, obj):
        self.proc.stdin.write(json.dumps(obj) + "\n")
        self.proc.stdin.flush()

    def recv_line(self, timeout_s):
        try:
            return self._q.get(timeout=timeout_s if timeout_s > 0 else 0.001)
        except queue.Empty:
            return None


def _wait_for_response(p, expected_id, timeout_s):
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        line = p.recv_line(0.01)
        if not line:
            continue
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            msg = json.loads(line)
            if msg.get("id") == expected_id:
                return msg
        except:
            continue
    raise TimeoutError(f"timeout {timeout_s}s")


def mcp_check(name: str, cfg: Dict[str, Any]) -> Tuple[bool, str]:
    cmd = cfg.get("command")
    if not isinstance(cmd, list) or not cmd:
        return False, "no command"
    env = cfg.get("environment") or {}
    timeout_s = int(DEFAULT_TIMEOUTS.get(name, 5))
    p = MCPProcess(
        name, [str(x) for x in cmd], {str(k): str(v) for k, v in env.items()}, timeout_s
    )
    p.start()
    try:
        p.send(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "clientInfo": {"name": "preflight", "version": "1.0"},
                    "capabilities": {},
                },
            }
        )
        _wait_for_response(p, 1, timeout_s)
        p.send({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
        return True, "ok"
    except Exception as e:
        import re

        err = str(e)
        err = re.sub(
            r"(postgres(?:ql)?://[^:\s]+:)([^@\s]+)(@)",
            r"\1***\3",
            err,
            flags=re.IGNORECASE,
        )
        tail = "".join(p._stderr)
        if tail:
            err += f" | tail={tail[-150:].strip()}"
        return False, err
    finally:
        p.stop()


def main():
    cfg_path = Path("opencode.json")
    if not cfg_path.exists():
        print("[PREFLIGHT] opencode.json missing", file=sys.stderr)
        return 1
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        mcp_cfg = cfg.get("mcp", {})
    except Exception as e:
        print(f"[PREFLIGHT] parse error: {e}", file=sys.stderr)
        return 1

    enabled = {
        k: v for k, v in mcp_cfg.items() if isinstance(v, dict) and v.get("enabled")
    }

    # Pre-check memory file schema to avoid runtime MCP schema mismatches.
    mem = enabled.get("memory")
    if isinstance(mem, dict):
        cmd = mem.get("command")
        mem_path = None
        if isinstance(cmd, list):
            for i, part in enumerate(cmd):
                if str(part) == "--memory-file-path" and i + 1 < len(cmd):
                    mem_path = str(cmd[i + 1])
                    break
        if not mem_path and isinstance(cmd, list):
            try:
                joined = " ".join(str(x) for x in cmd)
            except Exception:
                joined = ""
            if "memory_mcp.py" in joined:
                mem_path = ".ai/knowledge-graph.json"

        if mem_path:
            p = Path(mem_path)
            if not p.is_absolute():
                p = (Path(".") / p).resolve()
            try:
                obj = json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
            except Exception:
                obj = None

            def _is_canonical_kg(o: Any) -> bool:
                if not isinstance(o, dict):
                    return False
                ents = o.get("entities")
                rels = o.get("relations")
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

            if not _is_canonical_kg(obj):
                repair = Path(__file__).parent / "repair_knowledge_graph.py"
                if repair.exists():
                    try:
                        subprocess.run(
                            [
                                sys.executable,
                                str(repair),
                                "--project-root",
                                str(Path(".").resolve()),
                                "--quiet",
                            ],
                            cwd=str(Path(".").resolve()),
                            check=False,
                            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                        )
                        try:
                            obj2 = (
                                json.loads(p.read_text(encoding="utf-8"))
                                if p.exists()
                                else None
                            )
                        except Exception:
                            obj2 = None
                        if not _is_canonical_kg(obj2):
                            raise RuntimeError("memory file still invalid")
                    except Exception as e:
                        print(
                            f"[PREFLIGHT] WARN memory file invalid and repair failed: {e}",
                            file=sys.stderr,
                        )
                else:
                    try:
                        p.parent.mkdir(parents=True, exist_ok=True)
                        p.write_text(
                            '{"entities": [], "relations": []}\n', encoding="utf-8"
                        )
                    except Exception as e:
                        print(
                            f"[PREFLIGHT] WARN could not create memory file: {e}",
                            file=sys.stderr,
                        )

    to_check = [n for n in (REQUIRED_ALWAYS | OPTIONAL_IF_ENABLED) if n in enabled]
    to_check_slow = [n for n in OPTIONAL_SLOW_START if n in enabled]

    # If Apify is enabled but not configured, don't stall preflight.
    if "apify" in enabled and "apify" in to_check:
        token = (
            os.environ.get("APIFY_TOKEN")
            or enabled.get("apify", {}).get("environment", {}).get("APIFY_TOKEN")
            or ""
        ).strip()
        auth_path = Path.home() / ".apify" / "auth.json"
        if not token and not auth_path.exists():
            print(
                "[PREFLIGHT] WARN apify: APIFY_TOKEN not set; skipping check (non-blocking)",
                file=sys.stderr,
            )
            to_check = [n for n in to_check if n != "apify"]

    from concurrent.futures import ThreadPoolExecutor, as_completed

    failures, warnings = [], []

    with ThreadPoolExecutor(max_workers=30) as ex:
        futures = {ex.submit(mcp_check, n, enabled[n]): (n, False) for n in to_check}
        futures.update(
            {ex.submit(mcp_check, n, enabled[n]): (n, True) for n in to_check_slow}
        )

        for f in as_completed(futures):
            name, slow = futures[f]
            required = name in REQUIRED_ALWAYS
            try:
                ok, msg = f.result()
                if ok:
                    print(f"[PREFLIGHT] OK   {name}")
                elif (not required) or slow:
                    print(
                        f"[PREFLIGHT] WARN {name}: {msg} (non-blocking)",
                        file=sys.stderr,
                    )
                    warnings.append((name, msg))
                else:
                    print(f"[PREFLIGHT] FAIL {name}: {msg}", file=sys.stderr)
                    failures.append((name, msg))
            except Exception as e:
                if required:
                    print(f"[PREFLIGHT] FAIL {name}: {e}", file=sys.stderr)
                    failures.append((name, str(e)))
                else:
                    print(
                        f"[PREFLIGHT] WARN {name}: {e} (non-blocking)", file=sys.stderr
                    )
                    warnings.append((name, str(e)))

    if failures:
        return 1
    print(
        "[PREFLIGHT] PASSED" + (f" with {len(warnings)} warnings" if warnings else "")
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
