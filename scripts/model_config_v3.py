"""
MODEL CONFIGURATION v3.0 - RESEARCHED SPECIFICATIONS
=====================================================

Based on official documentation and research (January 2026):

MODEL SPECIFICATIONS:
--------------------
1. Claude Opus 4.5:     200K context, 64K max output
2. Claude Sonnet 4.5:   200K context, 64K max output
3. GPT-5.2:             400K context, 128K max output
4. GPT-5.1:             400K context, 128K max output
5. DeepSeek Reasoner:   64K input, 32K max output (quality degrades >8K)
6. DeepSeek Chat:       128K context, 32K max output
7. Gemini 3 Pro:        1M context, 64K max output
8. Gemini 3 Flash:      1M context, 32K max output
9. GLM-4.7:             200K context, 128K max output
10. Kimi K2:            128K context, 16K max output
11. GPT-OSS-120B (Groq): 128K context, 32K max output
12. Perplexity Sonar Pro: 200K context, ~8K practical output

TEMPERATURE GUIDELINES:
----------------------
- Analytical/Precision (0.0-0.3): Code, facts, validation, verification
- Balanced (0.4-0.6): Planning, integration, editing
- Creative (0.7-1.0): Ideation, brainstorming, alternatives

Sources:
- https://platform.claude.com/docs/en/build-with-claude/context-windows
- https://openai.com/index/introducing-gpt-5-2/
- https://api-docs.deepseek.com/guides/reasoning_model
- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/3-pro
- https://llm-stats.com/models/glm-4.7
- https://moonshotai.github.io/Kimi-K2/
- https://docs.perplexity.ai/getting-started/models/models/sonar-pro
"""

# Properly researched model configurations
MODEL_SPECS = {
    # Claude models - 200K context, 64K output
    "claude-opus-4-5-20251101": {
        "context_window": 200000,
        "max_output": 64000,
        "recommended_output": 16384,  # practical for most tasks
        "provider": "anthropic"
    },
    "claude-sonnet-4-5-20250929": {
        "context_window": 200000,
        "max_output": 64000,
        "recommended_output": 16384,
        "provider": "anthropic"
    },

    # OpenAI GPT-5 models - 400K context, 128K output
    "gpt-5.2": {
        "context_window": 400000,
        "max_output": 128000,
        "recommended_output": 32768,
        "provider": "openai"
    },
    "gpt-5.1": {
        "context_window": 400000,
        "max_output": 128000,
        "recommended_output": 32768,
        "provider": "openai"
    },

    # DeepSeek models
    "deepseek-reasoner": {
        "context_window": 64000,
        "max_output": 32000,
        "recommended_output": 8192,  # quality degrades above 8K
        "provider": "deepseek"
    },
    "deepseek-chat": {
        "context_window": 128000,
        "max_output": 32000,
        "recommended_output": 16384,
        "provider": "deepseek"
    },

    # Google Gemini models - 1M context
    "gemini-3-pro-preview": {
        "context_window": 1000000,
        "max_output": 65536,
        "recommended_output": 32768,
        "provider": "google"
    },
    "gemini-3-flash-preview": {
        "context_window": 1000000,
        "max_output": 32768,
        "recommended_output": 16384,
        "provider": "google"
    },

    # GLM-4.7 - 200K context, 128K output
    "glm-4.7": {
        "context_window": 200000,
        "max_output": 128000,
        "recommended_output": 32768,
        "provider": "zai"
    },

    # Kimi K2 - 128K context
    "moonshotai/kimi-k2-instruct-0905": {
        "context_window": 128000,
        "max_output": 16000,
        "recommended_output": 8192,
        "provider": "groq"
    },

    # GPT-OSS-120B via Groq
    "openai/gpt-oss-120b": {
        "context_window": 128000,
        "max_output": 32000,
        "recommended_output": 16384,
        "provider": "groq"
    },

    # Perplexity Sonar Pro
    "sonar-pro": {
        "context_window": 200000,
        "max_output": 8000,  # practical limit
        "recommended_output": 4096,
        "provider": "perplexity"
    }
}

# Temperature settings by task type
TEMPERATURE_BY_ROLE = {
    # Analytical/Precision tasks - LOW temperature (0.0-0.3)
    "planner": 0.4,           # Balanced - needs structure but some creativity
    "researcher": 0.2,        # Low - factual accuracy critical
    "verifier": 0.1,          # Very low - precision critical
    "test_engineer": 0.2,     # Low - code accuracy critical

    # Balanced tasks - MEDIUM temperature (0.4-0.6)
    "architect": 0.5,         # Medium - design requires exploration
    "integrator": 0.3,        # Low-medium - consistency important
    "meta_reasoner": 0.4,     # Medium - meta-analysis needs balance
    "editor": 0.5,            # Medium - clarity with style
    "domain_expert": 0.3,     # Low-medium - knowledge accuracy

    # Creative tasks - HIGH temperature (0.7-1.0)
    "ideator": 0.9,           # High - creativity is the goal
    "critic": 0.6,            # Medium-high - find diverse issues

    # Code generation - LOW temperature
    "implementer": 0.1,       # Very low - code must be correct

    # Orchestration
    "orchestrator": 0.2       # Low - coordination precision
}

# Recommended max_tokens by role (based on task needs)
MAX_TOKENS_BY_ROLE = {
    "planner": 16384,         # Detailed plans
    "researcher": 8192,       # Summaries with citations
    "architect": 32768,       # Full architecture docs
    "implementer": 32768,     # Complete code files
    "ideator": 16384,         # Multiple alternatives
    "verifier": 8192,         # Verification reports
    "critic": 16384,          # Detailed critiques
    "editor": 32768,          # Full polished output
    "domain_expert": 8192,    # Domain knowledge
    "meta_reasoner": 8192,    # Meta-analysis
    "integrator": 32768,      # Combined outputs
    "test_engineer": 16384,   # Test suites
    "orchestrator": 4096      # Coordination decisions
}
