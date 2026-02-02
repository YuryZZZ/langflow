#!/usr/bin/env python3
"""
Deployment verification script for Hybrid Langflow + OpenCode system.
This script verifies that all components are ready for deployment.
"""

import json
import os
import sys
from pathlib import Path

def check_file_exists(file_path, description):
    """Check if a file exists and return status."""
    if os.path.exists(file_path):
        print(f"✅ {description}: {file_path}")
        return True
    else:
        print(f"❌ {description}: {file_path} - NOT FOUND")
        return False

def check_directory_exists(dir_path, description):
    """Check if a directory exists and return status."""
    if os.path.isdir(dir_path):
        print(f"✅ {description}: {dir_path}")
        return True
    else:
        print(f"❌ {description}: {dir_path} - NOT FOUND")
        return False

def validate_hybrid_flow():
    """Validate the hybrid flow JSON file."""
    flow_path = "agent/workflows/hybrid_multiflow.json"
    if not os.path.exists(flow_path):
        print(f"❌ Hybrid flow not found: {flow_path}")
        return False
    
    try:
        with open(flow_path, 'r') as f:
            flow_data = json.load(f)
        
        # Check for required components
        if 'nodes' not in flow_data or 'edges' not in flow_data:
            print("❌ Hybrid flow missing nodes or edges")
            return False
        
        nodes = flow_data.get('nodes', [])
        edges = flow_data.get('edges', [])
        
        print(f"✅ Hybrid flow validated: {len(nodes)} nodes, {len(edges)} connections")
        
        # Check for HybridAgentComponent
        hybrid_components = [n for n in nodes if n.get('data', {}).get('node', {}).get('display_name') == 'HybridAgentComponent']
        if hybrid_components:
            print(f"✅ Found {len(hybrid_components)} HybridAgentComponent(s)")
        else:
            print("⚠️  No HybridAgentComponent found in flow (may be using different component)")
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in hybrid flow: {e}")
        return False
    except Exception as e:
        print(f"❌ Error validating hybrid flow: {e}")
        return False

def validate_deployment_configs():
    """Validate deployment configuration files."""
    configs = [
        ("render-hybrid.yaml", "Render hybrid deployment config"),
        ("render_mcp.yaml", "Render MCP deployment config"),
        ("docker/hybrid.Dockerfile", "Hybrid Dockerfile"),
        ("scripts/start-hybrid.sh", "Startup script"),
    ]
    
    all_valid = True
    for file_path, description in configs:
        if not check_file_exists(file_path, description):
            all_valid = False
    
    return all_valid

def validate_system_components():
    """Validate system components are in place."""
    components = [
        ("src/backend/base/langflow/components/hybrid/hybrid_agent.py", "Hybrid Agent component"),
        ("scripts/validate_hybrid_system.py", "System validation script"),
        ("scripts/validate_flow_connections.py", "Flow connection validation"),
    ]
    
    all_valid = True
    for file_path, description in components:
        if not check_file_exists(file_path, description):
            all_valid = False
    
    return all_valid

def create_deployment_summary():
    """Create a deployment summary report."""
    summary = {
        "system_ready": False,
        "components_validated": False,
        "flow_validated": False,
        "configs_validated": False,
        "deployment_methods": [],
        "next_steps": []
    }
    
    print("\n" + "="*60)
    print("DEPLOYMENT VERIFICATION SUMMARY")
    print("="*60)
    
    # Check system components
    print("\n1. System Components:")
    summary["components_validated"] = validate_system_components()
    
    # Check hybrid flow
    print("\n2. Hybrid Flow Validation:")
    summary["flow_validated"] = validate_hybrid_flow()
    
    # Check deployment configs
    print("\n3. Deployment Configurations:")
    summary["configs_validated"] = validate_deployment_configs()
    
    # Check available deployment methods
    print("\n4. Available Deployment Methods:")
    
    # Method 1: Render CLI
    if check_file_exists("render-hybrid.yaml", "Render hybrid config"):
        summary["deployment_methods"].append({
            "method": "Render CLI",
            "command": "render deploy -f render-hybrid.yaml",
            "requirements": "Render CLI installed and authenticated"
        })
        print("✅ Render CLI deployment available")
    
    # Method 2: Manual Docker
    if check_file_exists("docker/hybrid.Dockerfile", "Dockerfile"):
        summary["deployment_methods"].append({
            "method": "Manual Docker",
            "command": "docker build -f docker/hybrid.Dockerfile -t langflow-hybrid:latest . && docker run -d -p 10000:10000 -p 8080:8080 --name langflow-hybrid langflow-hybrid:latest",
            "requirements": "Docker installed"
        })
        print("✅ Manual Docker deployment available")
    
    # Method 3: Git push (if in git repo)
    if os.path.exists(".git"):
        summary["deployment_methods"].append({
            "method": "Git Push",
            "command": "git push",
            "requirements": "Git repository connected to Render"
        })
        print("✅ Git push deployment available")
    
    # Determine overall readiness
    summary["system_ready"] = all([
        summary["components_validated"],
        summary["flow_validated"],
        summary["configs_validated"],
        len(summary["deployment_methods"]) > 0
    ])
    
    # Create next steps
    if summary["system_ready"]:
        summary["next_steps"] = [
            "Choose a deployment method from the options above",
            "Run the deployment command",
            "Access Langflow UI at http://localhost:10000 (or your Render URL)",
            "Open the hybrid flow to see graphical agent connections",
            "Test parallel execution between Langflow and OpenCode"
        ]
    else:
        summary["next_steps"] = [
            "Fix the validation errors shown above",
            "Ensure all required files are present",
            "Run validation scripts to identify issues",
            "Re-run this verification script"
        ]
    
    # Print summary
    print("\n" + "="*60)
    print("VERIFICATION RESULT:")
    print("="*60)
    
    if summary["system_ready"]:
        print("✅ SYSTEM READY FOR DEPLOYMENT!")
        print(f"\nAvailable deployment methods: {len(summary['deployment_methods'])}")
        for i, method in enumerate(summary["deployment_methods"], 1):
            print(f"\n{i}. {method['method']}:")
            print(f"   Command: {method['command']}")
            print(f"   Requirements: {method['requirements']}")
    else:
        print("❌ SYSTEM NOT READY FOR DEPLOYMENT")
        print("\nIssues found. Please fix the validation errors above.")
    
    print("\n" + "="*60)
    print("NEXT STEPS:")
    print("="*60)
    for i, step in enumerate(summary["next_steps"], 1):
        print(f"{i}. {step}")
    
    # Save summary to file
    with open("DEPLOYMENT_VERIFICATION_REPORT.json", "w") as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n📄 Full report saved to: DEPLOYMENT_VERIFICATION_REPORT.json")
    
    return summary

def main():
    """Main verification function."""
    print("🔍 Verifying Hybrid Langflow + OpenCode Deployment Readiness")
    print("="*60)
    
    summary = create_deployment_summary()
    
    # Exit with appropriate code
    if summary["system_ready"]:
        print("\n🎉 Verification complete! System is ready for deployment.")
        return 0
    else:
        print("\n⚠️  Verification failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())