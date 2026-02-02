# 👁️ Visual Guide - Seeing Connected Agents in Langflow

## How to View the 5-Level Hybrid System Visually

### Method 1: Langflow Web UI (Recommended)

#### Step 1: Start Langflow
```bash
# Start the server
python -m langflow run

# Or use the batch file
start_langflow.bat
```

#### Step 2: Open Browser
```
http://localhost:7860
```

#### Step 3: Import the Flow
1. Click **"My Files"** (left sidebar)
2. Click **"New Flow"** button
3. Select **"Import"**
4. Choose file: `agent/workflows/hybrid_5level_complete.json`
5. Click **"Import"**

#### Step 4: View Visual Graph
Once imported, you'll see:

```
┌─────────────────────────────────────────────────────────────────┐
│                    LANGFLOW VISUAL EDITOR                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   [🎯 Orchestrator] ←── Master control node                     │
│         │                                                       │
│    ┌────┴────┬────────┬────────┬────────┐                       │
│    ▼         ▼        ▼        ▼        ▼                       │
│ [P1]      [P2]     [P3]     [P4]     [P5]   ← 5 Planners       │
│ Arch      Sec      Work      Log      Impl                     │
│    │         │        │        │        │                       │
│    └────┬────┘        │        │        │                       │
│         ▼             │        │        │                       │
│   [🏗️ Architect] ─────┘        │        │                       │
│         │                       │        │                       │
│         ▼                       │        │                       │
│   [📦 Components]               │        │                       │
│         │                       │        │                       │
│         ▼                       │        │                       │
│   [🎨 Interface]                │        │                       │
│         │                       │        │                       │
│         ▼                       │        │                       │
│   [🗄️ Data Model] ─────────────┴────────┘                       │
│         │                                                       │
│    ┌────┼────┬────────┬────────┬────────┬────────┐              │
│    ▼    ▼    ▼        ▼        ▼        ▼        ▼              │
│  [C1] [C2] [C3]     [C4]     [C5]     [C6]       ← 6 Coders    │
│ Back  Front DB      Sec      Fast      Integ                    │
│    │    │    │       │        │        │                        │
│    └────┴────┴───────┴────────┴────────┘                        │
│                   │                                             │
│                   ▼                                             │
│            [🔍 Code Review]                                     │
│                   │                                             │
│                   ▼                                             │
│            [🔒 Security Review]                                 │
│                   │                                             │
│                   ▼                                             │
│            [🧪 Testing]                                         │
│                   │                                             │
│                   ▼                                             │
│            [📝 Documentation]                                   │
│                   │                                             │
│            ┌──────┴──────┐                                      │
│            ▼             ▼                                      │
│      [✓ Validator 1] [✓ Validator 2]                           │
│           Google      Anthropic                                 │
│            │             │                                      │
│            └──────┬──────┘                                      │
│                   ▼                                             │
│            [📊 Output Aggregator]                               │
│                   │                                             │
│                   ▼                                             │
│            [🎯 Final Output]                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### What You'll See:

#### 🟦 **Level 1 - Blue Nodes** (Control)
- **Orchestrator** - Large node at top
- Connected to all 5 planners with arrows

#### 🟨 **Level 2 - Yellow Nodes** (Parallel Planning)
- 5 planner nodes side by side
- All receiving from orchestrator
- All feeding into Level 3

#### 🟩 **Level 3 - Green Nodes** (Sequential Design)
- 4 designer nodes in vertical chain
- Arrows showing sequential flow
- Last node (Data) branches to 6 coders

#### 🟪 **Level 4 - Purple Nodes** (Parallel Coding)
- 6 coder nodes in row
- All receiving from Data Designer
- All feeding into Reviewer

#### 🟧 **Level 5 - Orange Nodes** (Sequential Review)
- 4 reviewer nodes in vertical chain
- Code → Security → Testing → Documentation
- Final node feeds to validators

#### 🟥 **Level 6 - Red Nodes** (Validation)
- 2 validator nodes side by side
- Both feeding into Aggregator

---

### Method 2: Visual Node Indicators

Each node in Langflow shows:

```
┌──────────────────────────────┐
│  🤖 Agent Name               │
│  ───────────────────────────│
│  Model: kimi-k2.5            │
│  Layer: 2 (Parallel)         │
│  Status: ✅ Ready            │
│                              │
│  [▶️ Run] [⚙️ Config]        │
└──────────────────────────────┘
         │
         │ Arrow shows data flow
         ▼
┌──────────────────────────────┐
│  Next Agent                  │
└──────────────────────────────┘
```

### Method 3: Connection Lines

**Different line colors show relationship types:**

- **→ Solid Arrow**: Sequential flow (wait for completion)
- **⇢ Dashed Arrow**: Parallel flow (concurrent execution)
- **⇒ Thick Arrow**: Data passing
- **⟿ Curved Arrow**: Cross-layer communication
- **⤴ Bi-directional**: Memory sync (to/from Memory Hub)

---

### Method 4: Interactive Features

#### Hover Over Node:
Shows tooltip:
```
Agent: L3-S1: System Architect
Model: google/gemini-3-pro
Layer: 3 (Sequential)
Status: Idle
Inputs: 5 planners
Outputs: designer_components
Execution: ~400s
```

#### Click Node:
Opens configuration panel:
```
┌─────────────────────────────────────┐
│ 🔧 Agent Configuration              │
├─────────────────────────────────────┤
│ Name: System Architect              │
│ ID: designer_architecture           │
│                                     │
│ Model:                              │
│   Provider: Google                  │
│   Model: gemini-3-pro-preview       │
│   Context: 1,000,000 tokens         │
│                                     │
│ Execution:                          │
│   Mode: Sequential                  │
│   Order: 1 of 4                     │
│   Dependencies: 5 planners          │
│                                     │
│ [View Prompt] [View Connections]    │
└─────────────────────────────────────┘
```

#### Right-Click Node:
Context menu:
- **Run This Agent** - Execute individually
- **View Logs** - See execution history
- **Highlight Connections** - Show all connected nodes
- **Configure** - Edit settings
- **Disable** - Temporarily disable

---

### Method 5: Layer View Toggle

In the toolbar, click **"Layers"** to see:

```
☑️ Show All Layers
☑️ Level 1: Orchestration
☑️ Level 2: Planning (5 parallel agents)
☑️ Level 3: Design (4 sequential agents)
☑️ Level 4: Implementation (6 parallel agents)
☑️ Level 5: Review (4 sequential agents)
☑️ Level 6: Validation (2 parallel agents)
☐ Show Support Agents (Researcher, Analyst)
☐ Show Memory Hub
```

**Click to toggle visibility of each layer**

---

### Method 6: Execution Visualization

When running, nodes animate:

```
BEFORE EXECUTION:
┌──────────┐
│ Agent    │ ○ Gray = Idle
└──────────┘

DURING EXECUTION:
┌──────────┐
│ Agent    │ 🟡 Yellow = Running
│ ▓▓▓░░░░░ │ Progress bar
└──────────┘

COMPLETED:
┌──────────┐
│ Agent    │ 🟢 Green = Done
│ ✓ Success│
└──────────┘

ERROR:
┌──────────┐
│ Agent    │ 🔴 Red = Error
│ ✗ Failed │
└──────────┘
```

---

### Method 7: Mini-Map Navigation

Bottom-right corner shows mini-map:

```
┌─────────────┐
│  ┌─┐ ┌─┐   │  ◄ Current view
│  │ │ │ │   │
│  └─┘ └─┘   │
│    ┌───┐    │
│    └───┘    │
│ [═══]      │  ◄ Zoom slider
└─────────────┘
```

**Click and drag** the view box to navigate large flows

---

### Method 8: Connection Inspector

Click any arrow (connection line):

```
┌─────────────────────────────────────┐
│ 🔗 Connection Details               │
├─────────────────────────────────────┤
│ From: designer_data                 │
│ To: coder_backend                   │
│                                     │
│ Type: provides_specification        │
│ Layer Transition: 3 → 4             │
│                                     │
│ Data Passed:                        │
│   - Database schema                 │
│   - API contracts                   │
│   - Data models                     │
│                                     │
│ Execution:                          │
│   Mode: Parallel dispatch           │
│   Delay: 0s (immediate)             │
└─────────────────────────────────────┘
```

---

### Method 9: Export Visual Diagram

**Option 1: Screenshot**
```
File → Export → Screenshot
```

**Option 2: SVG Export**
```
File → Export → SVG
```
Creates scalable vector graphic of the entire flow

**Option 3: JSON with positions**
```
File → Export → JSON
```
Includes x,y coordinates for custom visualization

---

### Method 10: Custom Visualization (Python)

Create visual representation programmatically:

```python
import json
import matplotlib.pyplot as plt
import networkx as nx

# Load flow
with open('agent/workflows/hybrid_5level_complete.json') as f:
    flow = json.load(f)

# Create graph
G = nx.DiGraph()

# Add nodes with positions
for comp in flow['components']:
    G.add_node(
        comp['id'],
        name=comp['name'],
        layer=comp.get('layer', 0),
        pos=(comp['position']['x'], -comp['position']['y'])  # Flip Y
    )

# Add edges
for edge in flow['edges']:
    if isinstance(edge, dict) and 'source' in edge:
        G.add_edge(edge['source'], edge['target'], 
                  type=edge.get('type', 'default'))

# Draw
pos = nx.get_node_attributes(G, 'pos')
colors = [G.nodes[n].get('layer', 0) for n in G.nodes()]

plt.figure(figsize=(20, 16))
nx.draw_networkx_nodes(G, pos, node_color=colors, 
                      cmap='tab10', node_size=3000, alpha=0.8)
nx.draw_networkx_edges(G, pos, edge_color='gray', 
                      arrows=True, arrowsize=20, width=1.5)
nx.draw_networkx_labels(G, pos, 
                       labels={n: G.nodes[n]['name'][:15] for n in G.nodes()},
                       font_size=8)

plt.title('5-Level Hybrid Multi-Agent System', fontsize=16)
plt.axis('off')
plt.tight_layout()
plt.savefig('agent_visualization.png', dpi=150, bbox_inches='tight')
plt.show()

print("✅ Visualization saved: agent_visualization.png")
```

---

## Quick Visual Reference

### Icon Legend

| Icon | Meaning |
|------|---------|
| 🎯 | Orchestrator (Control) |
| 🧠 | Planner (Strategy) |
| 🏗️ | Designer (Architecture) |
| 💻 | Coder (Implementation) |
| 🔍 | Reviewer (Quality) |
| ✓ | Validator (Verification) |
| 🔬 | Researcher (Internet) |
| 📊 | Analyst (Data) |
| 🧠 | Memory Hub |
| 📊 | Aggregator |

### Color Legend

| Color | Layer | Type |
|-------|-------|------|
| 🔵 Blue | 1 | Orchestration |
| 🟡 Yellow | 2 | Planning (Parallel) |
| 🟢 Green | 3 | Design (Sequential) |
| 🟣 Purple | 4 | Coding (Parallel) |
| 🟠 Orange | 5 | Review (Sequential) |
| 🔴 Red | 6 | Validation (Parallel) |
| ⚪ Gray | Support | Research/Analysis |

### Arrow Legend

| Arrow | Meaning |
|-------|---------|
| → | Sequential dependency |
| ⇢ | Parallel dispatch |
| ⟿ | Memory sync |
| ⤏ | Cross-layer call |

---

## Troubleshooting Visual Issues

### **"Can't see all agents"**
→ Zoom out (Ctrl + -) or use mini-map

### **"Connections not showing"**
→ Toggle: View → Show All Connections

### **"Nodes overlapping"**
→ Click: Layout → Auto-Arrange

### **"Can't read labels"**
→ Zoom in (Ctrl + +) or hover for tooltip

### **"Flow too large"**
→ Use layer filters to show one layer at a time

---

## Summary

**5 Ways to See Agents Connected:**
1. ✅ **Web UI** - Import and view interactive graph
2. ✅ **Connection Lines** - Arrows show data flow
3. ✅ **Layer Toggle** - Show/hide by level
4. ✅ **Animation** - Watch execution in real-time
5. ✅ **Python Export** - Create custom visualizations

**Start here:**
```bash
python -m langflow run
# Then open http://localhost:7860
# Import: agent/workflows/hybrid_5level_complete.json
```

**You'll see all 22 agents fully connected!** 🎯
