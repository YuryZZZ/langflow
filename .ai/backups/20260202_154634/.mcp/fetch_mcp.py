#!/usr/bin/env python3
"""fetch_mcp.py

Lightweight Fetch MCP server (stdio) implemented in Python.

Why
- Avoid npm/npx dependency for fetch when registry access is restricted.
- Provide deterministic, always-available web fetching.

Tools
- fetch_fetch_html
- fetch_fetch_markdown
- fetch_fetch_txt
- fetch_fetch_json

All tools take:
- url (required)
- max_length (optional, default 5000)
- start_index (optional, default 0)

NOTE: This implementation is intentionally simple. Markdown output is best-effort
(text extraction from HTML).
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request
from html import unescape
from typing import Any, Dict, Optional


DEFAULT_MAX = 5000


def _fetch_url(url: str, timeout_s: int = 30) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "OpenCode-FetchMCP/1.0",
            "Accept": "*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        return resp.read()


def _decode(data: bytes) -> str:
    # best-effort decode
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return data.decode(enc)
        except Exception:
            pass
    return data.decode("utf-8", errors="replace")


def _slice(text: str, start_index: int, max_length: int) -> str:
    if start_index < 0:
        start_index = 0
    if max_length <= 0:
        max_length = DEFAULT_MAX
    return text[start_index : start_index + max_length]


def _html_to_text(html: str) -> str:
    # Remove script/style
    html = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
    # Replace breaks with newlines
    html = re.sub(r"(?i)<br\s*/?>", "\n", html)
    html = re.sub(r"(?i)</p>", "\n\n", html)
    # Strip tags
    html = re.sub(r"(?s)<[^>]+>", " ", html)
    # Unescape
    html = unescape(html)
    # Collapse whitespace
    html = re.sub(r"[ \t\r\f\v]+", " ", html)
    html = re.sub(r"\n{3,}", "\n\n", html)
    return html.strip()


def fetch_html(args: Dict[str, Any]) -> Dict[str, Any]:
    url = args["url"]
    max_length = int(args.get("max_length", DEFAULT_MAX))
    start_index = int(args.get("start_index", 0))
    raw = _decode(_fetch_url(url))
    return {"url": url, "content": _slice(raw, start_index, max_length)}


def fetch_txt(args: Dict[str, Any]) -> Dict[str, Any]:
    url = args["url"]
    max_length = int(args.get("max_length", DEFAULT_MAX))
    start_index = int(args.get("start_index", 0))
    raw = _decode(_fetch_url(url))
    txt = _html_to_text(raw)
    return {"url": url, "content": _slice(txt, start_index, max_length)}


def fetch_markdown(args: Dict[str, Any]) -> Dict[str, Any]:
    # best-effort: return extracted text as markdown
    return fetch_txt(args)


def fetch_json(args: Dict[str, Any]) -> Dict[str, Any]:
    url = args["url"]
    max_length = int(args.get("max_length", DEFAULT_MAX))
    start_index = int(args.get("start_index", 0))
    raw = _decode(_fetch_url(url))
    # slice before parse is unsafe; parse first if possible
    try:
        obj = json.loads(raw)
        return {"url": url, "json": obj}
    except Exception:
        # fallback: provide sliced text
        return {"url": url, "content": _slice(raw, start_index, max_length), "error": "invalid json"}


TOOLS = [
    {
        "name": "fetch_fetch_html",
        "description": "Fetch a website and return the content as HTML",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "max_length": {"type": "integer"},
                "start_index": {"type": "integer"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "fetch_fetch_markdown",
        "description": "Fetch a website and return the content as Markdown (best-effort)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "max_length": {"type": "integer"},
                "start_index": {"type": "integer"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "fetch_fetch_txt",
        "description": "Fetch a website and return the content as plain text",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "max_length": {"type": "integer"},
                "start_index": {"type": "integer"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "fetch_fetch_json",
        "description": "Fetch a JSON file from a URL",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "max_length": {"type": "integer"},
                "start_index": {"type": "integer"},
            },
            "required": ["url"],
        },
    },
]


def handle_tool_call(name: str, args: Dict[str, Any]) -> Any:
    if name == "fetch_fetch_html":
        return fetch_html(args)
    if name == "fetch_fetch_markdown":
        return fetch_markdown(args)
    if name == "fetch_fetch_txt":
        return fetch_txt(args)
    if name == "fetch_fetch_json":
        return fetch_json(args)
    return {"error": f"Unknown tool: {name}"}


def handle_request(req: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    method = req.get("method")
    params = req.get("params", {})
    req_id = req.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "fetch-python", "version": "1.0.0"},
                "capabilities": {"tools": {}},
            },
        }
    if method == "notifications/initialized":
        return None
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}}
    if method == "tools/call":
        tool = params.get("name")
        args = params.get("arguments", {})
        out = handle_tool_call(tool, args)
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"content": [{"type": "text", "text": json.dumps(out, ensure_ascii=False)}]},
        }
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Unknown method: {method}"}}


def main() -> None:
    sys.stdout = open(sys.stdout.fileno(), mode="w", buffering=1, encoding="utf-8", errors="replace")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            resp = handle_request(req)
            if resp is not None:
                print(json.dumps(resp), flush=True)
        except json.JSONDecodeError as e:
            print(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": f"Parse error: {e}"}}), flush=True)
        except Exception as e:
            print(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32000, "message": str(e)}}), flush=True)


if __name__ == "__main__":
    main()
