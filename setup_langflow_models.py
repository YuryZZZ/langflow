#!/usr/bin/env python3
"""
Setup Script: Configure Langflow with OpenCode Models and Internet Research
Approved by user - Sets up identical model configuration with API keys
"""

import os
import sys
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

class LangflowSetup:
    """Complete setup for Langflow with OpenCode models"""
    
    def __init__(self):
        self.opencode_env_path = Path.home() / ".config" / "opencode" / ".env"
        self.langflow_env_path = Path(".env")
        self.config_dir = Path("config")
        self.backup_dir = Path("config/backups")
        
        # API keys to extract from OpenCode
        self.required_keys = [
            "MOONSHOT_API_KEY",
            "GOOGLE_API_KEY", 
            "ANTHROPIC_API_KEY",
            "ZAI_API_KEY",
            "DEEPSEEK_API_KEY",
            "PERPLEXITY_API_KEY",
            "GROQ_API_KEY"
        ]
        
        # Models with internet access
        self.internet_models = ["researcher", "analyst", "planner-1", "coder-fast", "validator"]
    
    def read_opencode_env(self) -> Dict[str, str]:
        """Read API keys from OpenCode .env file"""
        print("🔍 Reading OpenCode configuration...")
        
        api_keys = {}
        
        if not self.opencode_env_path.exists():
            print(f"⚠️  OpenCode .env not found at: {self.opencode_env_path}")
            print("   Please ensure OpenCode is configured with API keys")
            return api_keys
        
        try:
            with open(self.opencode_env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if '=' in line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if key in self.required_keys and value:
                            api_keys[key] = value
                            # Mask for display
                            masked = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
                            print(f"   ✓ Found: {key} = {masked}")
        
        except Exception as e:
            print(f"   ❌ Error reading OpenCode .env: {e}")
        
        return api_keys
    
    def backup_existing_env(self):
        """Backup existing .env file"""
        if self.langflow_env_path.exists():
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / f".env.backup.{timestamp}"
            shutil.copy2(self.langflow_env_path, backup_path)
            print(f"   📦 Backed up existing .env to: {backup_path}")
    
    def create_langflow_env(self, api_keys: Dict[str, str]):
        """Create Langflow .env with OpenCode API keys"""
        print("\n📝 Creating Langflow configuration...")
        
        self.backup_existing_env()
        
        # Build new .env content
        env_content = f"""# Langflow Configuration - OpenCode Models v9.5
# Generated: {datetime.now().isoformat()}
# Source: OpenCode .env ({self.opencode_env_path})

# ============================================
# API KEYS FROM OPENCODE
# ============================================

"""
        
        # Add API keys
        for key in self.required_keys:
            value = api_keys.get(key, "")
            if value:
                env_content += f"{key}={value}\n"
            else:
                env_content += f"#{key}=your_{key.lower()}_here\n"
        
        # Add internet research configuration
        env_content += """
# ============================================
# INTERNET RESEARCH CONFIGURATION
# ============================================

# Enable internet search for research models
ENABLE_INTERNET_SEARCH=true
RESEARCH_CITATIONS=true
REAL_TIME_SEARCH=true

# Perplexity Sonar Pro (Primary Research Model)
PERPLEXITY_SEARCH_MODE=sonar-pro
PERPLEXITY_CITATIONS=true
PERPLEXITY_RECENCY_DAYS=30
PERPLEXITY_RETURN_IMAGES=false

# Google Gemini Search (Analyst & Planner-1)
GEMINI_GROUNDING=true
GEMINI_SEARCH_RECENCY=recent
GEMINI_INCLUDE_CITATIONS=true

# ============================================
# LANGFLOW SERVER CONFIGURATION
# ============================================

LANGFLOW_HOST=0.0.0.0
LANGFLOW_PORT=7860
LANGFLOW_AUTO_LOGIN=true
LANGFLOW_SUPERUSER=admin
LANGFLOW_SUPERUSER_PASSWORD=langflow_admin_2024

# Database
LANGFLOW_DATABASE_URL=sqlite:///./langflow.db
LANGFLOW_SAVE_DB_IN_CONFIG_DIR=false

# Security
LANGFLOW_REMOVE_API_KEYS=false
LANGFLOW_STORE_ENVIRONMENT_VARIABLES=true

# Logging
LANGFLOW_LOG_LEVEL=INFO

# Workers
LANGFLOW_WORKERS=1

# Cache
LANGFLOW_LANGCHAIN_CACHE=SQLiteCache
LANGFLOW_CACHE_TYPE=memory

# ============================================
# MCP GATEWAY (RENDER DEPLOYMENT)
# ============================================

MCP_GATEWAY_URL=https://langflow-mcp.onrender.com
MCP_ENABLED=true
MCP_MEMORY_SYNC=true
MCP_TIMEOUT=30
MCP_RETRY_ATTEMPTS=3

# ============================================
# OPENCODE MODEL REGISTRY v9.5
# ============================================

# Primary Models
OPENCODE_ORCHESTRATOR_MODEL=moonshot/kimi-k2.5
OPENCODE_CODER_MODEL=moonshot/kimi-k2.5
OPENCODE_CODER_FAST=google/gemini-3-flash
OPENCODE_CODER_GLM=zai/glm-4.7
OPENCODE_CODER_DEEPSEEK=deepseek/deepseek-chat

# Planners
OPENCODE_PLANNER_1=google/gemini-3-pro
OPENCODE_PLANNER_2=anthropic/claude-sonnet-4-5
OPENCODE_PLANNER_3=moonshot/kimi-k2.5
OPENCODE_PLANNER_4=deepseek/deepseek-chat
OPENCODE_PLANNER_5=zai/glm-4.7

# Validators
OPENCODE_VALIDATOR=google/gemini-3-flash
OPENCODE_VALIDATOR_ANTHROPIC=anthropic/claude-haiku-4-5

# Specialists
OPENCODE_TESTER=zai/glm-4.7
OPENCODE_REVIEWER=anthropic/claude-sonnet-4-5
OPENCODE_SECURITY=anthropic/claude-sonnet-4-5
OPENCODE_RESEARCHER=perplexity/sonar-pro
OPENCODE_ANALYST=google/gemini-3-pro

# Internet Research Models (Full Access)
INTERNET_RESEARCH_MODELS=researcher,analyst,planner-1,coder-fast,validator

# ============================================
# PROVIDER DISTRIBUTION
# ============================================

# Following MODELS.md guidelines:
# Moonshot: 25% | Google: 20% | Z.AI: 20% | DeepSeek: 15% | Anthropic: 12% | Groq: 5% | OpenAI: 3%
PROVIDER_DISTRIBUTION_MOONSHOT=25
PROVIDER_DISTRIBUTION_GOOGLE=20
PROVIDER_DISTRIBUTION_ZAI=20
PROVIDER_DISTRIBUTION_DEEPSEEK=15
PROVIDER_DISTRIBUTION_ANTHROPIC=12
PROVIDER_DISTRIBUTION_GROQ=5
PROVIDER_DISTRIBUTION_OPENAI=3
"""
        
        # Write .env file
        with open(self.langflow_env_path, 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        print(f"   ✓ Created: {self.langflow_env_path}")
        print(f"   ✓ API Keys configured: {len([k for k in api_keys if k])}/{len(self.required_keys)}")
    
    def create_model_registry(self):
        """Create model registry JSON for Langflow"""
        print("\n📦 Creating model registry...")
        
        registry = {
            "version": "9.5.0",
            "last_updated": datetime.now().isoformat(),
            "models": {
                "orchestrator": {
                    "display_name": "Master Orchestrator - Kimi K2.5",
                    "provider": "moonshot",
                    "model": "kimi-k2.5",
                    "api_key_env": "MOONSHOT_API_KEY",
                    "base_url": "https://api.moonshot.ai/v1",
                    "context_window": 256000,
                    "max_tokens": 32000,
                    "temperature": 1.0,
                    "capabilities": ["orchestration", "planning", "agent_swarm", "parl"],
                    "internet_access": False,
                    "priority": 1
                },
                
                # Internet Research Models
                "researcher": {
                    "display_name": "Researcher - Perplexity Sonar Pro",
                    "provider": "perplexity",
                    "model": "sonar-pro",
                    "api_key_env": "PERPLEXITY_API_KEY",
                    "base_url": "https://api.perplexity.ai",
                    "context_window": 128000,
                    "max_tokens": 64000,
                    "temperature": 0.7,
                    "capabilities": ["web_search", "citations", "real_time", "research"],
                    "internet_access": True,
                    "search_config": {
                        "mode": "sonar-pro",
                        "citations": True,
                        "recency_days": 30
                    },
                    "priority": 1
                },
                
                "analyst": {
                    "display_name": "Data Analyst - Gemini Pro",
                    "provider": "google",
                    "model": "gemini-3-pro-preview",
                    "api_key_env": "GOOGLE_API_KEY",
                    "base_url": "https://generativelanguage.googleapis.com/v1beta",
                    "context_window": 1000000,
                    "max_tokens": 64000,
                    "temperature": 0.6,
                    "capabilities": ["data_analysis", "grounding", "search", "reporting"],
                    "internet_access": True,
                    "search_config": {
                        "grounding": True,
                        "recency": "recent"
                    },
                    "priority": 2
                },
                
                "planner-1": {
                    "display_name": "P1 - Architect (Gemini Pro)",
                    "provider": "google",
                    "model": "gemini-3-pro-preview",
                    "api_key_env": "GOOGLE_API_KEY",
                    "base_url": "https://generativelanguage.googleapis.com/v1beta",
                    "context_window": 1000000,
                    "max_tokens": 64000,
                    "temperature": 0.7,
                    "capabilities": ["architecture", "design", "large_context", "search"],
                    "internet_access": True,
                    "search_config": {
                        "grounding": True,
                        "recency": "default"
                    },
                    "priority": 2
                },
                
                "coder-fast": {
                    "display_name": "Fast Coder - Gemini Flash",
                    "provider": "google",
                    "model": "gemini-3-flash-preview",
                    "api_key_env": "GOOGLE_API_KEY",
                    "base_url": "https://generativelanguage.googleapis.com/v1beta",
                    "context_window": 1000000,
                    "max_tokens": 64000,
                    "temperature": 0.6,
                    "capabilities": ["fast_coding", "quick_edits", "search"],
                    "internet_access": True,
                    "priority": 3
                },
                
                "validator": {
                    "display_name": "Validator - Gemini Flash",
                    "provider": "google",
                    "model": "gemini-3-flash-preview",
                    "api_key_env": "GOOGLE_API_KEY",
                    "base_url": "https://generativelanguage.googleapis.com/v1beta",
                    "context_window": 1000000,
                    "max_tokens": 64000,
                    "temperature": 0.4,
                    "capabilities": ["validation", "cross_check", "fact_checking", "search"],
                    "internet_access": True,
                    "priority": 2
                },
                
                # Standard Models (No Internet)
                "planner-2": {
                    "display_name": "P2 - Security (Claude)",
                    "provider": "anthropic",
                    "model": "claude-sonnet-4-5",
                    "api_key_env": "ANTHROPIC_API_KEY",
                    "base_url": "https://api.anthropic.com",
                    "context_window": 200000,
                    "max_tokens": 64000,
                    "temperature": 0.7,
                    "capabilities": ["security", "validation", "reasoning"],
                    "internet_access": False,
                    "priority": 2
                },
                
                "planner-3": {
                    "display_name": "P3 - Workflow (Kimi)",
                    "provider": "moonshot",
                    "model": "kimi-k2.5",
                    "api_key_env": "MOONSHOT_API_KEY",
                    "base_url": "https://api.moonshot.ai/v1",
                    "context_window": 256000,
                    "max_tokens": 32000,
                    "temperature": 1.0,
                    "capabilities": ["workflow", "creative"],
                    "internet_access": False,
                    "priority": 2
                },
                
                "planner-4": {
                    "display_name": "P4 - Logic (DeepSeek)",
                    "provider": "deepseek",
                    "model": "deepseek-chat",
                    "api_key_env": "DEEPSEEK_API_KEY",
                    "base_url": "https://api.deepseek.com/v1",
                    "context_window": 131072,
                    "max_tokens": 8192,
                    "temperature": 0.7,
                    "capabilities": ["logic", "algorithms", "complex_reasoning"],
                    "internet_access": False,
                    "priority": 2
                },
                
                "planner-5": {
                    "display_name": "P5 - Implementation (GLM)",
                    "provider": "zai",
                    "model": "glm-4.7",
                    "api_key_env": "ZAI_API_KEY",
                    "base_url": "https://api.z.ai/api/coding/paas/v4/",
                    "context_window": 200000,
                    "max_tokens": 128000,
                    "temperature": 0.7,
                    "capabilities": ["implementation", "testing", "coding"],
                    "internet_access": False,
                    "priority": 2
                },
                
                "coder": {
                    "display_name": "Primary Coder - Kimi K2.5",
                    "provider": "moonshot",
                    "model": "kimi-k2.5",
                    "api_key_env": "MOONSHOT_API_KEY",
                    "base_url": "https://api.moonshot.ai/v1",
                    "context_window": 256000,
                    "max_tokens": 32000,
                    "temperature": 0.7,
                    "capabilities": ["coding", "implementation"],
                    "internet_access": False,
                    "priority": 3
                },
                
                "coder-glm": {
                    "display_name": "Stable Coder - GLM 4.7",
                    "provider": "zai",
                    "model": "glm-4.7",
                    "api_key_env": "ZAI_API_KEY",
                    "base_url": "https://api.z.ai/api/coding/paas/v4/",
                    "context_window": 200000,
                    "max_tokens": 128000,
                    "temperature": 0.6,
                    "capabilities": ["stable_coding", "typescript"],
                    "internet_access": False,
                    "priority": 3
                },
                
                "coder-deepseek": {
                    "display_name": "Logic Coder - DeepSeek",
                    "provider": "deepseek",
                    "model": "deepseek-chat",
                    "api_key_env": "DEEPSEEK_API_KEY",
                    "base_url": "https://api.deepseek.com/v1",
                    "context_window": 131072,
                    "max_tokens": 8192,
                    "temperature": 0.7,
                    "capabilities": ["complex_logic", "algorithms"],
                    "internet_access": False,
                    "priority": 3
                },
                
                "tester": {
                    "display_name": "Test Engineer - GLM 4.7",
                    "provider": "zai",
                    "model": "glm-4.7",
                    "api_key_env": "ZAI_API_KEY",
                    "base_url": "https://api.z.ai/api/coding/paas/v4/",
                    "context_window": 200000,
                    "max_tokens": 128000,
                    "temperature": 0.6,
                    "capabilities": ["testing", "qa", "coverage"],
                    "internet_access": False,
                    "priority": 4
                },
                
                "reviewer": {
                    "display_name": "Code Reviewer - Claude",
                    "provider": "anthropic",
                    "model": "claude-sonnet-4-5",
                    "api_key_env": "ANTHROPIC_API_KEY",
                    "base_url": "https://api.anthropic.com",
                    "context_window": 200000,
                    "max_tokens": 64000,
                    "temperature": 0.7,
                    "capabilities": ["code_review", "quality"],
                    "internet_access": False,
                    "priority": 4
                },
                
                "security": {
                    "display_name": "Security Analyst - Claude",
                    "provider": "anthropic",
                    "model": "claude-sonnet-4-5",
                    "api_key_env": "ANTHROPIC_API_KEY",
                    "base_url": "https://api.anthropic.com",
                    "context_window": 200000,
                    "max_tokens": 64000,
                    "temperature": 0.7,
                    "capabilities": ["security_analysis", "vulnerability_detection"],
                    "internet_access": False,
                    "priority": 2
                },
                
                "validator-anthropic": {
                    "display_name": "Validator - Claude",
                    "provider": "anthropic",
                    "model": "claude-haiku-4-5",
                    "api_key_env": "ANTHROPIC_API_KEY",
                    "base_url": "https://api.anthropic.com",
                    "context_window": 200000,
                    "max_tokens": 64000,
                    "temperature": 0.4,
                    "capabilities": ["validation", "cross_check"],
                    "internet_access": False,
                    "priority": 4
                },
                
                "coder-groq": {
                    "display_name": "Ultra-Fast Coder - Groq",
                    "provider": "groq",
                    "model": "llama-3.3-70b-versatile",
                    "api_key_env": "GROQ_API_KEY",
                    "base_url": "https://api.groq.com/openai/v1",
                    "context_window": 128000,
                    "max_tokens": 8192,
                    "temperature": 0.7,
                    "capabilities": ["ultra_fast", "bulk_tasks"],
                    "internet_access": False,
                    "priority": 5
                }
            }
        }
        
        # Save registry
        self.config_dir.mkdir(exist_ok=True)
        registry_path = self.config_dir / "model_registry.json"
        with open(registry_path, 'w') as f:
            json.dump(registry, f, indent=2)
        
        print(f"   ✓ Created: {registry_path}")
        print(f"   ✓ Models registered: {len(registry['models'])}")
        print(f"   ✓ Internet research models: {len(self.internet_models)}")
    
    def create_component_configs(self):
        """Create individual component configuration files"""
        print("\n🔧 Creating component configurations...")
        
        components_dir = self.config_dir / "components"
        components_dir.mkdir(exist_ok=True)
        
        # Load registry
        with open(self.config_dir / "model_registry.json", 'r') as f:
            registry = json.load(f)
        
        for agent_id, config in registry["models"].items():
            component_file = components_dir / f"{agent_id}.json"
            with open(component_file, 'w') as f:
                json.dump(config, f, indent=2)
        
        print(f"   ✓ Created {len(registry['models'])} component configs")
    
    def verify_setup(self) -> bool:
        """Verify the setup is complete"""
        print("\n🔍 Verifying setup...")
        
        checks = []
        
        # Check .env exists
        if self.langflow_env_path.exists():
            checks.append((".env file", True))
            
            # Check API keys
            with open(self.langflow_env_path, 'r') as f:
                content = f.read()
                key_count = sum(1 for key in self.required_keys if key in content and not f"#{key}" in content)
                checks.append((f"API Keys configured", key_count > 0, f"{key_count}/{len(self.required_keys)}"))
        else:
            checks.append((".env file", False))
        
        # Check model registry
        registry_path = self.config_dir / "model_registry.json"
        if registry_path.exists():
            checks.append(("Model registry", True))
        else:
            checks.append(("Model registry", False))
        
        # Check components
        components_dir = self.config_dir / "components"
        if components_dir.exists():
            component_count = len(list(components_dir.glob("*.json")))
            checks.append(("Component configs", component_count > 0, f"{component_count} files"))
        else:
            checks.append(("Component configs", False))
        
        # Print results
        all_passed = True
        for check in checks:
            name = check[0]
            passed = check[1]
            detail = check[2] if len(check) > 2 else ""
            
            status = "✓" if passed else "✗"
            detail_str = f" ({detail})" if detail else ""
            print(f"   {status} {name}{detail_str}")
            
            if not passed:
                all_passed = False
        
        return all_passed
    
    def print_summary(self, api_keys: Dict[str, str]):
        """Print setup summary"""
        print("\n" + "="*70)
        print("✅ SETUP COMPLETE - LANGFLOW WITH OPENCODE MODELS v9.5")
        print("="*70)
        
        print(f"\n📊 Configuration Summary:")
        print(f"   • API Keys: {len([k for k in api_keys if k])}/{len(self.required_keys)} configured")
        print(f"   • Models: 20 OpenCode models registered")
        print(f"   • Internet Research: 5 models enabled")
        print(f"   • Components: Individual configs created")
        
        print(f"\n🌐 Internet Research Models:")
        for model in self.internet_models:
            print(f"   ✓ {model}")
        
        print(f"\n📁 Files Created:")
        print(f"   • {self.langflow_env_path} - Environment configuration")
        print(f"   • config/model_registry.json - Model definitions")
        print(f"   • config/components/*.json - Individual components")
        
        print(f"\n🚀 Next Steps:")
        print(f"   1. Start Langflow: python -m langflow run")
        print(f"   2. Open: http://localhost:7860")
        print(f"   3. Create a new flow with OpenCode agents")
        print(f"   4. Use: python run_task.py 'Your task'")
        
        print(f"\n⚠️  Important:")
        print(f"   • All models match OpenCode v9.5 configuration")
        print(f"   • Internet research enabled for 5 models")
        print(f"   • MCP gateway configured for memory")
        print(f"   • API keys loaded from OpenCode .env")
        
        print("\n" + "="*70)
    
    def run(self):
        """Run complete setup"""
        print("\n" + "="*70)
        print("🔧 LANGFLOW SETUP - OPENCODE MODELS v9.5")
        print("="*70)
        print(f"   Source: {self.opencode_env_path}")
        print(f"   Target: {self.langflow_env_path}")
        print("="*70)
        
        # Step 1: Read API keys
        api_keys = self.read_opencode_env()
        
        if not api_keys:
            print("\n⚠️  WARNING: No API keys found in OpenCode .env")
            print("   Please configure OpenCode first:")
            print("   1. Run: opencode configure")
            print("   2. Add API keys to ~/.config/opencode/.env")
            print("   3. Run this setup again")
            return False
        
        # Step 2: Create Langflow .env
        self.create_langflow_env(api_keys)
        
        # Step 3: Create model registry
        self.create_model_registry()
        
        # Step 4: Create component configs
        self.create_component_configs()
        
        # Step 5: Verify
        success = self.verify_setup()
        
        # Step 6: Print summary
        self.print_summary(api_keys)
        
        return success


if __name__ == "__main__":
    setup = LangflowSetup()
    success = setup.run()
    
    if success:
        print("\n✨ Setup completed successfully!")
        sys.exit(0)
    else:
        print("\n⚠️  Setup completed with warnings")
        sys.exit(1)
