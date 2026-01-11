# MCP Servers Reference (v7.5)

## Overview

14 MCP servers configured, 13 enabled by default.

## Server List

| # | Server | Type | Status | Description |
|---|--------|------|--------|-------------|
| 1 | taskbus | Python | Required | PostgreSQL task queue for swarm coordination |
| 2 | parallel | Python | Required | Parallel planner/worker dispatch |
| 3 | memory | Node.js | Required | Knowledge graph persistence |
| 4 | sequential-thinking | Node.js | Required | Chain-of-thought reasoning |
| 5 | filesystem | Node.js | Required | File system operations |
| 6 | fetch | Node.js | Required | HTTP fetch for web content |
| 7 | context-compactor | Python | Required | Prevents context truncation |
| 8 | postgres | Node.js | Optional | Direct PostgreSQL queries |
| 9 | github | Node.js | Optional | GitHub API integration |
| 10 | codebase-map | Node.js | Optional | Code indexing and search |
| 11 | playwright | Node.js | Optional | Browser automation |
| 12 | tavily | Python | Optional | Tavily web search API |
| 13 | perplexity | Python | Optional | Perplexity AI search |
| 14 | computer-control | Node.js | Disabled | Desktop automation |

## Core Servers (Required)

### taskbus
- **File**: `postgres_mcp.py`
- **Purpose**: PostgreSQL-backed task queue
- **Tools**: `create_run`, `create_task`, `complete_task`, `get_parallel_status`
- **Database**: `opencode_taskbus`

### parallel
- **File**: `parallel_mcp.py`
- **Purpose**: Parallel task dispatch
- **Tools**: `parallel_dispatch_planners`, `parallel_dispatch_workers`, `parallel_run_tasks`

### context-compactor
- **File**: `context_compactor.py`
- **Purpose**: Prevents context window overflow
- **Tools**: `context_store_message`, `context_get_compacted`, `context_compact_now`, `context_get_stats`
- **Features**:
  - Stores full history in PostgreSQL
  - Auto-compacts at 80% of context limit
  - Keeps last 10 messages uncompacted
  - Per-model context limits

### memory
- **Package**: `@modelcontextprotocol/server-memory`
- **Purpose**: Persistent knowledge graph
- **Storage**: `.ai/knowledge-graph.json`

### sequential-thinking
- **Package**: `@modelcontextprotocol/server-sequential-thinking`
- **Purpose**: Chain-of-thought reasoning
- **Tools**: `create_thinking_chain`, `add_thought`, `get_chain`

### filesystem
- **Package**: `@modelcontextprotocol/server-filesystem`
- **Purpose**: File read/write operations
- **Root**: Project directory (`.`)

### fetch
- **Package**: `mcp-fetch-server`
- **Purpose**: HTTP content fetching
- **Features**: HTML to markdown conversion

## Search Servers

### tavily
- **File**: `tavily_mcp.py`
- **Purpose**: Tavily search API
- **Tools**: `tavily_search`, `tavily_extract`
- **API Key**: `TAVILY_API_KEY`

### perplexity
- **File**: `perplexity_mcp.py`
- **Purpose**: Perplexity AI search
- **Tools**: `perplexity_search`
- **API Key**: `PERPLEXITY_API_KEY`

## Optional Servers

### postgres
- **Package**: `@modelcontextprotocol/server-postgres`
- **Purpose**: Direct SQL queries
- **Connection**: `postgresql://postgres:postgres@localhost:5432/opencode_taskbus`

### github
- **Package**: `github-mcp`
- **Purpose**: GitHub API operations
- **API Key**: `GITHUB_TOKEN`

### codebase-map
- **Package**: `mcp-codebase-map`
- **Purpose**: Code indexing
- **Storage**: `.ai/codebase-map.db`
- **Note**: Slow startup (30s timeout)

### playwright
- **Package**: `@playwright/mcp`
- **Purpose**: Browser automation
- **Mode**: Headless
- **Port**: 3001

### computer-control (Disabled)
- **Package**: `computer-use-mcp`
- **Purpose**: Desktop automation
- **Status**: Disabled by default

## Configuration

All servers configured in `~/.opencode/opencode.json` under the `mcp` section.

### Enable/Disable
```json
"mcp": {
  "server-name": {
    "enabled": true  // or false
  }
}
```

### Environment Variables
```bash
# Search APIs
TAVILY_API_KEY=tvly-xxxxx
PERPLEXITY_API_KEY=pplx-xxxxx

# GitHub
GITHUB_TOKEN=ghp_xxxxx

# PostgreSQL
POSTGRES_CONNECTION_STRING=postgresql://postgres:postgres@localhost:5432/opencode_taskbus
```

## Preflight Check

Run preflight to validate all MCPs:
```bash
python mcp_preflight.py
```

Expected output:
```
[PREFLIGHT] OK   taskbus
[PREFLIGHT] OK   parallel
[PREFLIGHT] OK   context-compactor
[PREFLIGHT] OK   memory
[PREFLIGHT] OK   sequential-thinking
[PREFLIGHT] OK   filesystem
[PREFLIGHT] OK   fetch
[PREFLIGHT] OK   postgres
[PREFLIGHT] OK   github
[PREFLIGHT] OK   tavily
[PREFLIGHT] OK   perplexity
[PREFLIGHT] WARN codebase-map: timeout 30s (non-blocking)
[PREFLIGHT] WARN playwright: timeout 30s (non-blocking)
[PREFLIGHT] PASSED
```

## Troubleshooting

### Server won't start
1. Check if the file exists at the configured path
2. Verify Node.js/Python is in PATH
3. Check API keys are set in environment

### Timeout during preflight
- Increase timeout in `mcp_preflight.py` DEFAULT_TIMEOUTS
- Some servers (codebase-map, playwright) are slow to initialize

### Context overflow
- Ensure `context-compactor` is enabled
- Check `context_get_stats` for utilization percentage
- Force compaction with `context_compact_now`
