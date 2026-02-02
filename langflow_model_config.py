#!/usr/bin/env python3
"""
Langflow Model Configuration - OpenCode v9.5 Alignment
Configures Langflow to use the same models as OpenCode with internet research capabilities
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Any

class LangflowModelConfig:
    """
    Manages Langflow model configuration to match OpenCode v9.5
    Ensures all models have internet research capabilities where applicable
    """
    
    # OpenCode v9.5 Model Registry (from MODELS.md)
    OPENCODE_MODELS = {
        # Primary Orchestrator
        "orchestrator": {
            "provider": "moonshot",
            "model": "kimi-k2.5",
            "api_key_env": "MOONSHOT_API_KEY",
            "base_url": "https://api.moonshot.ai/v1",
            "context": 256000,
            "output": 32000,
            "features": ["vision", "reasoning", "agent_swarm"],
            "internet_access": False  # Use researcher for internet
        },
        
        # Planners (5 parallel)
        "planner-1": {
            "provider": "google",
            "model": "gemini-3-pro-preview",
            "api_key_env": "GOOGLE_API_KEY",
            "base_url": "https://generativelanguage.googleapis.com/v1beta",
            "context": 1000000,
            "output": 64000,
            "features": ["architecture", "data_analysis", "large_context"],
            "internet_access": True  # Gemini has search capability
        },
        "planner-2": {
            "provider": "anthropic",
            "model": "claude-sonnet-4-5",
            "api_key_env": "ANTHROPIC_API_KEY",
            "base_url": "https://api.anthropic.com",
            "context": 200000,
            "output": 64000,
            "features": ["security", "validation", "reasoning"],
            "internet_access": False
        },
        "planner-3": {
            "provider": "moonshot",
            "model": "kimi-k2.5",
            "api_key_env": "MOONSHOT_API_KEY",
            "base_url": "https://api.moonshot.ai/v1",
            "context": 256000,
            "output": 32000,
            "features": ["workflow", "creative", "agent_swarm"],
            "internet_access": False
        },
        "planner-4": {
            "provider": "deepseek",
            "model": "deepseek-chat",
            "api_key_env": "DEEPSEEK_API_KEY",
            "base_url": "https://api.deepseek.com/v1",
            "context": 131072,
            "output": 8192,
            "features": ["logic", "algorithms", "deep_reasoning"],
            "internet_access": False
        },
        "planner-5": {
            "provider": "zai",
            "model": "glm-4.7",
            "api_key_env": "ZAI_API_KEY",
            "base_url": "https://api.z.ai/api/coding/paas/v4/",
            "context": 200000,
            "output": 128000,
            "features": ["implementation", "testing", "coding"],
            "internet_access": False
        },
        
        # Coders
        "coder": {
            "provider": "moonshot",
            "model": "kimi-k2.5",
            "api_key_env": "MOONSHOT_API_KEY",
            "base_url": "https://api.moonshot.ai/v1",
            "context": 256000,
            "output": 32000,
            "features": ["coding", "implementation"],
            "internet_access": False
        },
        "coder-fast": {
            "provider": "google",
            "model": "gemini-3-flash-preview",
            "api_key_env": "GOOGLE_API_KEY",
            "base_url": "https://generativelanguage.googleapis.com/v1beta",
            "context": 1000000,
            "output": 64000,
            "features": ["fast_editing", "simple_tasks"],
            "internet_access": True
        },
        "coder-glm": {
            "provider": "zai",
            "model": "glm-4.7",
            "api_key_env": "ZAI_API_KEY",
            "base_url": "https://api.z.ai/api/coding/paas/v4/",
            "context": 200000,
            "output": 128000,
            "features": ["stable_coding", "typescript"],
            "internet_access": False
        },
        "coder-deepseek": {
            "provider": "deepseek",
            "model": "deepseek-chat",
            "api_key_env": "DEEPSEEK_API_KEY",
            "base_url": "https://api.deepseek.com/v1",
            "context": 131072,
            "output": 8192,
            "features": ["complex_logic", "algorithms"],
            "internet_access": False
        },
        
        # Validators (Cross-provider)
        "validator": {
            "provider": "google",
            "model": "gemini-3-flash-preview",
            "api_key_env": "GOOGLE_API_KEY",
            "base_url": "https://generativelanguage.googleapis.com/v1beta",
            "context": 1000000,
            "output": 64000,
            "features": ["cross_validation"],
            "internet_access": True
        },
        "validator-anthropic": {
            "provider": "anthropic",
            "model": "claude-haiku-4-5",
            "api_key_env": "ANTHROPIC_API_KEY",
            "base_url": "https://api.anthropic.com",
            "context": 200000,
            "output": 64000,
            "features": ["cross_validation"],
            "internet_access": False
        },
        
        # Specialists
        "tester": {
            "provider": "zai",
            "model": "glm-4.7",
            "api_key_env": "ZAI_API_KEY",
            "base_url": "https://api.z.ai/api/coding/paas/v4/",
            "context": 200000,
            "output": 128000,
            "features": ["testing", "qa"],
            "internet_access": False
        },
        "reviewer": {
            "provider": "anthropic",
            "model": "claude-sonnet-4-5",
            "api_key_env": "ANTHROPIC_API_KEY",
            "base_url": "https://api.anthropic.com",
            "context": 200000,
            "output": 64000,
            "features": ["code_review", "quality"],
            "internet_access": False
        },
        "security": {
            "provider": "anthropic",
            "model": "claude-sonnet-4-5",
            "api_key_env": "ANTHROPIC_API_KEY",
            "base_url": "https://api.anthropic.com",
            "context": 200000,
            "output": 64000,
            "features": ["security_analysis", "vulnerability_detection"],
            "internet_access": False
        },
        
        # Internet Research Specialists (FULL INTERNET ACCESS)
        "researcher": {
            "provider": "perplexity",
            "model": "sonar-pro",
            "api_key_env": "PERPLEXITY_API_KEY",
            "base_url": "https://api.perplexity.ai",
            "context": 128000,
            "output": 64000,
            "features": ["web_search", "citations", "research"],
            "internet_access": True,
            "search_capabilities": {
                "real_time": True,
                "citations": True,
                "sources": ["web", "academic", "news"]
            }
        },
        "analyst": {
            "provider": "google",
            "model": "gemini-3-pro-preview",
            "api_key_env": "GOOGLE_API_KEY",
            "base_url": "https://generativelanguage.googleapis.com/v1beta",
            "context": 1000000,
            "output": 64000,
            "features": ["data_analysis", "metrics", "reporting", "search"],
            "internet_access": True,
            "search_capabilities": {
                "real_time": True,
                "grounding": True
            }
        },
        
        # Backup/Fast Options
        "coder-groq": {
            "provider": "groq",
            "model": "llama-3.3-70b-versatile",
            "api_key_env": "GROQ_API_KEY",
            "base_url": "https://api.groq.com/openai/v1",
            "context": 128000,
            "output": 8192,
            "features": ["ultra_fast", "bulk_tasks"],
            "internet_access": False
        }
    }
    
    # Models with FULL internet research access
    INTERNET_RESEARCH_MODELS = ["researcher", "analyst", "planner-1", "coder-fast", "validator"]
    
    def __init__(self):
        self.config_dir = Path("config")
        self.config_dir.mkdir(exist_ok=True)
        self.config_file = self.config_dir / "langflow_models.json"
        self.load_config()
    
    def load_config(self):
        """Load or create model configuration"""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
        else:
            self.config = {
                "version": "9.5.0",
                "models": self.OPENCODE_MODELS,
                "api_keys": {},
                "defaults": {
                    "orchestrator": "orchestrator",
                    "planner": "planner-1",
                    "coder": "coder",
                    "validator": "validator",
                    "tester": "tester",
                    "researcher": "researcher"
                }
            }
            self.save_config()
    
    def save_config(self):
        """Save configuration"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def get_model_config(self, agent_id: str) -> Dict[str, Any]:
        """Get configuration for a specific agent"""
        return self.OPENCODE_MODELS.get(agent_id, {})
    
    def get_internet_research_models(self) -> List[str]:
        """Get list of models with internet access"""
        return self.INTERNET_RESEARCH_MODELS
    
    def generate_env_template(self) -> str:
        """Generate .env template with required API keys"""
        template = """# Langflow OpenCode Model Configuration
# Copy this to your .env file and fill in your API keys
# These should match your OpenCode configuration

# ============================================
# REQUIRED API KEYS (Get from OpenCode .env)
# ============================================

# Moonshot AI (Kimi K2.5) - Primary Orchestrator & Coder
MOONSHOT_API_KEY=your_moonshot_api_key_here

# Google (Gemini 3 Pro/Flash) - Planning & Fast Coding
GOOGLE_API_KEY=your_google_api_key_here

# Anthropic (Claude Sonnet 4.5/Haiku 4.5) - Security & Review
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Z.AI (GLM-4.7) - Implementation & Testing
ZAI_API_KEY=your_zai_api_key_here

# DeepSeek (V3.2) - Complex Logic & Algorithms
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# Perplexity (Sonar Pro) - Internet Research with Citations
PERPLEXITY_API_KEY=your_perplexity_api_key_here

# Groq (Llama 3.3 70B) - Ultra-fast backup
GROQ_API_KEY=your_groq_api_key_here

# ============================================
# INTERNET RESEARCH CONFIGURATION
# ============================================

# Enable internet search for research models
ENABLE_INTERNET_SEARCH=true
RESEARCH_CITATIONS=true
REAL_TIME_SEARCH=true

# Perplexity-specific settings
PERPLEXITY_SEARCH_MODE=sonar-pro  # Options: sonar, sonar-pro, sonar-reasoning
PERPLEXITY_CITATIONS=true
PERPLEXITY_RECENCY_DAYS=30

# Google Gemini search settings
GEMINI_GROUNDING=true
GEMINI_SEARCH_RECENCY=default  # Options: default, recent

# ============================================
# LANGFLOW SERVER CONFIGURATION
# ============================================

LANGFLOW_HOST=0.0.0.0
LANGFLOW_PORT=7860
LANGFLOW_AUTO_LOGIN=true
LANGFLOW_SUPERUSER=admin
LANGFLOW_SUPERUSER_PASSWORD=your_secure_password

# Database
LANGFLOW_DATABASE_URL=sqlite:///./langflow.db

# Enable environment variable storage
LANGFLOW_STORE_ENVIRONMENT_VARIABLES=true

# Logging
LANGFLOW_LOG_LEVEL=INFO

# ============================================
# MCP GATEWAY (Render Deployment)
# ============================================

MCP_GATEWAY_URL=https://langflow-mcp.onrender.com
MCP_ENABLED=true
MCP_MEMORY_SYNC=true
"""
        return template
    
    def create_langflow_component_config(self, agent_id: str) -> Dict:
        """
        Generate Langflow component configuration for an agent
        """
        model_config = self.get_model_config(agent_id)
        
        if not model_config:
            return {}
        
        component = {
            "name": f"{agent_id}_{model_config['provider']}",
            "display_name": f"{agent_id.replace('-', ' ').title()} - {model_config['model']}",
            "provider": model_config["provider"],
            "model": model_config["model"],
            "api_key_env": model_config["api_key_env"],
            "base_url": model_config.get("base_url", ""),
            "context_window": model_config["context"],
            "max_tokens": model_config["output"],
            "features": model_config["features"],
            "internet_access": model_config.get("internet_access", False),
            "temperature": 0.7,
            "top_p": 0.95,
        }
        
        # Add search capabilities if applicable
        if model_config.get("internet_access"):
            component["search_config"] = model_config.get("search_capabilities", {})
            component["system_prompt"] = self._get_research_prompt(agent_id)
        else:
            component["system_prompt"] = self._get_standard_prompt(agent_id)
        
        return component
    
    def _get_research_prompt(self, agent_id: str) -> str:
        """Get system prompt for internet research models"""
        prompts = {
            "researcher": """You are an expert researcher with full internet access via Perplexity Sonar Pro.

Capabilities:
- Search the web in real-time
- Access academic papers, news, and documentation
- Provide citations for all findings
- Synthesize information from multiple sources

Instructions:
1. Always cite your sources with URLs
2. Provide recent and relevant information
3. Distinguish between facts and opinions
4. Include publication dates when available
5. Search for conflicting viewpoints when appropriate

When given a research task:
1. Break down the topic into searchable queries
2. Gather information from authoritative sources
3. Synthesize findings into a coherent report
4. Include citations in [Source: URL] format
5. Highlight key insights and actionable recommendations""",
            
            "analyst": """You are a data analyst with access to Google Gemini's search capabilities.

Capabilities:
- Analyze data with grounding in real-time information
- Search for relevant datasets and metrics
- Validate assumptions with current data
- Generate reports with evidence-based insights

Instructions:
1. Use search to validate data and findings
2. Ground analysis in real-world context
3. Provide sources for all data points
4. Include confidence levels for predictions
5. Highlight data limitations and biases

When analyzing:
1. Search for relevant benchmarks and comparisons
2. Validate trends with current information
3. Provide data-driven recommendations
4. Include uncertainty ranges where appropriate""",
            
            "planner-1": """You are a systems architect with access to current best practices via Google Gemini.

Capabilities:
- Research latest architecture patterns
- Access current technology documentation
- Validate design decisions with real-world examples
- Ground recommendations in current industry standards

Instructions:
1. Search for current best practices before recommending
2. Validate technology choices with recent information
3. Consider scalability based on current standards
4. Include security considerations from recent threats
5. Reference official documentation and case studies""",
            
            "coder-fast": """You are a fast coder with search access for quick lookups.

Capabilities:
- Quickly search for syntax and API references
- Access documentation for libraries and frameworks
- Validate code patterns with current best practices

Instructions:
1. Use search for syntax verification
2. Reference official documentation
3. Follow current coding standards
4. Consider performance implications""",
            
            "validator": """You are a validator with search access for fact-checking.

Capabilities:
- Verify facts against current information
- Search for authoritative sources
- Cross-reference claims with evidence

Instructions:
1. Search to verify factual claims
2. Check against authoritative sources
3. Identify outdated information
4. Provide confidence ratings"""
        }
        
        return prompts.get(agent_id, "You have internet search capabilities. Use them wisely.")
    
    def _get_standard_prompt(self, agent_id: str) -> str:
        """Get standard system prompt for non-research models"""
        prompts = {
            "orchestrator": "You are the Master Orchestrator using Kimi K2.5. Coordinate multi-agent execution, decompose tasks, and synthesize results. You have 256K context and can spawn up to 100 subagents.",
            
            "planner-2": "You are a Security & Validation Planner using Claude Sonnet 4.5. Focus on security architecture, threat modeling, and validation strategies.",
            
            "planner-3": "You are a Workflow & Creative Planner using Kimi K2.5. Design efficient workflows and creative solutions.",
            
            "planner-4": "You are a Logic & Algorithms Planner using DeepSeek V3.2. Design complex algorithms and logical structures.",
            
            "planner-5": "You are an Implementation & Testing Planner using GLM-4.7. Create detailed implementation plans and testing strategies.",
            
            "coder": "You are a Primary Coder using Kimi K2.5. Write high-quality, maintainable code with proper error handling.",
            
            "coder-glm": "You are a Stable Coder using GLM-4.7. Focus on reliable implementation and TypeScript/JavaScript.",
            
            "coder-deepseek": "You are a Logic Coder using DeepSeek V3.2. Handle complex algorithms and mathematical logic.",
            
            "tester": "You are a Test Engineer using GLM-4.7. Create comprehensive test suites with 90%+ coverage.",
            
            "reviewer": "You are a Code Reviewer using Claude Sonnet 4.5. Review code for quality, security, and best practices.",
            
            "security": "You are a Security Analyst using Claude Sonnet 4.5. Identify vulnerabilities and security issues.",
            
            "validator-anthropic": "You are a Cross-Model Validator using Claude Haiku 4.5. Validate outputs from other model families."
        }
        
        return prompts.get(agent_id, "Complete your assigned task with high quality.")
    
    def export_to_langflow(self, output_dir: str = "config/langflow_components"):
        """
        Export all model configurations as Langflow-compatible JSON
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        for agent_id in self.OPENCODE_MODELS.keys():
            config = self.create_langflow_component_config(agent_id)
            if config:
                file_path = output_path / f"{agent_id}.json"
                with open(file_path, 'w') as f:
                    json.dump(config, f, indent=2)
                print(f"✅ Exported: {file_path}")
        
        print(f"\n📁 All components exported to: {output_dir}")
        print("\nTo use in Langflow:")
        print("1. Copy these JSON files to your Langflow components directory")
        print("2. Set the API keys in your .env file")
        print("3. Restart Langflow")
    
    def get_setup_instructions(self) -> str:
        """Get complete setup instructions"""
        return """
╔════════════════════════════════════════════════════════════════════╗
║           LANGFLOW OPENCODE MODEL SETUP GUIDE                      ║
╚════════════════════════════════════════════════════════════════════╝

STEP 1: Copy API Keys from OpenCode
─────────────────────────────────────
1. Open your OpenCode .env file (usually in ~/.config/opencode/.env)
2. Copy these API keys to your Langflow .env file:

   MOONSHOT_API_KEY=...
   GOOGLE_API_KEY=...
   ANTHROPIC_API_KEY=...
   ZAI_API_KEY=...
   DEEPSEEK_API_KEY=...
   PERPLEXITY_API_KEY=...
   GROQ_API_KEY=...

STEP 2: Enable Internet Research
─────────────────────────────────
The following models have FULL internet access:
✅ researcher (Perplexity Sonar Pro) - Best for research with citations
✅ analyst (Google Gemini Pro) - Best for data analysis with grounding
✅ planner-1 (Google Gemini Pro) - Architecture with current best practices
✅ coder-fast (Google Gemini Flash) - Quick lookups
✅ validator (Google Gemini Flash) - Fact checking

These models can:
- Search the web in real-time
- Access current documentation
- Provide citations
- Validate against current information

STEP 3: Configure Langflow
───────────────────────────
1. Ensure LANGFLOW_STORE_ENVIRONMENT_VARIABLES=true in .env
2. Start Langflow: python -m langflow run
3. Go to Settings → Components
4. Verify all OpenCode models are available

STEP 4: Test Internet Access
────────────────────────────
Create a test flow with the 'researcher' agent:
- Task: "Research the latest Python 3.12 features"
- Should return current information with citations

STEP 5: Use in Dynamic Flows
─────────────────────────────
python run_task.py "Your complex task here"

The system will automatically:
✓ Select appropriate models
✓ Grant internet access to research tasks
✓ Use MCP for memory (avoid truncation)
✓ Create a new flow with all agents connected

═══════════════════════════════════════════════════════════════════════

INTERNET RESEARCH BEST PRACTICES:

1. Use 'researcher' agent for:
   - Web searches
   - Finding documentation
   - Getting current information
   - Academic research

2. Use 'analyst' agent for:
   - Data validation
   - Market research
   - Trend analysis
   - Benchmarking

3. Use 'planner-1' for:
   - Current architecture patterns
   - Technology comparisons
   - Best practices research

4. All research includes:
   - Source citations
   - Publication dates
   - Confidence ratings
   - Alternative viewpoints

═══════════════════════════════════════════════════════════════════════
"""


if __name__ == "__main__":
    config = LangflowModelConfig()
    
    print(config.get_setup_instructions())
    
    # Generate .env template
    print("\n" + "="*70)
    print("📄 ENVIRONMENT FILE TEMPLATE")
    print("="*70)
    print(config.generate_env_template())
    
    # Export components
    print("\n" + "="*70)
    print("📦 EXPORTING COMPONENTS")
    print("="*70)
    config.export_to_langflow()
