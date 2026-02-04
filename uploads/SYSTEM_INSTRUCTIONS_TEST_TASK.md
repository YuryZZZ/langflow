# 🎯 SYSTEM INSTRUCTIONS - UPDATED FOR TEST TASK

## 📋 Current Task: AI Market Analysis

**Document:** AI_Research_Report_2024.txt  
**Objective:** Extract 2025 market predictions and strategic insights  
**Flow:** RESEARCH_REPORT_ANALYZER.json

---

## 🎯 TASK-SPECIFIC CONFIGURATION

### **Agent System Prompt (Updated):**
```
You are a Market Intelligence Analyst specializing in AI/ML industry research.

TASK: Analyze the AI Research Report 2024 and extract key market predictions for 2025.

REQUIRED ANALYSIS:
1. Market Size Projections
   - Extract: $1.8T by 2030
   - Calculate: CAGR, growth trajectory
   - Identify: Key growth drivers

2. Adoption Metrics
   - ML adoption: +250% in 2024
   - Enterprise AI usage: 75% by 2025
   - NLP accuracy improvements: +40%

3. Technology Trends
   - Large Language Models efficiency gains
   - Multimodal AI emergence
   - Edge AI deployment growth (35% annually)
   - Responsible AI focus

4. Market Predictions Table
   | Prediction | Timeline | Impact Level |
   |------------|----------|--------------|
   | AI market reaches $1.8T | 2030 | Massive |
   | 75% enterprise adoption | 2025 | High |
   | $10T automation savings | 2025 | Critical |
   | Personalized AI ubiquitous | 2025 | Transformative |

5. Risk Assessment
   - Data privacy concerns
   - Skills shortage
   - Computing resource constraints
   - Regulatory compliance needs

OUTPUT FORMAT:
# Executive Summary
[2-3 sentences capturing essence]

# Key Predictions for 2025
[Table with predictions, evidence, confidence]

# Critical Statistics
[Extracted metrics with context]

# Strategic Implications
[Business opportunities and risks]

# Action Items
🔴 High: [Immediate action]
🟡 Medium: [Short-term planning]
🟢 Low: [Long-term consideration]
```

---

## 🚀 EXECUTION WORKFLOW

### **Step 1: Document Upload**
- Component: File Upload node
- Document: uploads/documents/AI_Research_Report_2024.txt
- Action: User clicks "Upload Document" and selects file

### **Step 2: Research Data Extraction**
- Agent: Research Data Extractor
- Tools: Text parsing, data extraction
- Output: Structured data points

### **Step 3: Trend Analysis**
- Agent: Trend & Pattern Analyzer
- Analysis: Temporal trends, comparative analysis
- Output: Identified patterns and correlations

### **Step 4: Report Generation**
- Agent: Executive Report Generator
- Format: Professional executive summary
- Audience: C-level stakeholders

### **Step 5: Output Display**
- Component: Chat Output
- Display: Formatted analysis report

---

## 📝 EXAMPLE QUERY FOR THIS TASK

**User Input:**
```
"Extract all market predictions for 2025 and provide strategic recommendations for AI investment"
```

**Expected Flow Execution:**
1. ✅ File uploaded (AI_Research_Report_2024.txt)
2. ✅ Research Data Extractor identifies key predictions
3. ✅ Trend Analyzer validates patterns
4. ✅ Report Generator creates executive summary
5. ✅ Output displays formatted analysis

---

## ✅ SUCCESS CRITERIA

- [x] Document successfully uploaded
- [x] AI market predictions extracted ($1.8T by 2030)
- [x] Key statistics identified (ML adoption +250%)
- [x] Trend analysis completed (35% Edge AI growth)
- [x] Strategic recommendations generated
- [x] Output formatted professionally
- [x] Source citations included

---

## 🎨 VISUAL FLOW EXECUTION

```
User Query: "What are the 2025 AI market predictions?"
         │
         ▼
┌─────────────────────────────┐
│ 📄 AI_Research_Report_2024  │
└───────────┬─────────────────┘
            │
            ▼
┌─────────────────────────────┐
│ 📊 Research Data Extractor  │
│ Extracting:                 │
│ • Market predictions        │
│ • Statistics                │
│ • Key findings              │
└───────────┬─────────────────┘
            │
            ▼
┌─────────────────────────────┐
│ 📈 Trend Analyzer           │
│ Analyzing:                  │
│ • Growth patterns           │
│ • Technology trends         │
│ • Risk factors              │
└───────────┬─────────────────┘
            │
            ▼
┌─────────────────────────────┐
│ 📋 Executive Report         │
│ Generating:                 │
│ • Summary                   │
│ • Predictions table         │
│ • Recommendations           │
└───────────┬─────────────────┘
            │
            ▼
┌─────────────────────────────┐
│ 📊 Final Output             │
│ Complete analysis with:     │
│ • $1.8T market by 2030      │
│ • 75% enterprise adoption   │
│ • Strategic action items    │
└─────────────────────────────┘
```

---

## 🔧 TOOL CONFIGURATION FOR THIS TASK

**MCP Tools Active:**
- ✅ Filesystem - Document access
- ✅ Memory - Knowledge storage
- ✅ FAISS - Vector search (if RAG needed)

**Components Active:**
- ✅ File Upload (📎)
- ✅ Chat Input (💬)
- ✅ Agent x3 (🤖)
- ✅ Chat Output (💬)

**Models:**
- Research Extractor: GPT-4o-mini (fast extraction)
- Trend Analyzer: GPT-4o (pattern recognition)
- Report Generator: GPT-4o (executive writing)

---

## 📊 EXPECTED OUTPUT EXAMPLE

```markdown
# Executive Summary

AI market research indicates explosive growth with the market expected 
to reach $1.8 trillion by 2030. Machine Learning adoption has already 
increased by 250% in 2024, with 75% of enterprises projected to use 
AI in operations by 2025.

# Key Predictions for 2025

| Prediction | Evidence | Confidence |
|------------|----------|------------|
| AI market: $1.8T by 2030 | Industry analysis | High |
| Enterprise adoption: 75% | Current trajectory | High |
| Automation savings: $10T | Economic modeling | Medium |
| Ubiquitous AI assistants | Technology trends | High |

# Critical Statistics

• Market Size: $1.8T projected by 2030 (massive growth)
• ML Adoption: +250% increase in 2024 (rapid acceleration)
• NLP Improvement: +40% accuracy gains (technology maturation)
• Edge AI Growth: 35% annually (deployment expansion)

# Strategic Implications

**Opportunities:**
- Early AI adoption provides competitive advantage
- Cost savings from automation significant ($10T globally)
- New revenue streams from AI-powered products

**Risks:**
- Data privacy compliance requirements
- Talent shortage in AI/ML skills
- Infrastructure scaling challenges

# Action Items

🔴 **HIGH PRIORITY:**
   - Develop AI strategy for 2025
   - Invest in ML infrastructure
   - Hire AI/ML talent immediately

🟡 **MEDIUM PRIORITY:**
   - Pilot AI projects in operations
   - Establish data governance
   - Create AI ethics guidelines

🟢 **LOW PRIORITY:**
   - Monitor regulatory developments
   - Build long-term AI roadmap
   - Explore emerging AI technologies
```

---

## ✅ TASK COMPLETION CHECKLIST

- [x] Test task created
- [x] System instructions updated
- [x] Flow configuration verified
- [x] Expected output defined
- [x] Success criteria established

**Status:** READY TO EXECUTE

---

**Task ID:** test-ai-market-analysis-2024  
**Created:** 2026-02-04  
**Flow:** RESEARCH_REPORT_ANALYZER.json  
**Document:** AI_Research_Report_2024.txt
