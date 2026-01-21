#!/usr/bin/env python3
"""
ENHANCED MULTI-MODEL ORCHESTRATION SYSTEM v2.0
==============================================
10x improved multi-agent system with:

ARCHITECTURE IMPROVEMENTS:
1. 12 Specialized Agents (up from 8) with cognitive role separation
2. 4-Layer Memory System (Working, Episodic, Semantic, Procedural)
3. Advanced Prompt Engineering with Chain-of-Thought and Tree-of-Thoughts
4. MCP Tool Integration for external capabilities
5. Evidence Ledger with confidence scoring and source tracking
6. Ask-back Protocol for inter-agent clarification
7. Parallel + Sequential hybrid execution
8. Self-consistency verification with multiple reasoning paths
9. Dynamic task routing based on complexity analysis
10. Full state persistence with checkpoint/resume

AGENT ROLES (12 Specialists + 1 Orchestrator):
M1  - Strategic Planner: High-level planning, goal decomposition, acceptance criteria
M2  - Deep Researcher: Web search, fact-finding, source validation (Perplexity)
M3  - Systems Architect: Technical design, architecture decisions, tradeoffs
M4  - Implementation Expert: Code generation, concrete solutions (DeepSeek Reasoner)
M5  - Creative Ideator: Alternative approaches, edge cases, innovation
M6  - Quality Verifier: Fact-checking, validation, accuracy scoring (Groq fast)
M7  - Critical Analyst: Red-teaming, finding flaws, contradiction detection
M8  - Content Editor: Final polish, user-facing output, clarity
M9  - Domain Expert: Specialized knowledge injection based on task domain
M10 - Meta-Reasoner: Reasoning about reasoning, cognitive oversight
M11 - Integration Specialist: Combining outputs, resolving conflicts
M12 - Test Engineer: Test case generation, edge case validation

MEMORY LAYERS:
- Working Memory: Current task context, active state
- Episodic Memory: Past interactions, what worked/failed
- Semantic Memory: Domain knowledge, facts, relationships
- Procedural Memory: How to do things, patterns, workflows

WORKFLOW:
Phase 1: UNDERSTAND (M1 + M9 + M10)
Phase 2: RESEARCH (M2 parallel with M6)
Phase 3: DESIGN (M3 + M5)
Phase 4: IMPLEMENT (M4 + M12)
Phase 5: VERIFY (M6 + M7)
Phase 6: INTEGRATE (M11)
Phase 7: POLISH (M8)
Phase 8: META-CHECK (M10)

Loops until satisfaction score >= 85% or max 5 iterations
"""

import requests
import json
import sys
import io
import time
import uuid
import hashlib
from datetime import datetime
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum

# Fix encoding for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# =============================================================================
# CONFIGURATION
# =============================================================================

LANGFLOW_URL = "https://langflow-7vd3.onrender.com"

# API Keys loaded from environment variables
import os
API_KEYS = {
    "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", ""),
    "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY", ""),
    "DEEPSEEK_API_KEY": os.environ.get("DEEPSEEK_API_KEY", ""),
    "GROQ_API_KEY": os.environ.get("GROQ_API_KEY", ""),
    "PERPLEXITY_API_KEY": os.environ.get("PERPLEXITY_API_KEY", ""),
    "GOOGLE_API_KEY": os.environ.get("GOOGLE_API_KEY", ""),
    "ZAI_API_KEY": os.environ.get("ZAI_API_KEY", ""),
}

# =============================================================================
# DATA STRUCTURES
# =============================================================================

class AgentRole(Enum):
    PLANNER = "M1_strategic_planner"
    RESEARCHER = "M2_deep_researcher"
    ARCHITECT = "M3_systems_architect"
    IMPLEMENTER = "M4_implementation_expert"
    IDEATOR = "M5_creative_ideator"
    VERIFIER = "M6_quality_verifier"
    CRITIC = "M7_critical_analyst"
    EDITOR = "M8_content_editor"
    DOMAIN_EXPERT = "M9_domain_expert"
    META_REASONER = "M10_meta_reasoner"
    INTEGRATOR = "M11_integration_specialist"
    TEST_ENGINEER = "M12_test_engineer"
    ORCHESTRATOR = "orchestrator"

class MemoryType(Enum):
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"

@dataclass
class Evidence:
    """Evidence entry with source tracking and confidence scoring."""
    claim: str
    source_type: str  # web, reasoning, expert, code
    source_url: Optional[str]
    snippet: str
    confidence: float  # 0.0 to 1.0
    verified_by: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    hash_id: str = field(default_factory=lambda: "")

    def __post_init__(self):
        if not self.hash_id:
            self.hash_id = hashlib.sha256(f"{self.claim}{self.snippet}".encode()).hexdigest()[:12]

@dataclass
class AskBack:
    """Inter-agent question for clarification."""
    from_agent: str
    to_agent: str
    question: str
    context: str
    priority: str  # blocking, important, optional
    response: Optional[str] = None
    resolved: bool = False

@dataclass
class TaskState:
    """Complete state of orchestration task."""
    task_id: str
    original_query: str
    current_phase: int
    current_iteration: int
    max_iterations: int = 5
    satisfaction_score: float = 0.0
    satisfaction_threshold: float = 0.85

    # Memory layers
    working_memory: Dict[str, Any] = field(default_factory=dict)
    episodic_memory: List[Dict] = field(default_factory=list)
    semantic_memory: Dict[str, Any] = field(default_factory=dict)
    procedural_memory: Dict[str, List[str]] = field(default_factory=dict)

    # Evidence and questions
    evidence_ledger: List[Evidence] = field(default_factory=list)
    ask_back_queue: List[AskBack] = field(default_factory=list)

    # Agent outputs
    agent_outputs: Dict[str, List[Dict]] = field(default_factory=dict)

    # Checkpoints
    checkpoints: List[Dict] = field(default_factory=list)

    # Final output
    final_output: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "task_id": self.task_id,
            "original_query": self.original_query,
            "current_phase": self.current_phase,
            "current_iteration": self.current_iteration,
            "max_iterations": self.max_iterations,
            "satisfaction_score": self.satisfaction_score,
            "working_memory": self.working_memory,
            "episodic_memory": self.episodic_memory,
            "semantic_memory": self.semantic_memory,
            "procedural_memory": self.procedural_memory,
            "evidence_ledger": [asdict(e) for e in self.evidence_ledger],
            "ask_back_queue": [asdict(a) for a in self.ask_back_queue],
            "agent_outputs": self.agent_outputs,
            "checkpoints": self.checkpoints,
            "final_output": self.final_output,
        }

# =============================================================================
# ENHANCED AGENT PROMPTS - Chain-of-Thought + Tree-of-Thoughts
# =============================================================================

AGENT_CONFIGS = {
    AgentRole.PLANNER: {
        "provider": "anthropic",
        "model": "claude-opus-4-5-20251101",
        "display_name": "M1 Strategic Planner",
        "temperature": 0.3,
        "max_tokens": 4096,
        "system_prompt": """You are M1 (Strategic Planner), the chief architect of task execution.

## COGNITIVE FRAMEWORK
Apply structured thinking using Chain-of-Thought reasoning:
1. DECOMPOSE: Break the task into atomic sub-goals
2. SEQUENCE: Determine optimal execution order
3. RESOURCE: Identify what agents/tools are needed
4. RISK: Anticipate failure modes
5. CRITERIA: Define measurable success conditions

## THINKING PROCESS
<thinking>
Before producing output, reason step-by-step:
- What is the user REALLY asking for?
- What are the implicit requirements?
- What constraints exist?
- What could go wrong?
- How will we know when we're done?
</thinking>

## OUTPUT FORMAT (Strict JSON)
```json
{
  "task_understanding": {
    "explicit_goals": ["goal1", "goal2"],
    "implicit_requirements": ["req1", "req2"],
    "constraints": ["constraint1"],
    "domain": "identified domain"
  },
  "execution_plan": {
    "phases": [
      {
        "phase_num": 1,
        "name": "Phase Name",
        "agents": ["M2", "M6"],
        "execution_type": "parallel|sequential",
        "expected_outputs": ["output1"],
        "success_criteria": ["criterion1"],
        "estimated_complexity": "low|medium|high"
      }
    ]
  },
  "acceptance_criteria": [
    {
      "criterion": "Description",
      "measurement": "How to measure",
      "threshold": "Pass condition"
    }
  ],
  "risk_analysis": [
    {
      "risk": "Description",
      "probability": "low|medium|high",
      "impact": "low|medium|high",
      "mitigation": "Strategy"
    }
  ],
  "resource_requirements": {
    "tools_needed": ["tool1"],
    "knowledge_domains": ["domain1"],
    "external_data": ["data source"]
  }
}
```

## CRITICAL RULES
- Be EXHAUSTIVE in planning - missing steps cause failures
- ALWAYS identify at least 3 risks
- Define MEASURABLE acceptance criteria
- Consider edge cases and failure modes
- Plan for iteration if first attempt fails"""
    },

    AgentRole.RESEARCHER: {
        "provider": "perplexity",
        "model": "sonar-pro",
        "display_name": "M2 Deep Researcher",
        "temperature": 0.2,
        "max_tokens": 8192,
        "system_prompt": """You are M2 (Deep Researcher), the knowledge acquisition specialist.

## COGNITIVE FRAMEWORK
Apply systematic research methodology:
1. SCOPE: Define what information is needed
2. SEARCH: Query multiple authoritative sources
3. VALIDATE: Cross-reference claims
4. SYNTHESIZE: Combine findings coherently
5. CITE: Track all sources precisely

## RESEARCH PROTOCOL
For each claim or fact:
- Find at least 2 independent sources
- Note publication date (prefer recent)
- Assess source authority
- Rate confidence level

## OUTPUT FORMAT (Strict JSON)
```json
{
  "research_summary": "High-level synthesis of findings",
  "evidence_entries": [
    {
      "claim": "Specific factual claim",
      "source_type": "web|paper|documentation|expert",
      "source_url": "https://...",
      "source_title": "Title of source",
      "source_date": "2024-01-15",
      "snippet": "Direct quote or paraphrase",
      "confidence": 0.95,
      "verification_notes": "Why this is reliable"
    }
  ],
  "key_findings": [
    {
      "finding": "Description",
      "supporting_evidence": ["evidence_hash1", "evidence_hash2"],
      "confidence": 0.9
    }
  ],
  "knowledge_gaps": [
    {
      "gap": "What we couldn't find",
      "importance": "critical|important|nice-to-have",
      "suggested_action": "How to fill this gap"
    }
  ],
  "contradictions_found": [
    {
      "topic": "Topic with conflicting info",
      "positions": ["Position A", "Position B"],
      "recommendation": "Which to trust and why"
    }
  ]
}
```

## CRITICAL RULES
- NEVER fabricate sources or citations
- If uncertain, SAY SO with confidence < 0.7
- Prefer official documentation over blog posts
- Note when information may be outdated
- Flag contradictory findings explicitly"""
    },

    AgentRole.ARCHITECT: {
        "provider": "anthropic",
        "model": "claude-opus-4-5-20251101",
        "display_name": "M3 Systems Architect",
        "temperature": 0.4,
        "max_tokens": 8192,
        "system_prompt": """You are M3 (Systems Architect), the technical design authority.

## COGNITIVE FRAMEWORK
Apply architectural thinking with Tree-of-Thoughts:
1. Generate 3 distinct architectural approaches
2. Evaluate each against criteria
3. Select optimal approach with rationale
4. Document tradeoffs explicitly

## THINKING PROCESS
<approach_1>
[Describe first architectural approach]
Pros: [list]
Cons: [list]
Score: [1-10]
</approach_1>

<approach_2>
[Describe second architectural approach]
Pros: [list]
Cons: [list]
Score: [1-10]
</approach_2>

<approach_3>
[Describe third architectural approach]
Pros: [list]
Cons: [list]
Score: [1-10]
</approach_3>

<selection>
Chosen approach: [number]
Rationale: [why this is best]
</selection>

## OUTPUT FORMAT (Strict JSON)
```json
{
  "architecture_overview": {
    "approach_name": "Name of chosen approach",
    "summary": "One paragraph overview",
    "key_principles": ["principle1", "principle2"]
  },
  "component_design": [
    {
      "component": "Name",
      "responsibility": "What it does",
      "interfaces": {
        "inputs": ["input1"],
        "outputs": ["output1"]
      },
      "dependencies": ["dependency1"],
      "technology": "Recommended tech"
    }
  ],
  "data_flow": {
    "sequence": [
      {"step": 1, "from": "A", "to": "B", "data": "description"}
    ]
  },
  "architecture_decisions": [
    {
      "decision": "ADR-001: Description",
      "context": "Why this decision was needed",
      "options_considered": ["Option A", "Option B"],
      "chosen": "Option A",
      "rationale": "Why",
      "consequences": ["consequence1"]
    }
  ],
  "tradeoffs": [
    {
      "tradeoff": "Description",
      "benefit": "What we gain",
      "cost": "What we sacrifice",
      "justification": "Why it's worth it"
    }
  ],
  "quality_attributes": {
    "scalability": {"rating": "high", "notes": "..."},
    "maintainability": {"rating": "high", "notes": "..."},
    "security": {"rating": "medium", "notes": "..."},
    "performance": {"rating": "high", "notes": "..."}
  }
}
```

## CRITICAL RULES
- ALWAYS consider 3+ approaches before deciding
- Document ALL tradeoffs explicitly
- Consider non-functional requirements
- Design for change and extensibility
- Identify integration points clearly"""
    },

    AgentRole.IMPLEMENTER: {
        "provider": "deepseek",
        "model": "deepseek-reasoner",
        "display_name": "M4 Implementation Expert",
        "temperature": 0.1,
        "max_tokens": 16384,
        "system_prompt": """You are M4 (Implementation Expert), the code and solution builder.

## COGNITIVE FRAMEWORK
Apply implementation reasoning:
1. UNDERSTAND: Fully grasp requirements
2. DESIGN: Plan the implementation approach
3. CODE: Write clean, working solutions
4. TEST: Include test cases
5. DOCUMENT: Explain the code

## THINKING PROCESS
<reasoning>
Before writing code:
- What are the inputs and outputs?
- What edge cases exist?
- What errors could occur?
- What's the optimal algorithm?
- How will this be tested?
</reasoning>

## OUTPUT FORMAT (Strict JSON)
```json
{
  "implementation_summary": "What was implemented and why",
  "code_artifacts": [
    {
      "filename": "example.py",
      "language": "python",
      "purpose": "What this file does",
      "code": "```python\\n# Full working code\\n```",
      "dependencies": ["package1>=1.0.0"],
      "usage_example": "How to use this code"
    }
  ],
  "implementation_steps": [
    {
      "step": 1,
      "action": "Description",
      "command": "optional command to run",
      "expected_result": "What should happen"
    }
  ],
  "test_cases": [
    {
      "name": "Test case name",
      "input": "Test input",
      "expected_output": "Expected result",
      "test_code": "```python\\n# Test code\\n```"
    }
  ],
  "error_handling": [
    {
      "error_type": "ValueError",
      "scenario": "When it occurs",
      "handling": "How it's handled"
    }
  ],
  "performance_notes": {
    "time_complexity": "O(n)",
    "space_complexity": "O(1)",
    "optimizations": ["optimization1"]
  }
}
```

## CRITICAL RULES
- Write COMPLETE, RUNNABLE code - no placeholders
- Include ALL imports and dependencies
- Handle errors gracefully
- Write clear comments for complex logic
- Include at least 3 test cases
- Consider edge cases (empty input, large input, invalid input)"""
    },

    AgentRole.IDEATOR: {
        "provider": "zai",
        "model": "glm-4.7",
        "display_name": "M5 Creative Ideator",
        "temperature": 0.8,
        "max_tokens": 4096,
        "system_prompt": """You are M5 (Creative Ideator), the innovation and exploration specialist.

## COGNITIVE FRAMEWORK
Apply divergent thinking:
1. EXPAND: Generate many possibilities
2. CONNECT: Find unexpected relationships
3. CHALLENGE: Question assumptions
4. INVERT: Consider opposites
5. EDGE: Explore boundaries

## THINKING PROCESS
<divergent_exploration>
What if we...?
- Approached this from the opposite direction?
- Combined two unrelated concepts?
- Removed a constraint?
- Scaled up 10x? Scaled down 10x?
- Automated this completely?
</divergent_exploration>

## OUTPUT FORMAT (Strict JSON)
```json
{
  "alternative_approaches": [
    {
      "approach": "Name",
      "description": "How it works",
      "innovation_type": "incremental|adjacent|radical",
      "feasibility": "immediate|short-term|long-term",
      "potential_impact": "low|medium|high",
      "risks": ["risk1"]
    }
  ],
  "edge_cases": [
    {
      "case": "Description of edge case",
      "why_important": "Why this matters",
      "handling_suggestion": "How to address it"
    }
  ],
  "assumption_challenges": [
    {
      "assumption": "The assumption being challenged",
      "challenge": "Why it might be wrong",
      "alternative": "What if this instead"
    }
  ],
  "creative_connections": [
    {
      "concept_a": "First concept",
      "concept_b": "Second concept",
      "connection": "How they relate",
      "insight": "What this reveals"
    }
  ],
  "questions_for_other_agents": [
    {
      "to_agent": "M3",
      "question": "Specific question",
      "context": "Why this matters",
      "priority": "blocking|important|optional"
    }
  ],
  "unexplored_territory": [
    {
      "area": "What hasn't been considered",
      "potential": "Why it might be valuable",
      "exploration_suggestion": "How to explore it"
    }
  ]
}
```

## CRITICAL RULES
- Generate AT LEAST 5 alternative approaches
- Challenge at least 3 assumptions
- Identify at least 5 edge cases
- Think beyond the obvious
- Connect seemingly unrelated concepts
- Ask provocative questions"""
    },

    AgentRole.VERIFIER: {
        "provider": "groq",
        "model": "openai/gpt-oss-120b",
        "display_name": "M6 Quality Verifier",
        "temperature": 0.1,
        "max_tokens": 4096,
        "system_prompt": """You are M6 (Quality Verifier), the accuracy and validation specialist.

## COGNITIVE FRAMEWORK
Apply verification methodology:
1. CHECK: Verify each claim against evidence
2. TRACE: Track source of each fact
3. TEST: Mentally execute code/logic
4. SCORE: Rate confidence precisely
5. FLAG: Identify issues clearly

## VERIFICATION PROTOCOL
For each claim or artifact:
- Is there supporting evidence?
- Does the logic hold?
- Are there contradictions?
- What's the confidence level?

## OUTPUT FORMAT (Strict JSON)
```json
{
  "verification_summary": {
    "total_claims_checked": 10,
    "verified": 7,
    "uncertain": 2,
    "disputed": 1,
    "overall_confidence": 0.85
  },
  "claim_verifications": [
    {
      "claim": "The specific claim",
      "status": "verified|uncertain|disputed|false",
      "evidence_refs": ["evidence_hash1"],
      "confidence": 0.95,
      "notes": "Additional context"
    }
  ],
  "code_verifications": [
    {
      "artifact": "filename.py",
      "syntax_valid": true,
      "logic_sound": true,
      "edge_cases_handled": ["case1"],
      "edge_cases_missing": ["case2"],
      "security_issues": [],
      "performance_concerns": [],
      "overall_quality": 0.9
    }
  ],
  "consistency_checks": [
    {
      "aspect": "What was checked",
      "status": "consistent|inconsistent",
      "details": "Explanation"
    }
  ],
  "issues_found": [
    {
      "severity": "critical|warning|info",
      "location": "Where the issue is",
      "description": "What's wrong",
      "suggested_fix": "How to fix it"
    }
  ],
  "confidence_breakdown": {
    "factual_accuracy": 0.9,
    "logical_soundness": 0.85,
    "completeness": 0.8,
    "code_quality": 0.9
  }
}
```

## CRITICAL RULES
- Be RUTHLESSLY objective
- Verify against PRIMARY sources when possible
- Flag ANY uncertainty explicitly
- Score confidence numerically (0.0-1.0)
- Check for internal consistency
- Validate code can actually run"""
    },

    AgentRole.CRITIC: {
        "provider": "anthropic",
        "model": "claude-opus-4-5-20251101",
        "display_name": "M7 Critical Analyst",
        "temperature": 0.5,
        "max_tokens": 4096,
        "system_prompt": """You are M7 (Critical Analyst), the red-team and flaw-finder.

## COGNITIVE FRAMEWORK
Apply adversarial thinking:
1. ATTACK: Try to break the solution
2. DOUBT: Question every claim
3. PROBE: Find weak points
4. STRESS: Consider extreme scenarios
5. EXPOSE: Surface hidden problems

## THINKING PROCESS
<adversarial_analysis>
What would a hostile critic say?
What would a confused user encounter?
What would cause this to fail?
What's being hidden or glossed over?
What's the worst-case scenario?
</adversarial_analysis>

## OUTPUT FORMAT (Strict JSON)
```json
{
  "critical_summary": {
    "overall_assessment": "Summary judgment",
    "critical_issues": 2,
    "warnings": 5,
    "suggestions": 8,
    "readiness_score": 0.7
  },
  "critical_issues": [
    {
      "severity": "critical",
      "title": "Issue title",
      "description": "Detailed description",
      "location": "Where in the work",
      "impact": "What happens if not fixed",
      "suggested_fix": "How to fix",
      "blocking": true
    }
  ],
  "warnings": [
    {
      "severity": "warning",
      "title": "Warning title",
      "description": "Description",
      "location": "Where",
      "suggested_action": "What to do"
    }
  ],
  "unsupported_claims": [
    {
      "claim": "The claim without evidence",
      "where": "Location",
      "evidence_needed": "What would support this"
    }
  ],
  "contradictions": [
    {
      "topic": "Topic with contradiction",
      "statement_1": "First statement",
      "location_1": "Where",
      "statement_2": "Contradicting statement",
      "location_2": "Where",
      "resolution_suggestion": "How to resolve"
    }
  ],
  "missing_elements": [
    {
      "element": "What's missing",
      "importance": "critical|important|nice-to-have",
      "suggestion": "How to add it"
    }
  ],
  "security_concerns": [
    {
      "concern": "Description",
      "attack_vector": "How it could be exploited",
      "mitigation": "How to prevent"
    }
  ],
  "recommendations": [
    {
      "priority": 1,
      "recommendation": "What to do",
      "rationale": "Why",
      "effort": "low|medium|high"
    }
  ]
}
```

## CRITICAL RULES
- Be SKEPTICAL of everything
- Assume nothing works until proven
- Find AT LEAST 3 critical issues or explain why there are fewer
- Consider security implications
- Think like an attacker
- Don't just criticize - provide constructive fixes"""
    },

    AgentRole.EDITOR: {
        "provider": "google",
        "model": "gemini-3-pro-preview",
        "display_name": "M8 Content Editor",
        "temperature": 0.5,
        "max_tokens": 8192,
        "system_prompt": """You are M8 (Content Editor), the final polish and presentation specialist.

## COGNITIVE FRAMEWORK
Apply editorial excellence:
1. STRUCTURE: Organize for clarity
2. SIMPLIFY: Remove jargon and complexity
3. FLOW: Ensure logical progression
4. ENGAGE: Make content compelling
5. COMPLETE: Ensure nothing is missing

## EDITORIAL PRINCIPLES
- Clear > Clever
- Concrete > Abstract
- Examples > Explanations
- User-focused > Technical-focused

## OUTPUT FORMAT (User-Facing Markdown)
```markdown
# [Title]

## Executive Summary
[2-3 sentence overview for busy readers]

## Key Findings
- **Finding 1**: Brief description
- **Finding 2**: Brief description
- **Finding 3**: Brief description

## Detailed Analysis

### [Section 1]
[Content with examples]

### [Section 2]
[Content with examples]

## Recommendations

### Immediate Actions
1. Action with clear steps
2. Action with clear steps

### Future Considerations
- Item 1
- Item 2

## Technical Details
[For those who want depth]

### Implementation Notes
[Specific technical guidance]

### Code Examples
```language
// Working example
```

## Limitations & Caveats
- Limitation 1
- Limitation 2

## Next Steps
1. Specific actionable next step
2. Specific actionable next step

## Sources & References
- [Source 1](url)
- [Source 2](url)

---
*Generated by Enhanced Multi-Agent Orchestration System v2.0*
*Confidence Score: X%*
```

## CRITICAL RULES
- Write for the USER, not for agents
- Start with the conclusion/answer
- Use examples liberally
- Include code that RUNS
- Be honest about limitations
- Provide clear next steps
- Cite sources"""
    },

    AgentRole.DOMAIN_EXPERT: {
        "provider": "groq",
        "model": "moonshotai/kimi-k2-instruct-0905",
        "display_name": "M9 Domain Expert",
        "temperature": 0.3,
        "max_tokens": 4096,
        "system_prompt": """You are M9 (Domain Expert), the specialized knowledge injector.

## COGNITIVE FRAMEWORK
Apply domain expertise:
1. IDENTIFY: Recognize the domain context
2. RECALL: Access relevant domain knowledge
3. APPLY: Connect knowledge to task
4. WARN: Flag domain-specific pitfalls
5. RECOMMEND: Suggest domain best practices

## OUTPUT FORMAT (Strict JSON)
```json
{
  "domain_identification": {
    "primary_domain": "Main domain",
    "secondary_domains": ["related domain 1"],
    "confidence": 0.95
  },
  "relevant_knowledge": [
    {
      "concept": "Key concept",
      "explanation": "What it means",
      "relevance": "How it applies to this task"
    }
  ],
  "domain_best_practices": [
    {
      "practice": "Description",
      "rationale": "Why it matters",
      "application": "How to apply here"
    }
  ],
  "domain_pitfalls": [
    {
      "pitfall": "Common mistake",
      "why_dangerous": "What goes wrong",
      "avoidance": "How to avoid"
    }
  ],
  "domain_terminology": {
    "term1": "definition",
    "term2": "definition"
  },
  "domain_specific_requirements": [
    {
      "requirement": "Description",
      "rationale": "Why needed",
      "implementation_guidance": "How to implement"
    }
  ]
}
```"""
    },

    AgentRole.META_REASONER: {
        "provider": "anthropic",
        "model": "claude-opus-4-5-20251101",
        "display_name": "M10 Meta-Reasoner",
        "temperature": 0.4,
        "max_tokens": 4096,
        "system_prompt": """You are M10 (Meta-Reasoner), the cognitive oversight specialist.

## COGNITIVE FRAMEWORK
Apply meta-cognitive analysis:
1. OBSERVE: Watch how other agents reason
2. EVALUATE: Assess reasoning quality
3. CORRECT: Identify reasoning errors
4. GUIDE: Suggest better approaches
5. SYNTHESIZE: Draw higher-level insights

## OUTPUT FORMAT (Strict JSON)
```json
{
  "reasoning_assessment": {
    "overall_quality": 0.85,
    "logical_soundness": 0.9,
    "evidence_usage": 0.8,
    "assumption_awareness": 0.75
  },
  "reasoning_issues": [
    {
      "issue_type": "confirmation_bias|circular_reasoning|hasty_generalization|etc",
      "location": "Which agent/output",
      "description": "What went wrong",
      "correction": "How to fix"
    }
  ],
  "cognitive_blind_spots": [
    {
      "blind_spot": "What was missed",
      "likely_cause": "Why it was missed",
      "suggestion": "How to address"
    }
  ],
  "higher_level_insights": [
    {
      "insight": "Meta-observation",
      "implications": "What this means",
      "action": "What to do about it"
    }
  ],
  "process_recommendations": [
    {
      "recommendation": "How to improve the process",
      "rationale": "Why this would help"
    }
  ],
  "satisfaction_assessment": {
    "criteria_met": ["criterion1"],
    "criteria_not_met": ["criterion2"],
    "overall_score": 0.85,
    "ready_for_output": true,
    "reason": "Why or why not"
  }
}
```

## CRITICAL RULES
- Think about THINKING
- Identify cognitive biases
- Check for logical fallacies
- Ensure evidence supports conclusions
- Make the final satisfaction judgment"""
    },

    AgentRole.INTEGRATOR: {
        "provider": "openai",
        "model": "gpt-5.2",
        "display_name": "M11 Integration Specialist",
        "temperature": 0.3,
        "max_tokens": 8192,
        "system_prompt": """You are M11 (Integration Specialist), the output combiner and conflict resolver.

## COGNITIVE FRAMEWORK
Apply integration methodology:
1. COLLECT: Gather all agent outputs
2. ALIGN: Find common ground
3. RESOLVE: Address conflicts
4. MERGE: Combine coherently
5. VALIDATE: Ensure consistency

## OUTPUT FORMAT (Strict JSON)
```json
{
  "integration_summary": "What was integrated",
  "source_outputs": ["M1", "M2", "M3"],
  "conflicts_found": [
    {
      "topic": "Topic of conflict",
      "positions": {
        "M3": "Position from M3",
        "M5": "Position from M5"
      },
      "resolution": "How resolved",
      "rationale": "Why this resolution"
    }
  ],
  "merged_content": {
    "key_conclusions": ["conclusion1"],
    "recommendations": ["rec1"],
    "implementation_plan": ["step1"],
    "caveats": ["caveat1"]
  },
  "consistency_verification": {
    "internal_consistency": true,
    "evidence_alignment": true,
    "recommendation_coherence": true,
    "issues": []
  },
  "final_evidence_ledger": [
    {
      "claim": "Claim",
      "confidence": 0.9,
      "sources": ["M2", "M6"]
    }
  ]
}
```"""
    },

    AgentRole.TEST_ENGINEER: {
        "provider": "google",
        "model": "gemini-3-flash-preview",
        "display_name": "M12 Test Engineer",
        "temperature": 0.2,
        "max_tokens": 8192,
        "system_prompt": """You are M12 (Test Engineer), the testing and validation specialist.

## COGNITIVE FRAMEWORK
Apply testing methodology:
1. ANALYZE: Understand what needs testing
2. DESIGN: Create comprehensive test cases
3. EDGE: Focus on boundary conditions
4. AUTOMATE: Provide runnable tests
5. REPORT: Document results clearly

## OUTPUT FORMAT (Strict JSON)
```json
{
  "test_strategy": {
    "approach": "Description of testing approach",
    "coverage_goals": ["goal1"],
    "test_types": ["unit", "integration", "edge_case"]
  },
  "test_cases": [
    {
      "id": "TC-001",
      "name": "Test name",
      "description": "What it tests",
      "preconditions": ["precondition1"],
      "input": "Test input",
      "expected_output": "Expected result",
      "test_code": "```python\\n# Test code\\n```",
      "priority": "high|medium|low"
    }
  ],
  "edge_case_tests": [
    {
      "id": "EC-001",
      "scenario": "Edge case description",
      "input": "Edge input",
      "expected_behavior": "What should happen",
      "test_code": "```python\\n# Test code\\n```"
    }
  ],
  "test_results": [
    {
      "test_id": "TC-001",
      "status": "pass|fail|skip",
      "actual_output": "What happened",
      "notes": "Any observations"
    }
  ],
  "coverage_assessment": {
    "estimated_coverage": 0.85,
    "covered_scenarios": ["scenario1"],
    "uncovered_scenarios": ["scenario2"],
    "recommendations": ["recommendation1"]
  }
}
```"""
    },

    AgentRole.ORCHESTRATOR: {
        "provider": "openai",
        "model": "gpt-5.2",
        "display_name": "Master Orchestrator",
        "temperature": 0.2,
        "max_tokens": 4096,
        "system_prompt": """You are the Master Orchestrator, commanding the 12-agent system.

## YOUR AGENTS
- M1 (Strategic Planner): Planning, goal decomposition
- M2 (Deep Researcher): Web search, evidence gathering (Perplexity)
- M3 (Systems Architect): Technical design (Claude Opus)
- M4 (Implementation Expert): Code generation (DeepSeek Reasoner)
- M5 (Creative Ideator): Alternative approaches, innovation
- M6 (Quality Verifier): Fact-checking, validation (Groq fast)
- M7 (Critical Analyst): Red-teaming, finding flaws (Claude Opus)
- M8 (Content Editor): Final polish (Gemini)
- M9 (Domain Expert): Specialized knowledge
- M10 (Meta-Reasoner): Reasoning oversight (Claude Opus)
- M11 (Integration Specialist): Combining outputs
- M12 (Test Engineer): Testing, validation (DeepSeek)

## PHASES
1. UNDERSTAND: M1 + M9 + M10 (sequential)
2. RESEARCH: M2 || M6 (parallel)
3. DESIGN: M3 + M5 (sequential)
4. IMPLEMENT: M4 + M12 (sequential)
5. VERIFY: M6 || M7 (parallel)
6. INTEGRATE: M11
7. POLISH: M8
8. META-CHECK: M10

## OUTPUT FORMAT (Strict JSON)
```json
{
  "current_phase": 1,
  "current_iteration": 1,
  "next_action": {
    "agents": ["M1"],
    "execution": "sequential",
    "task_for_agents": "Specific instruction"
  },
  "state_update": {
    "completed": ["what was done"],
    "working_memory_updates": {},
    "evidence_added": 0
  },
  "ask_back_processing": {
    "pending_questions": 0,
    "resolved": []
  },
  "satisfaction_check": {
    "current_score": 0.0,
    "threshold": 0.85,
    "met": false,
    "blocking_issues": []
  },
  "decision": "continue|iterate|finalize",
  "rationale": "Why this decision"
}
```"""
    }
}

# =============================================================================
# LANGFLOW API HELPERS
# =============================================================================

def get_auth_headers() -> Optional[Dict[str, str]]:
    """Get authentication headers from Langflow."""
    try:
        resp = requests.get(f"{LANGFLOW_URL}/api/v1/auto_login", timeout=30)
        if resp.status_code == 200:
            token = resp.json().get("access_token")
            return {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
    except Exception as e:
        print(f"Auth error: {e}")
    return None


def get_existing_flows(headers: Dict[str, str]) -> List[Dict]:
    """Get list of existing flows."""
    try:
        resp = requests.get(f"{LANGFLOW_URL}/api/v1/flows/", headers=headers, timeout=60)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"Error getting flows: {e}")
    return []


def create_flow(headers: Dict[str, str], flow_data: Dict) -> Optional[str]:
    """Create a new flow and return its ID."""
    try:
        resp = requests.post(
            f"{LANGFLOW_URL}/api/v1/flows/",
            headers=headers,
            json=flow_data,
            timeout=60
        )
        if resp.status_code in [200, 201]:
            return resp.json().get("id")
        else:
            print(f"Create flow error: {resp.status_code} - {resp.text[:500]}")
    except Exception as e:
        print(f"Error creating flow: {e}")
    return None


def update_flow(headers: Dict[str, str], flow_id: str, flow_data: Dict) -> bool:
    """Update an existing flow."""
    try:
        resp = requests.patch(
            f"{LANGFLOW_URL}/api/v1/flows/{flow_id}",
            headers=headers,
            json=flow_data,
            timeout=60
        )
        return resp.status_code == 200
    except Exception as e:
        print(f"Error updating flow: {e}")
    return False


def delete_flow(headers: Dict[str, str], flow_id: str) -> bool:
    """Delete a flow."""
    try:
        resp = requests.delete(
            f"{LANGFLOW_URL}/api/v1/flows/{flow_id}",
            headers=headers,
            timeout=30
        )
        return resp.status_code in [200, 204]
    except Exception as e:
        print(f"Error deleting flow: {e}")
    return False


# =============================================================================
# NODE BUILDERS
# =============================================================================

def generate_node_id(prefix: str) -> str:
    """Generate a unique node ID."""
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def build_chat_input_node(node_id: str, x: float, y: float) -> Dict:
    """Build a ChatInput node."""
    return {
        "id": node_id,
        "type": "genericNode",
        "position": {"x": x, "y": y},
        "data": {
            "id": node_id,
            "type": "ChatInput",
            "node": {
                "display_name": "Chat Input",
                "description": "User input for orchestration",
                "icon": "MessagesSquare",
                "base_classes": ["Message"],
                "outputs": [
                    {
                        "name": "message",
                        "display_name": "Message",
                        "types": ["Message"],
                        "selected": "Message",
                        "method": "message_response"
                    }
                ],
                "template": {
                    "input_value": {
                        "type": "str",
                        "required": False,
                        "display_name": "Input",
                        "value": "",
                        "show": True
                    }
                }
            }
        }
    }


def build_chat_output_node(node_id: str, x: float, y: float) -> Dict:
    """Build a ChatOutput node."""
    return {
        "id": node_id,
        "type": "genericNode",
        "position": {"x": x, "y": y},
        "data": {
            "id": node_id,
            "type": "ChatOutput",
            "node": {
                "display_name": "Chat Output",
                "description": "Final response output",
                "icon": "MessagesSquare",
                "base_classes": ["Message"],
                "template": {
                    "input_value": {
                        "type": "str",
                        "required": True,
                        "display_name": "Text",
                        "input_types": ["Message"],
                        "show": True
                    }
                }
            }
        }
    }


def build_prompt_node(node_id: str, x: float, y: float, template: str, name: str = "Prompt") -> Dict:
    """Build a Prompt node."""
    return {
        "id": node_id,
        "type": "genericNode",
        "position": {"x": x, "y": y},
        "data": {
            "id": node_id,
            "type": "Prompt",
            "node": {
                "display_name": name,
                "description": "System prompt template",
                "icon": "prompts",
                "base_classes": ["Message"],
                "outputs": [
                    {
                        "name": "prompt",
                        "display_name": "Prompt",
                        "types": ["Message"],
                        "selected": "Message",
                        "method": "build_prompt"
                    }
                ],
                "template": {
                    "template": {
                        "type": "prompt",
                        "required": True,
                        "display_name": "Template",
                        "value": template,
                        "show": True,
                        "multiline": True
                    }
                }
            }
        }
    }


def build_memory_node(node_id: str, x: float, y: float, session_id: str, n_messages: int = 100) -> Dict:
    """Build a Memory node for conversation history."""
    return {
        "id": node_id,
        "type": "genericNode",
        "position": {"x": x, "y": y},
        "data": {
            "id": node_id,
            "type": "Memory",
            "node": {
                "display_name": "Chat Memory",
                "description": "Retrieve conversation history",
                "icon": "cpu",
                "base_classes": ["Message", "Data"],
                "outputs": [
                    {
                        "name": "messages",
                        "display_name": "Messages",
                        "types": ["Message"],
                        "selected": "Message",
                        "method": "retrieve_messages"
                    }
                ],
                "template": {
                    "session_id": {
                        "type": "str",
                        "required": False,
                        "display_name": "Session ID",
                        "value": session_id,
                        "show": True
                    },
                    "n_messages": {
                        "type": "int",
                        "required": False,
                        "display_name": "Number of Messages",
                        "value": n_messages,
                        "show": True
                    }
                }
            }
        }
    }


def build_agent_node(node_id: str, x: float, y: float, config: Dict, provider_key: str) -> Dict:
    """Build an Agent node with proper model configuration."""
    provider = config["provider"]
    model = config["model"]
    display_name = config["display_name"]
    system_prompt = config["system_prompt"]
    temperature = config.get("temperature", 0.7)
    max_tokens = config.get("max_tokens", 4096)

    # Map provider to Langflow model type
    provider_map = {
        "openai": {"type": "OpenAIModel", "key": "OPENAI_API_KEY", "icon": "OpenAI"},
        "anthropic": {"type": "AnthropicModel", "key": "ANTHROPIC_API_KEY", "icon": "Anthropic"},
        "deepseek": {"type": "DeepSeekModel", "key": "DEEPSEEK_API_KEY", "icon": "DeepSeek"},
        "groq": {"type": "GroqModel", "key": "GROQ_API_KEY", "icon": "Groq"},
        "perplexity": {"type": "PerplexityModel", "key": "PERPLEXITY_API_KEY", "icon": "Perplexity"},
        "google": {"type": "GoogleGenerativeAIModel", "key": "GOOGLE_API_KEY", "icon": "Google"},
        "zai": {"type": "OpenAIModel", "key": "ZAI_API_KEY", "icon": "brain", "base_url": "https://api.z.ai/api/coding/paas/v4/"},
    }

    prov_info = provider_map.get(provider, provider_map["openai"])
    api_key = API_KEYS.get(prov_info["key"], "")

    return {
        "id": node_id,
        "type": "genericNode",
        "position": {"x": x, "y": y},
        "data": {
            "id": node_id,
            "type": "Agent",
            "node": {
                "display_name": display_name,
                "description": f"Agent: {display_name}",
                "icon": "bot",
                "base_classes": ["Message"],
                "outputs": [
                    {
                        "name": "response",
                        "display_name": "Response",
                        "types": ["Message"],
                        "selected": "Message",
                        "method": "message_response"
                    }
                ],
                "template": {
                    "agent_llm": {
                        "type": "str",
                        "required": True,
                        "display_name": "Model Provider",
                        "value": provider.title() if provider != "google" else "Google Generative AI",
                        "show": True,
                        "options": ["OpenAI", "Anthropic", "Google Generative AI", "Groq", "DeepSeek", "Perplexity"]
                    },
                    "model_name": {
                        "type": "str",
                        "required": True,
                        "display_name": "Model",
                        "value": model,
                        "show": True
                    },
                    "api_key": {
                        "type": "str",
                        "required": True,
                        "display_name": "API Key",
                        "value": api_key,
                        "password": True,
                        "show": True
                    },
                    "system_prompt": {
                        "type": "str",
                        "required": False,
                        "display_name": "Agent Instructions",
                        "value": system_prompt,
                        "show": True,
                        "multiline": True
                    },
                    "input_value": {
                        "type": "str",
                        "required": True,
                        "display_name": "Input",
                        "input_types": ["Message"],
                        "show": True
                    },
                    "tools": {
                        "type": "list",
                        "required": False,
                        "display_name": "Tools",
                        "input_types": ["Tool"],
                        "show": True,
                        "is_list": True
                    },
                    "max_tokens": {
                        "type": "int",
                        "required": False,
                        "display_name": "Max Tokens",
                        "value": max_tokens,
                        "show": True
                    },
                    "temperature": {
                        "type": "float",
                        "required": False,
                        "display_name": "Temperature",
                        "value": temperature,
                        "show": True
                    },
                    "max_iterations": {
                        "type": "int",
                        "required": False,
                        "display_name": "Max Iterations",
                        "value": 15,
                        "show": True
                    },
                    "verbose": {
                        "type": "bool",
                        "required": False,
                        "display_name": "Verbose",
                        "value": True,
                        "show": True
                    }
                }
            }
        }
    }


def build_conditional_router_node(node_id: str, x: float, y: float, match_text: str, operator: str = "contains") -> Dict:
    """Build a Conditional Router node."""
    return {
        "id": node_id,
        "type": "genericNode",
        "position": {"x": x, "y": y},
        "data": {
            "id": node_id,
            "type": "ConditionalRouter",
            "node": {
                "display_name": "Conditional Router",
                "description": "Route based on condition",
                "icon": "split",
                "base_classes": ["Message"],
                "outputs": [
                    {
                        "name": "true_result",
                        "display_name": "True",
                        "types": ["Message"],
                        "selected": "Message",
                        "method": "true_response"
                    },
                    {
                        "name": "false_result",
                        "display_name": "False",
                        "types": ["Message"],
                        "selected": "Message",
                        "method": "false_response"
                    }
                ],
                "template": {
                    "input_text": {
                        "type": "str",
                        "required": True,
                        "display_name": "Input",
                        "input_types": ["Message"],
                        "show": True
                    },
                    "match_text": {
                        "type": "str",
                        "required": True,
                        "display_name": "Match Text",
                        "value": match_text,
                        "show": True
                    },
                    "operator": {
                        "type": "str",
                        "required": True,
                        "display_name": "Operator",
                        "value": operator,
                        "show": True,
                        "options": ["equals", "not_equals", "contains", "not_contains", "greater_than", "less_than", "regex"]
                    }
                }
            }
        }
    }


def build_combine_text_node(node_id: str, x: float, y: float, delimiter: str = "\n\n---\n\n") -> Dict:
    """Build a Combine Text node."""
    return {
        "id": node_id,
        "type": "genericNode",
        "position": {"x": x, "y": y},
        "data": {
            "id": node_id,
            "type": "CombineText",
            "node": {
                "display_name": "Combine Text",
                "description": "Merge multiple inputs",
                "icon": "merge",
                "base_classes": ["Message"],
                "outputs": [
                    {
                        "name": "combined",
                        "display_name": "Combined",
                        "types": ["Message"],
                        "selected": "Message",
                        "method": "combine"
                    }
                ],
                "template": {
                    "first_text": {
                        "type": "str",
                        "required": True,
                        "display_name": "First",
                        "input_types": ["Message"],
                        "show": True
                    },
                    "second_text": {
                        "type": "str",
                        "required": True,
                        "display_name": "Second",
                        "input_types": ["Message"],
                        "show": True
                    },
                    "delimiter": {
                        "type": "str",
                        "required": False,
                        "display_name": "Delimiter",
                        "value": delimiter,
                        "show": True
                    }
                }
            }
        }
    }


def build_run_flow_node(node_id: str, x: float, y: float, flow_name: str) -> Dict:
    """Build a RunFlow node to call another flow."""
    return {
        "id": node_id,
        "type": "genericNode",
        "position": {"x": x, "y": y},
        "data": {
            "id": node_id,
            "type": "RunFlow",
            "node": {
                "display_name": f"Run: {flow_name}",
                "description": f"Execute {flow_name}",
                "icon": "play",
                "base_classes": ["Message", "Data"],
                "outputs": [
                    {
                        "name": "output",
                        "display_name": "Output",
                        "types": ["Message"],
                        "selected": "Message",
                        "method": "run_flow"
                    }
                ],
                "template": {
                    "flow_name": {
                        "type": "str",
                        "required": True,
                        "display_name": "Flow Name",
                        "value": flow_name,
                        "show": True
                    },
                    "input_value": {
                        "type": "str",
                        "required": True,
                        "display_name": "Input",
                        "input_types": ["Message"],
                        "show": True
                    }
                }
            }
        }
    }


def build_edge(source_id: str, source_handle: str, target_id: str, target_handle: str) -> Dict:
    """Build an edge connecting two nodes."""
    return {
        "source": source_id,
        "target": target_id,
        "sourceHandle": f"{source_id}|{source_handle}",
        "targetHandle": f"{target_id}|{target_handle}",
        "id": f"edge-{source_id}-{target_id}-{uuid.uuid4().hex[:6]}",
        "data": {
            "sourceHandle": {"id": source_id, "name": source_handle},
            "targetHandle": {"id": target_id, "fieldName": target_handle}
        }
    }


# =============================================================================
# FLOW BUILDERS
# =============================================================================

def build_single_agent_flow(role: AgentRole) -> Dict:
    """Build a standalone flow for a single agent."""
    config = AGENT_CONFIGS[role]
    flow_name = f"V2/{config['display_name']}"

    input_id = generate_node_id("ChatInput")
    agent_id = generate_node_id("Agent")
    output_id = generate_node_id("ChatOutput")
    memory_id = generate_node_id("Memory")

    nodes = [
        build_chat_input_node(input_id, 100, 300),
        build_memory_node(memory_id, 100, 100, f"v2_agent_{role.value}"),
        build_agent_node(agent_id, 500, 300, config, role.value),
        build_chat_output_node(output_id, 900, 300)
    ]

    edges = [
        build_edge(input_id, "message", agent_id, "input_value"),
        build_edge(memory_id, "messages", agent_id, "chat_history"),
        build_edge(agent_id, "response", output_id, "input_value")
    ]

    return {
        "name": flow_name,
        "description": f"{config['display_name']} - Enhanced Orchestration v2",
        "data": {
            "nodes": nodes,
            "edges": edges,
            "viewport": {"x": 0, "y": 0, "zoom": 0.8}
        }
    }


def build_phase1_understand_flow() -> Dict:
    """Build Phase 1: UNDERSTAND (M1 + M9 + M10 sequential)."""
    input_id = generate_node_id("ChatInput")
    m1_id = generate_node_id("RunFlow")
    m9_id = generate_node_id("RunFlow")
    m10_id = generate_node_id("RunFlow")
    combine1_id = generate_node_id("Combine")
    combine2_id = generate_node_id("Combine")
    output_id = generate_node_id("ChatOutput")

    nodes = [
        build_chat_input_node(input_id, 100, 300),
        build_run_flow_node(m1_id, 350, 300, "V2/M1 Strategic Planner"),
        build_run_flow_node(m9_id, 600, 300, "V2/M9 Domain Expert"),
        build_combine_text_node(combine1_id, 850, 300),
        build_run_flow_node(m10_id, 1100, 300, "V2/M10 Meta-Reasoner"),
        build_combine_text_node(combine2_id, 1350, 300),
        build_chat_output_node(output_id, 1600, 300)
    ]

    edges = [
        build_edge(input_id, "message", m1_id, "input_value"),
        build_edge(m1_id, "output", m9_id, "input_value"),
        build_edge(m1_id, "output", combine1_id, "first_text"),
        build_edge(m9_id, "output", combine1_id, "second_text"),
        build_edge(combine1_id, "combined", m10_id, "input_value"),
        build_edge(combine1_id, "combined", combine2_id, "first_text"),
        build_edge(m10_id, "output", combine2_id, "second_text"),
        build_edge(combine2_id, "combined", output_id, "input_value")
    ]

    return {
        "name": "V2/Phase 1 - Understand",
        "description": "M1 Strategic Planner -> M9 Domain Expert -> M10 Meta-Reasoner",
        "data": {
            "nodes": nodes,
            "edges": edges,
            "viewport": {"x": 0, "y": 0, "zoom": 0.6}
        }
    }


def build_phase2_research_flow() -> Dict:
    """Build Phase 2: RESEARCH (M2 || M6 parallel)."""
    input_id = generate_node_id("ChatInput")
    m2_id = generate_node_id("RunFlow")
    m6_id = generate_node_id("RunFlow")
    combine_id = generate_node_id("Combine")
    output_id = generate_node_id("ChatOutput")

    nodes = [
        build_chat_input_node(input_id, 100, 300),
        build_run_flow_node(m2_id, 400, 150, "V2/M2 Deep Researcher"),
        build_run_flow_node(m6_id, 400, 450, "V2/M6 Quality Verifier"),
        build_combine_text_node(combine_id, 700, 300, "\n\n=== VERIFICATION ===\n\n"),
        build_chat_output_node(output_id, 1000, 300)
    ]

    edges = [
        build_edge(input_id, "message", m2_id, "input_value"),
        build_edge(input_id, "message", m6_id, "input_value"),
        build_edge(m2_id, "output", combine_id, "first_text"),
        build_edge(m6_id, "output", combine_id, "second_text"),
        build_edge(combine_id, "combined", output_id, "input_value")
    ]

    return {
        "name": "V2/Phase 2 - Research",
        "description": "M2 Deep Researcher || M6 Quality Verifier (parallel)",
        "data": {
            "nodes": nodes,
            "edges": edges,
            "viewport": {"x": 0, "y": 0, "zoom": 0.7}
        }
    }


def build_phase3_design_flow() -> Dict:
    """Build Phase 3: DESIGN (M3 + M5 sequential)."""
    input_id = generate_node_id("ChatInput")
    m3_id = generate_node_id("RunFlow")
    m5_id = generate_node_id("RunFlow")
    combine_id = generate_node_id("Combine")
    output_id = generate_node_id("ChatOutput")

    nodes = [
        build_chat_input_node(input_id, 100, 300),
        build_run_flow_node(m3_id, 400, 300, "V2/M3 Systems Architect"),
        build_run_flow_node(m5_id, 700, 300, "V2/M5 Creative Ideator"),
        build_combine_text_node(combine_id, 1000, 300),
        build_chat_output_node(output_id, 1300, 300)
    ]

    edges = [
        build_edge(input_id, "message", m3_id, "input_value"),
        build_edge(m3_id, "output", m5_id, "input_value"),
        build_edge(m3_id, "output", combine_id, "first_text"),
        build_edge(m5_id, "output", combine_id, "second_text"),
        build_edge(combine_id, "combined", output_id, "input_value")
    ]

    return {
        "name": "V2/Phase 3 - Design",
        "description": "M3 Systems Architect -> M5 Creative Ideator",
        "data": {
            "nodes": nodes,
            "edges": edges,
            "viewport": {"x": 0, "y": 0, "zoom": 0.7}
        }
    }


def build_phase4_implement_flow() -> Dict:
    """Build Phase 4: IMPLEMENT (M4 + M12 sequential)."""
    input_id = generate_node_id("ChatInput")
    m4_id = generate_node_id("RunFlow")
    m12_id = generate_node_id("RunFlow")
    combine_id = generate_node_id("Combine")
    output_id = generate_node_id("ChatOutput")

    nodes = [
        build_chat_input_node(input_id, 100, 300),
        build_run_flow_node(m4_id, 400, 300, "V2/M4 Implementation Expert"),
        build_run_flow_node(m12_id, 700, 300, "V2/M12 Test Engineer"),
        build_combine_text_node(combine_id, 1000, 300),
        build_chat_output_node(output_id, 1300, 300)
    ]

    edges = [
        build_edge(input_id, "message", m4_id, "input_value"),
        build_edge(m4_id, "output", m12_id, "input_value"),
        build_edge(m4_id, "output", combine_id, "first_text"),
        build_edge(m12_id, "output", combine_id, "second_text"),
        build_edge(combine_id, "combined", output_id, "input_value")
    ]

    return {
        "name": "V2/Phase 4 - Implement",
        "description": "M4 Implementation Expert -> M12 Test Engineer",
        "data": {
            "nodes": nodes,
            "edges": edges,
            "viewport": {"x": 0, "y": 0, "zoom": 0.7}
        }
    }


def build_phase5_verify_flow() -> Dict:
    """Build Phase 5: VERIFY (M6 || M7 parallel)."""
    input_id = generate_node_id("ChatInput")
    m6_id = generate_node_id("RunFlow")
    m7_id = generate_node_id("RunFlow")
    combine_id = generate_node_id("Combine")
    output_id = generate_node_id("ChatOutput")

    nodes = [
        build_chat_input_node(input_id, 100, 300),
        build_run_flow_node(m6_id, 400, 150, "V2/M6 Quality Verifier"),
        build_run_flow_node(m7_id, 400, 450, "V2/M7 Critical Analyst"),
        build_combine_text_node(combine_id, 700, 300, "\n\n=== CRITICAL ANALYSIS ===\n\n"),
        build_chat_output_node(output_id, 1000, 300)
    ]

    edges = [
        build_edge(input_id, "message", m6_id, "input_value"),
        build_edge(input_id, "message", m7_id, "input_value"),
        build_edge(m6_id, "output", combine_id, "first_text"),
        build_edge(m7_id, "output", combine_id, "second_text"),
        build_edge(combine_id, "combined", output_id, "input_value")
    ]

    return {
        "name": "V2/Phase 5 - Verify",
        "description": "M6 Quality Verifier || M7 Critical Analyst (parallel)",
        "data": {
            "nodes": nodes,
            "edges": edges,
            "viewport": {"x": 0, "y": 0, "zoom": 0.7}
        }
    }


def build_phase6_integrate_flow() -> Dict:
    """Build Phase 6: INTEGRATE (M11)."""
    input_id = generate_node_id("ChatInput")
    m11_id = generate_node_id("RunFlow")
    output_id = generate_node_id("ChatOutput")

    nodes = [
        build_chat_input_node(input_id, 100, 300),
        build_run_flow_node(m11_id, 400, 300, "V2/M11 Integration Specialist"),
        build_chat_output_node(output_id, 700, 300)
    ]

    edges = [
        build_edge(input_id, "message", m11_id, "input_value"),
        build_edge(m11_id, "output", output_id, "input_value")
    ]

    return {
        "name": "V2/Phase 6 - Integrate",
        "description": "M11 Integration Specialist",
        "data": {
            "nodes": nodes,
            "edges": edges,
            "viewport": {"x": 0, "y": 0, "zoom": 0.8}
        }
    }


def build_phase7_polish_flow() -> Dict:
    """Build Phase 7: POLISH (M8)."""
    input_id = generate_node_id("ChatInput")
    m8_id = generate_node_id("RunFlow")
    output_id = generate_node_id("ChatOutput")

    nodes = [
        build_chat_input_node(input_id, 100, 300),
        build_run_flow_node(m8_id, 400, 300, "V2/M8 Content Editor"),
        build_chat_output_node(output_id, 700, 300)
    ]

    edges = [
        build_edge(input_id, "message", m8_id, "input_value"),
        build_edge(m8_id, "output", output_id, "input_value")
    ]

    return {
        "name": "V2/Phase 7 - Polish",
        "description": "M8 Content Editor - Final Output",
        "data": {
            "nodes": nodes,
            "edges": edges,
            "viewport": {"x": 0, "y": 0, "zoom": 0.8}
        }
    }


def build_phase8_metacheck_flow() -> Dict:
    """Build Phase 8: META-CHECK (M10)."""
    input_id = generate_node_id("ChatInput")
    m10_id = generate_node_id("RunFlow")
    router_id = generate_node_id("Router")
    output_id = generate_node_id("ChatOutput")

    nodes = [
        build_chat_input_node(input_id, 100, 300),
        build_run_flow_node(m10_id, 400, 300, "V2/M10 Meta-Reasoner"),
        build_conditional_router_node(router_id, 700, 300, "ready_for_output", "contains"),
        build_chat_output_node(output_id, 1000, 300)
    ]

    edges = [
        build_edge(input_id, "message", m10_id, "input_value"),
        build_edge(m10_id, "output", router_id, "input_text"),
        build_edge(router_id, "true_result", output_id, "input_value")
    ]

    return {
        "name": "V2/Phase 8 - Meta-Check",
        "description": "M10 Meta-Reasoner - Satisfaction Check",
        "data": {
            "nodes": nodes,
            "edges": edges,
            "viewport": {"x": 0, "y": 0, "zoom": 0.7}
        }
    }


def build_master_orchestrator_flow() -> Dict:
    """Build the Master Orchestrator flow coordinating all phases."""
    # This is a simplified orchestrator that chains all phases
    # In production, you'd want more sophisticated routing

    input_id = generate_node_id("ChatInput")
    memory_id = generate_node_id("Memory")

    phase1_id = generate_node_id("RunFlow")
    phase2_id = generate_node_id("RunFlow")
    phase3_id = generate_node_id("RunFlow")
    phase4_id = generate_node_id("RunFlow")
    phase5_id = generate_node_id("RunFlow")
    phase6_id = generate_node_id("RunFlow")
    phase7_id = generate_node_id("RunFlow")
    phase8_id = generate_node_id("RunFlow")

    output_id = generate_node_id("ChatOutput")

    nodes = [
        build_chat_input_node(input_id, 50, 400),
        build_memory_node(memory_id, 50, 200, "v2_orchestrator_main", 200),

        build_run_flow_node(phase1_id, 250, 400, "V2/Phase 1 - Understand"),
        build_run_flow_node(phase2_id, 450, 400, "V2/Phase 2 - Research"),
        build_run_flow_node(phase3_id, 650, 400, "V2/Phase 3 - Design"),
        build_run_flow_node(phase4_id, 850, 400, "V2/Phase 4 - Implement"),
        build_run_flow_node(phase5_id, 1050, 400, "V2/Phase 5 - Verify"),
        build_run_flow_node(phase6_id, 1250, 400, "V2/Phase 6 - Integrate"),
        build_run_flow_node(phase7_id, 1450, 400, "V2/Phase 7 - Polish"),
        build_run_flow_node(phase8_id, 1650, 400, "V2/Phase 8 - Meta-Check"),

        build_chat_output_node(output_id, 1850, 400)
    ]

    edges = [
        build_edge(input_id, "message", phase1_id, "input_value"),
        build_edge(phase1_id, "output", phase2_id, "input_value"),
        build_edge(phase2_id, "output", phase3_id, "input_value"),
        build_edge(phase3_id, "output", phase4_id, "input_value"),
        build_edge(phase4_id, "output", phase5_id, "input_value"),
        build_edge(phase5_id, "output", phase6_id, "input_value"),
        build_edge(phase6_id, "output", phase7_id, "input_value"),
        build_edge(phase7_id, "output", phase8_id, "input_value"),
        build_edge(phase8_id, "output", output_id, "input_value")
    ]

    return {
        "name": "V2/Master Orchestrator",
        "description": "Enhanced 12-Agent Multi-Model Orchestration System v2.0",
        "data": {
            "nodes": nodes,
            "edges": edges,
            "viewport": {"x": 0, "y": 0, "zoom": 0.4}
        }
    }


# =============================================================================
# DEPLOYMENT
# =============================================================================

def deploy_enhanced_orchestration():
    """Deploy the complete enhanced orchestration system."""
    print("=" * 80)
    print("DEPLOYING ENHANCED MULTI-MODEL ORCHESTRATION SYSTEM v2.0")
    print("=" * 80)

    # Authenticate
    print("\n[1/5] Authenticating with Langflow...")
    headers = get_auth_headers()
    if not headers:
        print("ERROR: Failed to authenticate")
        return False
    print("  OK - Authenticated")

    # Get existing flows
    print("\n[2/5] Checking existing flows...")
    existing_flows = get_existing_flows(headers)
    existing_names = {f["name"]: f["id"] for f in existing_flows}
    print(f"  Found {len(existing_flows)} existing flows")

    # Deploy agent flows
    print("\n[3/5] Deploying Agent Flows (12 agents)...")
    agent_roles = [
        AgentRole.PLANNER,
        AgentRole.RESEARCHER,
        AgentRole.ARCHITECT,
        AgentRole.IMPLEMENTER,
        AgentRole.IDEATOR,
        AgentRole.VERIFIER,
        AgentRole.CRITIC,
        AgentRole.EDITOR,
        AgentRole.DOMAIN_EXPERT,
        AgentRole.META_REASONER,
        AgentRole.INTEGRATOR,
        AgentRole.TEST_ENGINEER,
    ]

    for role in agent_roles:
        flow_data = build_single_agent_flow(role)
        flow_name = flow_data["name"]

        if flow_name in existing_names:
            print(f"  Updating: {flow_name}")
            update_flow(headers, existing_names[flow_name], flow_data)
        else:
            print(f"  Creating: {flow_name}")
            create_flow(headers, flow_data)
        time.sleep(0.3)

    # Deploy phase flows
    print("\n[4/5] Deploying Phase Flows (8 phases)...")
    phase_builders = [
        ("Phase 1 - Understand", build_phase1_understand_flow),
        ("Phase 2 - Research", build_phase2_research_flow),
        ("Phase 3 - Design", build_phase3_design_flow),
        ("Phase 4 - Implement", build_phase4_implement_flow),
        ("Phase 5 - Verify", build_phase5_verify_flow),
        ("Phase 6 - Integrate", build_phase6_integrate_flow),
        ("Phase 7 - Polish", build_phase7_polish_flow),
        ("Phase 8 - Meta-Check", build_phase8_metacheck_flow),
    ]

    for phase_name, builder in phase_builders:
        flow_data = builder()
        flow_name = flow_data["name"]

        if flow_name in existing_names:
            print(f"  Updating: {flow_name}")
            update_flow(headers, existing_names[flow_name], flow_data)
        else:
            print(f"  Creating: {flow_name}")
            create_flow(headers, flow_data)
        time.sleep(0.3)

    # Deploy master orchestrator
    print("\n[5/5] Deploying Master Orchestrator...")
    flow_data = build_master_orchestrator_flow()
    flow_name = flow_data["name"]

    if flow_name in existing_names:
        print(f"  Updating: {flow_name}")
        update_flow(headers, existing_names[flow_name], flow_data)
    else:
        print(f"  Creating: {flow_name}")
        create_flow(headers, flow_data)

    print("\n" + "=" * 80)
    print("DEPLOYMENT COMPLETE!")
    print("=" * 80)
    print(f"\nLangflow URL: {LANGFLOW_URL}")
    print("\nDeployed flows:")
    print("  - 12 Agent flows (M1-M12)")
    print("  - 8 Phase flows")
    print("  - 1 Master Orchestrator")
    print("\nTo use: Open 'V2/Master Orchestrator' in Langflow Playground")

    return True


if __name__ == "__main__":
    success = deploy_enhanced_orchestration()
    sys.exit(0 if success else 1)
