---
description: "CODER (DeepSeek) - Complex logic."
model: deepseek/deepseek-chat
mode: primary
maxTokens: 8192
temperature: 0.8
maxSteps: 100
tools:
  edit: true
  write: true
  read: true
  bash: true
  webfetch: true
  mcp: true
  todowrite: true
permission:
  read: allow
---

# DEPRECATED: coder-deepseek

## MIGRATION NOTICE

This agent file is **DEPRECATED** as of Ver05.1 FLUID Architecture.

### Why Deprecated?
The FLUID architecture separates:
- **ROLE** (what to do) → `roles/coder.md`
- **MODEL** (which LLM) → Selected dynamically from pools by planner

### Migration Path
```
OLD: @coder-deepseek (hardcoded to DeepSeek)
NEW: @coder(pool=CODING_STANDARD) (model selected from pool)
```

### What Happens Now?
When this agent is called, the system will:
1. Load the role definition from `roles/coder.md`
2. Select a model from `CODING_STANDARD` pool based on availability
3. Execute with automatic failover if model fails

### Pool Priority (CODING_STANDARD)
1. google/gemini-2.5-flash (fastest, cheapest)
2. deepseek/deepseek-chat (original model for this role)
3. zai/glm-4.6 (fallback)

### For Backwards Compatibility
This file still works but redirects to the role-based system.

---

## Legacy System Instructions (Preserved for Reference)

The following instructions are loaded from `roles/coder.md`:

**Role:** Standard Implementation Worker
**Purpose:** Write clean, working code for simple to medium tasks
**Workflow:** Read → Understand → Implement → Verify

See `roles/coder.md` for complete system instructions.
