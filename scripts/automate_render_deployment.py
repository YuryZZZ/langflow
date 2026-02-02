#!/usr/bin/env python3
"""
Automate Render.com Deployment for Langflow with MCP Integration
This script provides automation for deploying to Render.com
"""

import json
import os
import sys
import subprocess
from pathlib import Path
import webbrowser
import time

class RenderDeploymentAutomator:
    def __init__(self):
        self.config_dir = Path("deploy/config")
        self.config_file = self.config_dir / "render_env_config.json"
        self.deployment_guide = Path("RENDER_DEPLOYMENT_GUIDE.md")
        
    def check_prerequisites(self):
        """Check if all prerequisites are met"""
        print("🔍 Checking prerequisites...")
        
        checks = []
        
        # Check if configuration file exists
        if self.config_file.exists():
            checks.append(("✅ Configuration file", self.config_file))
        else:
            checks.append(("❌ Configuration file missing", self.config_file))
            
        # Check if deployment guide exists
        if self.deployment_guide.exists():
            checks.append(("✅ Deployment guide", self.deployment_guide))
        else:
            checks.append(("❌ Deployment guide missing", self.deployment_guide))
            
        # Check if render_mcp.yaml exists
        render_config = Path("render_mcp.yaml")
        if render_config.exists():
            checks.append(("✅ Render configuration", render_config))
        else:
            checks.append(("❌ Render configuration missing", render_config))
            
        # Check if Dockerfile exists
        dockerfile = Path("docker/build_and_push_mcp.Dockerfile")
        if dockerfile.exists():
            checks.append(("✅ Dockerfile", dockerfile))
        else:
            checks.append(("❌ Dockerfile missing", dockerfile))
            
        # Check git status
        try:
            result = subprocess.run(["git", "status", "--porcelain"], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                if result.stdout.strip():
                    checks.append(("⚠️  Uncommitted changes", "Consider committing before deployment"))
                else:
                    checks.append(("✅ Git repository clean", "Ready for deployment"))
            else:
                checks.append(("❌ Git not available", "Install git"))
        except:
            checks.append(("❌ Git check failed", "Git may not be installed"))
            
        # Display check results
        print("\n" + "="*60)
        print("PREREQUISITE CHECKS")
        print("="*60)
        for status, message in checks:
            print(f"{status}: {message}")
        print("="*60)
        
        # Count failures
        failures = sum(1 for status, _ in checks if status.startswith("❌"))
        warnings = sum(1 for status, _ in checks if status.startswith("⚠️"))
        
        if failures > 0:
            print(f"\n❌ Found {failures} critical issues. Please fix before deployment.")
            return False
        elif warnings > 0:
            print(f"\n⚠️  Found {warnings} warnings. Review before deployment.")
            return True
        else:
            print("\n✅ All prerequisites met!")
            return True
    
    def load_configuration(self):
        """Load the Render.com configuration"""
        print("\n📋 Loading configuration...")
        
        if not self.config_file.exists():
            print(f"❌ Configuration file not found: {self.config_file}")
            return None
            
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            print(f"✅ Loaded configuration with {len(config)} environment variables")
            return config
        except Exception as e:
            print(f"❌ Failed to load configuration: {e}")
            return None
    
    def generate_deployment_commands(self, config):
        """Generate deployment commands and instructions"""
        print("\n🚀 Generating deployment instructions...")
        
        # Count required API keys
        required_keys = []
        optional_keys = []
        
        for key, value in config.items():
            if isinstance(value, dict) and value.get('required', False):
                required_keys.append(key)
            elif 'API' in key or 'KEY' in key or 'TOKEN' in key:
                optional_keys.append(key)
        
        # Create deployment instructions
        instructions = {
            "summary": {
                "total_variables": len(config),
                "required_api_keys": len(required_keys),
                "optional_api_keys": len(optional_keys),
                "postgres_required": any(k.startswith('POSTGRES_') for k in config)
            },
            "steps": [
                {
                    "step": 1,
                    "title": "Prepare Repository",
                    "actions": [
                        "Ensure your repository is forked on GitHub",
                        "Push the mcp-integration-clean branch to your fork",
                        "Verify render_mcp.yaml is in the root directory"
                    ]
                },
                {
                    "step": 2,
                    "title": "Create Render.com Web Service",
                    "actions": [
                        "Go to https://render.com",
                        "Click 'New +' → 'Web Service'",
                        "Connect your GitHub repository",
                        "Select branch: mcp-integration-clean",
                        "Configure as shown in RENDER_DEPLOYMENT_GUIDE.md"
                    ]
                },
                {
                    "step": 3,
                    "title": "Set Environment Variables",
                    "actions": [
                        f"Add {len(config)} environment variables",
                        "Use the values from deploy/config/render_env_config.json",
                        f"Fill in {len(required_keys)} required API keys",
                        "Set sync: false for all API keys"
                    ],
                    "required_keys": required_keys,
                    "optional_keys": optional_keys
                },
                {
                    "step": 4,
                    "title": "Create PostgreSQL Database",
                    "actions": [
                        "Create new PostgreSQL database named 'opencode_taskbus'",
                        "Link it to your web service",
                        "Render will auto-set POSTGRES_* variables"
                    ]
                },
                {
                    "step": 5,
                    "title": "Configure Persistent Disk",
                    "actions": [
                        "Add persistent disk named 'langflow-mcp-data'",
                        "Mount path: /app/data",
                        "Size: 1GB minimum"
                    ]
                },
                {
                    "step": 6,
                    "title": "Deploy",
                    "actions": [
                        "Click 'Create Web Service'",
                        "Monitor build logs",
                        "Wait for deployment to complete (5-10 minutes)"
                    ]
                }
            ],
            "post_deployment": [
                "Test health endpoint: https://[your-service].onrender.com/health",
                "Access Langflow UI: https://[your-service].onrender.com",
                "Test MCP integration using test scripts",
                "Configure custom domain if needed"
            ]
        }
        
        return instructions
    
    def open_deployment_guide(self):
        """Open the deployment guide in browser"""
        print("\n📖 Opening deployment guide...")
        
        if self.deployment_guide.exists():
            try:
                # Try to open in default browser
                webbrowser.open(f"file://{self.deployment_guide.absolute()}")
                print("✅ Deployment guide opened in browser")
            except:
                print(f"📄 Deployment guide location: {self.deployment_guide.absolute()}")
        else:
            print("❌ Deployment guide not found")
    
    def generate_quick_setup_script(self):
        """Generate a quick setup script for manual execution"""
        print("\n⚡ Generating quick setup script...")
        
        script_content = """#!/bin/bash
# Quick Setup Script for Render.com Deployment
# Run this script to get deployment commands

echo "================================================"
echo "Render.com Quick Deployment Setup"
echo "================================================"
echo ""
echo "1. FORK REPOSITORY:"
echo "   - Go to https://github.com/langflow-ai/langflow"
echo "   - Click 'Fork' in top-right corner"
echo "   - Select your account"
echo ""
echo "2. PUSH BRANCH TO FORK:"
echo "   git remote add fork https://github.com/YOUR_USERNAME/langflow.git"
echo "   git push fork mcp-integration-clean"
echo ""
echo "3. CREATE RENDER SERVICE:"
echo "   Open: https://render.com/new/web"
echo "   Connect your forked repository"
echo "   Select branch: mcp-integration-clean"
echo ""
echo "4. CONFIGURE SERVICE:"
echo "   Name: langflow-mcp"
echo "   Environment: Docker"
echo "   Dockerfile Path: ./docker/build_and_push_mcp.Dockerfile"
echo "   Plan: Standard (recommended)"
echo ""
echo "5. SET ENVIRONMENT VARIABLES:"
echo "   Use values from: deploy/config/render_env_config.json"
echo "   Required API keys:"
echo "     - OPENAI_API_KEY"
echo "     - ANTHROPIC_API_KEY"
echo "     - GOOGLE_API_KEY"
echo "     - DEEPSEEK_API_KEY"
echo "     - ZAI_API_KEY"
echo "     - GROQ_API_KEY"
echo ""
echo "6. CREATE DATABASE:"
echo "   Create PostgreSQL database named 'opencode_taskbus'"
echo "   Link to web service"
echo ""
echo "7. ADD PERSISTENT DISK:"
echo "   Name: langflow-mcp-data"
echo "   Mount Path: /app/data"
echo "   Size: 1GB"
echo ""
echo "8. DEPLOY:"
echo "   Click 'Create Web Service'"
echo "   Monitor build logs"
echo ""
echo "9. TEST DEPLOYMENT:"
echo "   Health check: https://langflow-mcp.onrender.com/health"
echo "   UI: https://langflow-mcp.onrender.com"
echo ""
echo "For detailed instructions, see RENDER_DEPLOYMENT_GUIDE.md"
echo "================================================"
"""
        
        script_file = self.config_dir / "quick_deploy.sh"
        with open(script_file, 'w') as f:
            f.write(script_content)
            
        # Make executable
        script_file.chmod(0o755)
        
        print(f"✅ Quick setup script created: {script_file}")
        return script_file
    
    def run(self):
        """Main execution method"""
        print("="*60)
        print("Render.com Deployment Automator")
        print("="*60)
        
        # Check prerequisites
        if not self.check_prerequisites():
            print("\n❌ Prerequisites not met. Please fix issues and try again.")
            return False
        
        # Load configuration
        config = self.load_configuration()
        if not config:
            return False
        
        # Generate instructions
        instructions = self.generate_deployment_commands(config)
        
        # Display summary
        print("\n" + "="*60)
        print("DEPLOYMENT SUMMARY")
        print("="*60)
        print(f"Total Environment Variables: {instructions['summary']['total_variables']}")
        print(f"Required API Keys: {instructions['summary']['required_api_keys']}")
        print(f"Optional API Keys: {instructions['summary']['optional_api_keys']}")
        print(f"PostgreSQL Required: {'Yes' if instructions['summary']['postgres_required'] else 'No'}")
        print("="*60)
        
        # Display steps
        print("\n📋 DEPLOYMENT STEPS:")
        for step_info in instructions['steps']:
            print(f"\nStep {step_info['step']}: {step_info['title']}")
            for action in step_info['actions']:
                print(f"  • {action}")
            
            if 'required_keys' in step_info and step_info['required_keys']:
                print(f"\n  Required API Keys ({len(step_info['required_keys'])}):")
                for key in step_info['required_keys']:
                    print(f"    - {key}")
            
            if 'optional_keys' in step_info and step_info['optional_keys']:
                print(f"\n  Optional API Keys ({len(step_info['optional_keys'])}):")
                for key in step_info['optional_keys']:
                    print(f"    - {key}")
        
        # Post-deployment
        print("\n🎯 POST-DEPLOYMENT:")
        for action in instructions['post_deployment']:
            print(f"  • {action}")
        
        # Generate quick setup script
        script_file = self.generate_quick_setup_script()
        
        # Open deployment guide
        self.open_deployment_guide()
        
        print("\n" + "="*60)
        print("NEXT ACTIONS")
        print("="*60)
        print("1. Review the deployment guide: RENDER_DEPLOYMENT_GUIDE.md")
        print("2. Run the quick setup script:")
        print(f"   bash {script_file}")
        print("3. Follow the step-by-step instructions above")
        print("4. Deploy to Render.com web interface")
        print("="*60)
        print("\n✅ Deployment automation complete!")
        print("   Manual deployment required through Render.com web interface")
        
        return True

def main():
    """Main function"""
    automator = RenderDeploymentAutomator()
    
    try:
        success = automator.run()
        if success:
            sys.exit(0)
        else:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Deployment automation cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Error during deployment automation: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()