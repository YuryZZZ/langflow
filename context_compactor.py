#!/usr/bin/env python3
"""context_compactor.py - PostgreSQL-backed Context Compaction for Orchestrator

Prevents context truncation by:
1. Storing FULL conversation history in PostgreSQL
2. Providing COMPACT summaries to orchestrator (under token limit)
3. Allowing retrieval of full context on-demand

Architecture:
- Full history stored in DB (never lost)
- Orchestrator receives: system prompt + recent N messages + summary of older
- Threshold: 80% of context window triggers compaction
"""

import json
import os
import sys
import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# PostgreSQL connection
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor, Json
except ImportError:
    print("[ERROR] psycopg2 required: pip install psycopg2-binary", file=sys.stderr)
    sys.exit(1)


# Configuration
POSTGRES_DSN = os.environ.get(
    "POSTGRES_CONNECTION_STRING",
    "postgresql://postgres:postgres@localhost:5432/opencode_taskbus"
)

# Context limits per model (tokens)
MODEL_CONTEXT_LIMITS = {
    "deepseek/deepseek-chat": 128000,
    "deepseek/deepseek-reasoner": 128000,
    "google/gemini-3-pro-preview": 1000000,
    "google/gemini-3-flash-preview": 1000000,
    "openai/gpt-5.2": 400000,
    "openai/gpt-5.1": 400000,
    "anthropic/claude-sonnet-4-5-20250514": 200000,
    "zai/glm-4.7": 256000,
}

# Compaction settings
COMPACTION_THRESHOLD = 0.80  # Trigger at 80% of context
RECENT_MESSAGES_KEEP = 10     # Keep last N messages uncompacted
SUMMARY_MAX_TOKENS = 2000     # Max tokens for summary
CHARS_PER_TOKEN = 4           # Rough estimate


class ContextCompactor:
    """Manages conversation context with PostgreSQL backing."""

    def __init__(self, session_id: str, model: str = "deepseek/deepseek-chat"):
        self.session_id = session_id
        self.model = model
        self.context_limit = MODEL_CONTEXT_LIMITS.get(model, 128000)
        self.threshold_tokens = int(self.context_limit * COMPACTION_THRESHOLD)
        self.conn = None
        self._connect()
        self._ensure_tables()

    def _connect(self):
        """Connect to PostgreSQL."""
        self.conn = psycopg2.connect(POSTGRES_DSN)
        self.conn.autocommit = True

    def _ensure_tables(self):
        """Create tables if not exist."""
        with self.conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS conversation_history (
                    id SERIAL PRIMARY KEY,
                    session_id VARCHAR(255) NOT NULL,
                    message_index INTEGER NOT NULL,
                    role VARCHAR(50) NOT NULL,
                    content TEXT NOT NULL,
                    tool_calls JSONB,
                    tool_results JSONB,
                    token_count INTEGER,
                    created_at TIMESTAMP DEFAULT NOW(),
                    compacted BOOLEAN DEFAULT FALSE,
                    UNIQUE(session_id, message_index)
                );

                CREATE INDEX IF NOT EXISTS idx_conv_session
                ON conversation_history(session_id, message_index);

                CREATE TABLE IF NOT EXISTS conversation_summaries (
                    id SERIAL PRIMARY KEY,
                    session_id VARCHAR(255) NOT NULL,
                    summary TEXT NOT NULL,
                    messages_start INTEGER NOT NULL,
                    messages_end INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                );

                CREATE INDEX IF NOT EXISTS idx_summary_session
                ON conversation_summaries(session_id);
            """)

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count from text."""
        return len(text) // CHARS_PER_TOKEN

    def store_message(self, role: str, content: str,
                      tool_calls: Optional[List] = None,
                      tool_results: Optional[List] = None) -> int:
        """Store a message in PostgreSQL. Returns message index."""
        with self.conn.cursor() as cur:
            # Get next index
            cur.execute(
                "SELECT COALESCE(MAX(message_index), -1) + 1 FROM conversation_history WHERE session_id = %s",
                (self.session_id,)
            )
            idx = cur.fetchone()[0]

            token_count = self._estimate_tokens(content)
            if tool_calls:
                token_count += self._estimate_tokens(json.dumps(tool_calls))
            if tool_results:
                token_count += self._estimate_tokens(json.dumps(tool_results))

            cur.execute("""
                INSERT INTO conversation_history
                (session_id, message_index, role, content, tool_calls, tool_results, token_count)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (session_id, message_index) DO UPDATE
                SET content = EXCLUDED.content, tool_calls = EXCLUDED.tool_calls,
                    tool_results = EXCLUDED.tool_results, token_count = EXCLUDED.token_count
            """, (self.session_id, idx, role, content,
                  Json(tool_calls) if tool_calls else None,
                  Json(tool_results) if tool_results else None,
                  token_count))

            return idx

    def get_total_tokens(self) -> int:
        """Get total token count for session."""
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT COALESCE(SUM(token_count), 0) FROM conversation_history WHERE session_id = %s",
                (self.session_id,)
            )
            return cur.fetchone()[0]

    def needs_compaction(self) -> bool:
        """Check if context needs compaction."""
        return self.get_total_tokens() >= self.threshold_tokens

    def get_full_history(self) -> List[Dict]:
        """Get full conversation history from PostgreSQL."""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT role, content, tool_calls, tool_results, message_index
                FROM conversation_history
                WHERE session_id = %s
                ORDER BY message_index ASC
            """, (self.session_id,))
            return [dict(row) for row in cur.fetchall()]

    def get_compacted_context(self, system_prompt: str = "") -> List[Dict]:
        """Get compacted context for orchestrator.

        Returns:
        - System prompt
        - Summary of old messages (if any)
        - Recent N messages in full
        """
        messages = []

        # 1. Add system prompt
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # 2. Get existing summary
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT summary, messages_end
                FROM conversation_summaries
                WHERE session_id = %s
                ORDER BY messages_end DESC
                LIMIT 1
            """, (self.session_id,))
            summary_row = cur.fetchone()

        summary_end = -1
        if summary_row:
            messages.append({
                "role": "system",
                "content": f"[CONTEXT SUMMARY - Messages 0-{summary_row['messages_end']}]\n{summary_row['summary']}"
            })
            summary_end = summary_row['messages_end']

        # 3. Get recent messages (after summary)
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT role, content, tool_calls, tool_results
                FROM conversation_history
                WHERE session_id = %s AND message_index > %s
                ORDER BY message_index ASC
            """, (self.session_id, summary_end))

            for row in cur.fetchall():
                msg = {"role": row["role"], "content": row["content"]}
                if row["tool_calls"]:
                    msg["tool_calls"] = row["tool_calls"]
                if row["tool_results"]:
                    msg["tool_results"] = row["tool_results"]
                messages.append(msg)

        return messages

    def create_summary(self, summarizer_func=None) -> str:
        """Create a summary of older messages.

        Args:
            summarizer_func: Optional function(messages) -> summary_text
                            If None, uses simple extraction
        """
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Get messages to summarize (all except recent N)
            cur.execute("""
                SELECT message_index, role, content
                FROM conversation_history
                WHERE session_id = %s AND compacted = FALSE
                ORDER BY message_index ASC
            """, (self.session_id,))
            all_messages = list(cur.fetchall())

        if len(all_messages) <= RECENT_MESSAGES_KEEP:
            return ""  # Not enough to summarize

        # Messages to compact
        to_compact = all_messages[:-RECENT_MESSAGES_KEEP]

        if not to_compact:
            return ""

        # Generate summary
        if summarizer_func:
            summary = summarizer_func([dict(m) for m in to_compact])
        else:
            # Simple extraction: key points from each message
            summary_parts = []
            for msg in to_compact:
                role = msg["role"]
                content = msg["content"][:500]  # Truncate long messages
                if role == "user":
                    summary_parts.append(f"- User asked: {content[:200]}...")
                elif role == "assistant":
                    summary_parts.append(f"- Assistant: {content[:200]}...")
            summary = "Conversation history summary:\n" + "\n".join(summary_parts[-20:])

        # Store summary
        start_idx = to_compact[0]["message_index"]
        end_idx = to_compact[-1]["message_index"]

        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO conversation_summaries
                (session_id, summary, messages_start, messages_end)
                VALUES (%s, %s, %s, %s)
            """, (self.session_id, summary, start_idx, end_idx))

            # Mark messages as compacted
            cur.execute("""
                UPDATE conversation_history
                SET compacted = TRUE
                WHERE session_id = %s AND message_index <= %s
            """, (self.session_id, end_idx))

        return summary

    def get_stats(self) -> Dict[str, Any]:
        """Get context statistics."""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    COUNT(*) as total_messages,
                    COALESCE(SUM(token_count), 0) as total_tokens,
                    COUNT(*) FILTER (WHERE compacted = TRUE) as compacted_messages
                FROM conversation_history
                WHERE session_id = %s
            """, (self.session_id,))
            row = cur.fetchone()

        return {
            "session_id": self.session_id,
            "model": self.model,
            "context_limit": self.context_limit,
            "threshold_tokens": self.threshold_tokens,
            "total_messages": row["total_messages"],
            "total_tokens": row["total_tokens"],
            "compacted_messages": row["compacted_messages"],
            "utilization_pct": round(row["total_tokens"] / self.context_limit * 100, 1),
            "needs_compaction": row["total_tokens"] >= self.threshold_tokens
        }

    def clear_session(self):
        """Clear all data for this session."""
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM conversation_history WHERE session_id = %s", (self.session_id,))
            cur.execute("DELETE FROM conversation_summaries WHERE session_id = %s", (self.session_id,))


# MCP Server Implementation
def run_mcp_server():
    """Run as MCP server for context compaction."""
    import json
    import sys

    compactors: Dict[str, ContextCompactor] = {}

    def get_compactor(session_id: str, model: str = "deepseek/deepseek-chat") -> ContextCompactor:
        key = f"{session_id}:{model}"
        if key not in compactors:
            compactors[key] = ContextCompactor(session_id, model)
        return compactors[key]

    TOOLS = [
        {
            "name": "context_store_message",
            "description": "Store a message in conversation history",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "role": {"type": "string", "enum": ["user", "assistant", "system"]},
                    "content": {"type": "string"},
                    "model": {"type": "string"}
                },
                "required": ["session_id", "role", "content"]
            }
        },
        {
            "name": "context_get_compacted",
            "description": "Get compacted context for orchestrator (prevents truncation)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "system_prompt": {"type": "string"},
                    "model": {"type": "string"}
                },
                "required": ["session_id"]
            }
        },
        {
            "name": "context_compact_now",
            "description": "Force compaction of conversation history",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "model": {"type": "string"}
                },
                "required": ["session_id"]
            }
        },
        {
            "name": "context_get_stats",
            "description": "Get context utilization statistics",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "model": {"type": "string"}
                },
                "required": ["session_id"]
            }
        },
        {
            "name": "context_get_full_history",
            "description": "Get full uncompacted history from PostgreSQL",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"}
                },
                "required": ["session_id"]
            }
        }
    ]

    def handle_tool(name: str, args: Dict) -> Dict:
        session_id = args.get("session_id", "default")
        model = args.get("model", "deepseek/deepseek-chat")
        compactor = get_compactor(session_id, model)

        if name == "context_store_message":
            idx = compactor.store_message(
                role=args["role"],
                content=args["content"],
                tool_calls=args.get("tool_calls"),
                tool_results=args.get("tool_results")
            )
            # Auto-compact if needed
            if compactor.needs_compaction():
                compactor.create_summary()
            return {"stored": True, "message_index": idx, "needs_compaction": compactor.needs_compaction()}

        elif name == "context_get_compacted":
            messages = compactor.get_compacted_context(args.get("system_prompt", ""))
            stats = compactor.get_stats()
            return {"messages": messages, "stats": stats}

        elif name == "context_compact_now":
            summary = compactor.create_summary()
            return {"compacted": True, "summary_preview": summary[:500] if summary else None}

        elif name == "context_get_stats":
            return compactor.get_stats()

        elif name == "context_get_full_history":
            return {"history": compactor.get_full_history()}

        return {"error": f"Unknown tool: {name}"}

    # MCP protocol loop
    sys.stderr.write("[Context Compactor MCP] Starting...\n")

    for line in sys.stdin:
        try:
            req = json.loads(line.strip())
            req_id = req.get("id")
            method = req.get("method")

            if method == "initialize":
                response = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "serverInfo": {"name": "context-compactor", "version": "1.0"},
                        "capabilities": {"tools": {}}
                    }
                }
            elif method == "notifications/initialized":
                continue
            elif method == "tools/list":
                response = {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}}
            elif method == "tools/call":
                params = req.get("params", {})
                result = handle_tool(params.get("name"), params.get("arguments", {}))
                response = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
                }
            else:
                response = {"jsonrpc": "2.0", "id": req_id, "result": {}}

            print(json.dumps(response), flush=True)
        except Exception as e:
            sys.stderr.write(f"[Context Compactor MCP] Error: {e}\n")


if __name__ == "__main__":
    run_mcp_server()
