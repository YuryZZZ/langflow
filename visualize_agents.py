#!/usr/bin/env python3
"""
Visualize the 5-Level Hybrid Agent System
Generates visual diagrams showing all connected agents
"""

import json
import sys
from pathlib import Path

def create_ascii_visualization():
    """Create ASCII art visualization of the 5-level system"""
    
    viz = """
╔══════════════════════════════════════════════════════════════════════════╗
║         5-LEVEL HYBRID MULTI-AGENT SYSTEM - VISUAL DIAGRAM              ║
║                   All 22 Agents Fully Connected                           ║
╚══════════════════════════════════════════════════════════════════════════╝

LEVEL 1: ORCHESTRATION (Sequential Control)
┌────────────────────────────────────────────────────────────────────┐
│                                                                    │
│                    ┌──────────────────────┐                        │
│                    │   🎯 ORCHESTRATOR    │                        │
│                    │   Kimi K2.5          │                        │
│                    │   (Master Control)   │                        │
│                    └──────────┬───────────┘                        │
│                               │                                    │
│         ┌─────────────────────┼─────────────────────┐              │
│         │                     │                     │              │
│         ▼                     ▼                     ▼              │
└────────────────────────────────────────────────────────────────────┘

LEVEL 2: PARALLEL PLANNING (5 Agents Concurrent)
┌────────────────────────────────────────────────────────────────────┐
│                                                                    │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────┐│
│   │  🧠 P1   │  │  🧠 P2   │  │  🧠 P3   │  │  🧠 P4   │  │ 🧠 P5││
│   │ Arch     │  │ Security │  │ Workflow │  │ Logic    │  │ Impl ││
│   │ Gemini   │  │ Claude   │  │ Kimi     │  │ DeepSeek │  │ GLM  ││
│   │ Pro      │  │ Sonnet   │  │ K2.5     │  │ V3.2     │  │ 4.7  ││
│   └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──┬───┘│
│        │             │             │             │            │    │
│        └─────────────┴─────────────┴─────────────┴────────────┘    │
│                               │                                     │
│                               ▼                                     │
└────────────────────────────────────────────────────────────────────┘

LEVEL 3: SEQUENTIAL DESIGN (4 Agents Chain)
┌────────────────────────────────────────────────────────────────────┐
│                                                                    │
│  ┌──────────────────┐                                             │
│  │ 🏗️ Architect     │                                             │
│  │ Gemini Pro       │                                             │
│  └────────┬─────────┘                                             │
│           │                                                        │
│           ▼                                                        │
│  ┌──────────────────┐                                             │
│  │ 📦 Components    │                                             │
│  │ GLM 4.7          │                                             │
│  └────────┬─────────┘                                             │
│           │                                                        │
│           ▼                                                        │
│  ┌──────────────────┐                                             │
│  │ 🎨 Interface     │                                             │
│  │ Claude Sonnet    │                                             │
│  └────────┬─────────┘                                             │
│           │                                                        │
│           ▼                                                        │
│  ┌──────────────────┐                                             │
│  │ 🗄️ Data Model    │                                             │
│  │ DeepSeek V3.2    │                                             │
│  └────────┬─────────┘                                             │
│           │                                                        │
│     ┌─────┴───────┬────────┬────────┬────────┬────────┐          │
│     ▼             ▼        ▼        ▼        ▼        ▼          │
└────────────────────────────────────────────────────────────────────┘

LEVEL 4: PARALLEL IMPLEMENTATION (6 Agents Concurrent)
┌────────────────────────────────────────────────────────────────────┐
│                                                                    │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌──────┐ │
│  │💻 Back │ │💻 Front│ │💻 DB   │ │💻 Sec  │ │💻 Fast │ │💻 Int│ │
│  │ Kimi   │ │ GLM    │ │ DeepS  │ │ Claude │ │ Gemini │ │ GLM  │ │
│  │ K2.5   │ │ 4.7    │ │ V3.2   │ │ Sonnet │ │ Flash  │ │ 4.7  │ │
│  └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘ └───┬──┘ │
│      │          │          │          │          │          │     │
│      └──────────┴──────────┴──────────┴──────────┴──────────┘     │
│                               │                                     │
│                               ▼                                     │
└────────────────────────────────────────────────────────────────────┘

LEVEL 5: SEQUENTIAL REVIEW (4 Agents Chain)
┌────────────────────────────────────────────────────────────────────┐
│                                                                    │
│  ┌──────────────────┐                                             │
│  │ 🔍 Code Review   │                                             │
│  │ Claude Sonnet    │                                             │
│  └────────┬─────────┘                                             │
│           │                                                        │
│           ▼                                                        │
│  ┌──────────────────┐                                             │
│  │ 🔒 Security Rev  │                                             │
│  │ Claude Sonnet    │                                             │
│  └────────┬─────────┘                                             │
│           │                                                        │
│           ▼                                                        │
│  ┌──────────────────┐                                             │
│  │ 🧪 Testing       │                                             │
│  │ GLM 4.7          │                                             │
│  └────────┬─────────┘                                             │
│           │                                                        │
│           ▼                                                        │
│  ┌──────────────────┐                                             │
│  │ 📝 Documentation │                                             │
│  │ Kimi K2.5        │                                             │
│  └────────┬─────────┘                                             │
│           │                                                        │
│      ┌────┴────┐                                                   │
│      ▼         ▼                                                   │
└────────────────────────────────────────────────────────────────────┘

LEVEL 6: PARALLEL VALIDATION (2 Agents Concurrent)
┌────────────────────────────────────────────────────────────────────┐
│                                                                    │
│  ┌──────────────────┐      ┌──────────────────┐                    │
│  │ ✓ Validator G    │      │ ✓ Validator A    │                    │
│  │ Gemini Flash     │      │ Claude Haiku     │                    │
│  │ (Google Family)  │      │ (Anthropic Fam)  │                    │
│  └────────┬─────────┘      └────────┬─────────┘                    │
│           │                         │                              │
│           └───────────┬─────────────┘                              │
│                       ▼                                            │
│            ┌──────────────────┐                                    │
│            │ 📊 Aggregator    │                                    │
│            │ (Final Output)   │                                    │
│            └────────┬─────────┘                                    │
│                     │                                              │
│                     ▼                                              │
│            ┌──────────────────┐                                    │
│            │ 📦 Comprehensive │                                    │
│            │ Output (No Trunc)│                                    │
│            └──────────────────┘                                    │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘

SUPPORT AGENTS (Cross-Layer)
┌────────────────────────────────────────────────────────────────────┐
│                                                                    │
│  ┌──────────────────┐    ┌──────────────────┐                     │
│  │ 🔬 Researcher    │    │ 📊 Analyst       │                     │
│  │ Perplexity       │    │ Gemini Pro       │                     │
│  │ Sonar Pro        │    │ (Internet)       │                     │
│  │ Internet + Cite  │    │ Grounding        │                     │
│  └────────┬─────────┘    └────────┬─────────┘                     │
│           │                       │                                │
│           └───────────┬───────────┘                                │
│                       ▼                                            │
│            ┌──────────────────┐                                    │
│            │ 🧠 Memory Hub    │                                    │
│            │ MCP Storage      │                                    │
│            │ (All agents)     │                                    │
│            └──────────────────┘                                    │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘

CONNECTION SUMMARY
═══════════════════════════════════════════════════════════════════
Total Agents:        22
Total Connections:   50+
Execution Modes:     Parallel (3 groups) + Sequential (2 chains)
Internet Models:     5 (Researcher, Analyst, P1, Coder-Fast, Validator)
API Keys:            7 configured
Max Output Size:     Unlimited (chunked storage)
═══════════════════════════════════════════════════════════════════

LEGEND
═══════════════════════════════════════════════════════════════════
🎯 Orchestrator    🧠 Planner      🏗️ Designer     💻 Coder
🔍 Reviewer        ✓ Validator    🔬 Researcher    📊 Analyst
🧠 Memory Hub      📊 Aggregator

→ Sequential flow    ⇢ Parallel dispatch    ⟿ Memory sync
═══════════════════════════════════════════════════════════════════
"""
    
    return viz

def create_connection_summary():
    """Create connection summary table"""
    
    summary = """
AGENT CONNECTION MATRIX
═══════════════════════════════════════════════════════════════════════════

AGENT                    │ LAYER │ CONNECTS TO                          │ TYPE
═════════════════════════╪═══════╪══════════════════════════════════════╪══════════
orchestrator             │   1   │ All 5 planners                       │ Dispatch
planner_1                │   2   │ designer_architecture                │ Parallel
planner_2                │   2   │ designer_architecture + coder_sec    │ Parallel
planner_3                │   2   │ designer_architecture + designer_int │ Parallel
planner_4                │   2   │ designer_data + coder_deepseek       │ Parallel
planner_5                │   2   │ designer_components + tester         │ Parallel
designer_architecture    │   3   │ designer_components                  │ Sequential
designer_components      │   3   │ designer_interface                   │ Sequential
designer_interface       │   3   │ designer_data                        │ Sequential
designer_data            │   3   │ All 6 coders                         │ Branch
coder_backend            │   4   │ reviewer_code                        │ Parallel
coder_frontend           │   4   │ reviewer_code                        │ Parallel
coder_database           │   4   │ reviewer_code                        │ Parallel
coder_security           │   4   │ reviewer_code                        │ Parallel
coder_fast               │   4   │ reviewer_code                        │ Parallel
coder_integration        │   4   │ reviewer_code                        │ Parallel
reviewer_code            │   5   │ reviewer_security                    │ Sequential
reviewer_security        │   5   │ tester                               │ Sequential
tester                   │   5   │ documenter                           │ Sequential
documenter               │   5   │ Both validators                      │ Branch
validator_google         │   6   │ output_aggregator                    │ Parallel
validator_anthropic      │   6   │ output_aggregator                    │ Parallel
output_aggregator        │   -   │ orchestrator                         │ Report
researcher               │   *   │ All layers (support)                 │ Support
analyst                  │   *   │ Architecture & data (support)        │ Support
memory_hub               │   *   │ All agents (storage)                 │ Storage
═══════════════════════════════════════════════════════════════════════════

TOTAL: 22 agents, 50+ connections, 6 layers
"""
    
    return summary

def create_layer_statistics():
    """Create layer statistics"""
    
    stats = """
LAYER STATISTICS
═══════════════════════════════════════════════════════════════════════════

Layer 1 - Orchestration
  ├─ Agents: 1
  ├─ Mode: Sequential
  ├─ Execution: ~60s
  └─ Output: Task decomposition

Layer 2 - Planning (PARALLEL)
  ├─ Agents: 5 (P1-P5)
  ├─ Mode: Parallel
  ├─ Execution: ~300s (concurrent)
  └─ Output: 5 specialized plans

Layer 3 - Design (SEQUENTIAL)
  ├─ Agents: 4 (S1-S4)
  ├─ Mode: Sequential Chain
  ├─ Execution: ~1,400s (chained)
  └─ Output: Complete specifications

Layer 4 - Implementation (PARALLEL)
  ├─ Agents: 6 (C1-C6)
  ├─ Mode: Parallel
  ├─ Execution: ~600s (concurrent)
  └─ Output: 6 code modules

Layer 5 - Review (SEQUENTIAL)
  ├─ Agents: 4 (R1-R4)
  ├─ Mode: Sequential Chain
  ├─ Execution: ~1,700s (chained)
  └─ Output: Reviewed, tested, documented code

Layer 6 - Validation (PARALLEL)
  ├─ Agents: 2 (V1-V2)
  ├─ Mode: Parallel
  ├─ Execution: ~300s (concurrent)
  └─ Output: Cross-validated results

Support Layer
  ├─ Agents: 2 (Researcher, Analyst)
  ├─ Mode: Support (on-demand)
  └─ Provides: Internet research, data analysis

Memory Layer
  ├─ Component: Memory Hub
  ├─ Function: Cross-layer storage
  └─ Prevents: Truncation

═══════════════════════════════════════════════════════════════════════════

Total Execution Time: 3,600-7,200 seconds (1-2 hours)
Parallel Speedup: ~4.5x vs sequential
Memory Usage: Unlimited (chunked)
Output Size: Unlimited (no truncation)
"""
    
    return stats

def main():
    """Main visualization function"""
    
    print("\n" + "="*80)
    print(" "*20 + "AGENT VISUALIZATION SYSTEM")
    print("="*80)
    
    # Print ASCII diagram
    print("\n" + create_ascii_visualization())
    
    # Print connection summary
    print(create_connection_summary())
    
    # Print layer statistics
    print(create_layer_statistics())
    
    print("\n" + "="*80)
    print("To see interactive visualization:")
    print("  1. Run: python -m langflow run")
    print("  2. Open: http://localhost:7860")
    print("  3. Import: agent/workflows/hybrid_5level_complete.json")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
