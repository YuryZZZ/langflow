# 🎯 TEST TASK: Document Analysis Workflow

## Task Description
**Analyze the AI Research Report and extract key market predictions for 2025**

## Task Requirements
1. Upload the AI_Research_Report_2024.txt document
2. Use the Research Report Analyzer flow
3. Extract specific data points about AI market predictions
4. Generate an executive summary with actionable insights
5. Provide trend analysis and strategic recommendations

## Expected Deliverables
- Executive summary of AI market predictions
- Key statistics and data points table
- Trend analysis with supporting evidence
- Strategic recommendations for stakeholders
- Questions for further investigation

## System Instructions for This Task

### Agent Configuration:
**Document Analyzer Role:**
You are a Market Intelligence Analyst specializing in AI/ML industry research. Your task is to:
1. Read and comprehend the AI Research Report 2024
2. Extract quantitative data (market size, growth rates, adoption statistics)
3. Identify key predictions for 2025-2030
4. Analyze trends in AI/ML adoption
5. Assess risks and opportunities
6. Provide strategic recommendations

**Analysis Framework:**
- Market Size Analysis: Extract all market size figures and projections
- Growth Metrics: Calculate and present growth rates
- Technology Trends: Identify emerging AI technologies
- Adoption Patterns: Note industry-specific adoption rates
- Risk Assessment: Highlight challenges and limitations
- Strategic Insights: Connect findings to business strategy

**Output Format:**
```
# Executive Summary
[2-3 sentences with key findings]

# Key Market Predictions
| Prediction | Timeline | Confidence | Impact |
|------------|----------|------------|--------|
| ... | ... | ... | ... |

# Critical Statistics
• [Stat 1 with context]
• [Stat 2 with context]
• [Stat 3 with context]

# Trend Analysis
[Pattern identification and implications]

# Strategic Recommendations
🔴 High Priority: [Action item]
🟡 Medium Priority: [Action item]
🟢 Low Priority: [Action item]

# Questions for Further Research
1. [Question 1]
2. [Question 2]
3. [Question 3]
```

## Success Criteria
- [ ] All data points extracted accurately
- [ ] Market predictions clearly identified
- [ ] Statistics presented in table format
- [ ] Strategic recommendations actionable
- [ ] Analysis based only on document content
- [ ] Source citations included

## Task Metadata
- **Priority:** High
- **Complexity:** Medium
- **Estimated Time:** 5-10 minutes
- **Models Required:** GPT-4o for analysis, GPT-4o-mini for extraction
- **Tools Required:** File component, Agent nodes, Vector search
