#!/usr/bin/env python3
"""
Validation Script for Hybrid Langflow + OpenCode System
Validates all components before deployment
"""

import os
import sys
import json
import subprocess
from pathlib import Path

class HybridSystemValidator:
    """Validates all components of the hybrid system"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.validation_results = {
            "passed": [],
            "failed": [],
            "warnings": []
        }
    
    def validate_file_structure(self):
        """Validate required files exist"""
        required_files = [
            "src/backend/base/langflow/components/hybrid/hybrid_agent.py",
            "docker/hybrid.Dockerfile",
            "scripts/start-hybrid.sh",
            "render-hybrid.yaml",
            "agent/workflows/hybrid_multiflow.json",
            "HYBRID_MULTIFLOW_DEPLOYMENT.md"
        ]
        
        for file_path in required_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                self.validation_results["passed"].append(f"File exists: {file_path}")
            else:
                self.validation_results["failed"].append(f"Missing file: {file_path}")
    
    def validate_dockerfile(self):
        """Validate Dockerfile syntax and content"""
        dockerfile_path = self.project_root / "docker" / "hybrid.Dockerfile"
        
        if not dockerfile_path.exists():
            self.validation_results["failed"].append("Dockerfile not found")
            return
        
        try:
            with open(dockerfile_path, 'r') as f:
                content = f.read()
            
            # Check for required sections
            required_sections = [
                "FROM langflowai/langflow:latest",
                "WORKDIR /app",
                "EXPOSE 10000",
                "HEALTHCHECK",
                "ENTRYPOINT"
            ]
            
            for section in required_sections:
                if section in content:
                    self.validation_results["passed"].append(f"Dockerfile contains: {section}")
                else:
                    self.validation_results["warnings"].append(f"Dockerfile missing: {section}")
                    
        except Exception as e:
            self.validation_results["failed"].append(f"Dockerfile validation error: {str(e)}")
    
    def validate_startup_script(self):
        """Validate startup script"""
        script_path = self.project_root / "scripts" / "start-hybrid.sh"
        
        if not script_path.exists():
            self.validation_results["failed"].append("Startup script not found")
            return
        
        try:
            with open(script_path, 'r') as f:
                content = f.read()
            
            # Check for required functionality
            required_patterns = [
                "#!/bin/bash",
                "Starting Langflow server",
                "Starting OpenCode MCP servers",
                "LANGFLOW_PID=",
                "trap 'echo"
            ]
            
            for pattern in required_patterns:
                if pattern in content:
                    self.validation_results["passed"].append(f"Startup script contains: {pattern}")
                else:
                    self.validation_results["warnings"].append(f"Startup script missing: {pattern}")
                    
            # Check executable permissions
            if os.access(script_path, os.X_OK):
                self.validation_results["passed"].append("Startup script is executable")
            else:
                self.validation_results["warnings"].append("Startup script is not executable")
                
        except Exception as e:
            self.validation_results["failed"].append(f"Startup script validation error: {str(e)}")
    
    def validate_render_config(self):
        """Validate Render deployment configuration"""
        config_path = self.project_root / "render-hybrid.yaml"
        
        if not config_path.exists():
            self.validation_results["failed"].append("Render config not found")
            return
        
        try:
            with open(config_path, 'r') as f:
                content = f.read()
            
            # Check for required sections
            required_sections = [
                "services:",
                "type: web",
                "name: langflow-hybrid",
                "runtime: docker",
                "dockerfilePath: ./docker/hybrid.Dockerfile",
                "healthCheckPath: /health_check"
            ]
            
            for section in required_sections:
                if section in content:
                    self.validation_results["passed"].append(f"Render config contains: {section}")
                else:
                    self.validation_results["warnings"].append(f"Render config missing: {section}")
                    
        except Exception as e:
            self.validation_results["failed"].append(f"Render config validation error: {str(e)}")
    
    def validate_hybrid_agent_component(self):
        """Validate Hybrid Agent component"""
        agent_path = self.project_root / "src" / "backend" / "base" / "langflow" / "components" / "hybrid" / "hybrid_agent.py"
        
        if not agent_path.exists():
            self.validation_results["failed"].append("Hybrid Agent component not found")
            return
        
        try:
            with open(agent_path, 'r') as f:
                content = f.read()
            
            # Check for required classes and methods
            required_elements = [
                "class HybridAgentComponent",
                "class OpenCodeParallelBridge",
                "def execute_hybrid_flow",
                "def dispatch_parallel",
                "display_name: str = \"Hybrid Agent\""
            ]
            
            for element in required_elements:
                if element in content:
                    self.validation_results["passed"].append(f"Hybrid Agent contains: {element}")
                else:
                    self.validation_results["warnings"].append(f"Hybrid Agent missing: {element}")
                    
        except Exception as e:
            self.validation_results["failed"].append(f"Hybrid Agent validation error: {str(e)}")
    
    def validate_workflow_json(self):
        """Validate hybrid workflow JSON"""
        workflow_path = self.project_root / "agent" / "workflows" / "hybrid_multiflow.json"
        
        if not workflow_path.exists():
            self.validation_results["failed"].append("Workflow JSON not found")
            return
        
        try:
            with open(workflow_path, 'r') as f:
                data = json.load(f)
            
            # Validate JSON structure
            required_keys = ["name", "description", "components", "edges", "execution_config"]
            
            for key in required_keys:
                if key in data:
                    self.validation_results["passed"].append(f"Workflow contains key: {key}")
                else:
                    self.validation_results["failed"].append(f"Workflow missing key: {key}")
            
            # Validate components
            if "components" in data and isinstance(data["components"], list):
                self.validation_results["passed"].append("Workflow has components array")
                if len(data["components"]) > 0:
                    self.validation_results["passed"].append(f"Workflow has {len(data['components'])} components")
                else:
                    self.validation_results["warnings"].append("Workflow has no components")
            
            # Validate edges
            if "edges" in data and isinstance(data["edges"], list):
                self.validation_results["passed"].append("Workflow has edges array")
                if len(data["edges"]) > 0:
                    self.validation_results["passed"].append(f"Workflow has {len(data['edges'])} edges (agent connections)")
                else:
                    self.validation_results["warnings"].append("Workflow has no edges")
                    
        except json.JSONDecodeError as e:
            self.validation_results["failed"].append(f"Invalid JSON in workflow: {str(e)}")
        except Exception as e:
            self.validation_results["failed"].append(f"Workflow validation error: {str(e)}")
    
    def validate_deployment_guide(self):
        """Validate deployment guide"""
        guide_path = self.project_root / "HYBRID_MULTIFLOW_DEPLOYMENT.md"
        
        if not guide_path.exists():
            self.validation_results["failed"].append("Deployment guide not found")
            return
        
        try:
            with open(guide_path, 'r') as f:
                content = f.read()
            
            # Check for required sections
            required_sections = [
                "## Overview",
                "## Architecture Components",
                "## Deployment Options",
                "## System Features",
                "## Usage Examples",
                "## Configuration",
                "## Monitoring & Debugging",
                "## Performance Optimization",
                "## Troubleshooting"
            ]
            
            for section in required_sections:
                if section in content:
                    self.validation_results["passed"].append(f"Deployment guide contains: {section}")
                else:
                    self.validation_results["warnings"].append(f"Deployment guide missing: {section}")
                    
        except Exception as e:
            self.validation_results["failed"].append(f"Deployment guide validation error: {str(e)}")
    
    def validate_improvement_plans(self):
        """Validate 1000 improvement plan documents"""
        plan_files = [
            "1000_IMPROVEMENT_PLAN_PART1.md",
            "1000_IMPROVEMENT_PLAN_PART2.md",
            "1000_IMPROVEMENT_PLAN_PART3.md"
        ]
        
        for plan_file in plan_files:
            plan_path = self.project_root / plan_file
            
            if plan_path.exists():
                self.validation_results["passed"].append(f"Improvement plan exists: {plan_file}")
                
                try:
                    with open(plan_path, 'r') as f:
                        content = f.read()
                    
                    if len(content) > 1000:  # Reasonable minimum size
                        self.validation_results["passed"].append(f"Improvement plan has substantial content: {plan_file}")
                    else:
                        self.validation_results["warnings"].append(f"Improvement plan may be too short: {plan_file}")
                        
                except Exception as e:
                    self.validation_results["failed"].append(f"Improvement plan read error: {plan_file} - {str(e)}")
            else:
                self.validation_results["warnings"].append(f"Improvement plan missing: {plan_file}")
    
    def run_all_validations(self):
        """Run all validation checks"""
        print("=" * 60)
        print("VALIDATING HYBRID LANGFLOW + OPENCODE SYSTEM")
        print("=" * 60)
        
        validations = [
            ("File Structure", self.validate_file_structure),
            ("Dockerfile", self.validate_dockerfile),
            ("Startup Script", self.validate_startup_script),
            ("Render Config", self.validate_render_config),
            ("Hybrid Agent Component", self.validate_hybrid_agent_component),
            ("Workflow JSON", self.validate_workflow_json),
            ("Deployment Guide", self.validate_deployment_guide),
            ("Improvement Plans", self.validate_improvement_plans)
        ]
        
        for name, validation_func in validations:
            print(f"\n🔍 Validating: {name}")
            validation_func()
        
        # Print summary
        print("\n" + "=" * 60)
        print("VALIDATION SUMMARY")
        print("=" * 60)
        
        print(f"\n✅ PASSED: {len(self.validation_results['passed'])}")
        for item in self.validation_results['passed'][:10]:  # Show first 10
            print(f"  ✓ {item}")
        if len(self.validation_results['passed']) > 10:
            print(f"  ... and {len(self.validation_results['passed']) - 10} more")
        
        print(f"\n⚠️  WARNINGS: {len(self.validation_results['warnings'])}")
        for item in self.validation_results['warnings']:
            print(f"  ⚠ {item}")
        
        print(f"\n❌ FAILED: {len(self.validation_results['failed'])}")
        for item in self.validation_results['failed']:
            print(f"  ✗ {item}")
        
        # Overall status
        print("\n" + "=" * 60)
        if len(self.validation_results['failed']) == 0:
            if len(self.validation_results['warnings']) == 0:
                print("🎉 SYSTEM VALIDATION: COMPLETELY SUCCESSFUL")
                print("All components are ready for deployment!")
            else:
                print("✅ SYSTEM VALIDATION: SUCCESSFUL WITH WARNINGS")
                print("System is deployable, but review warnings.")
        else:
            print("❌ SYSTEM VALIDATION: FAILED")
            print("Fix the failed items before deployment.")
        
        print("=" * 60)
        
        return self.validation_results

def main():
    """Main validation entry point"""
    validator = HybridSystemValidator()
    results = validator.run_all_validations()
    
    # Save validation report
    report_path = validator.project_root / "VALIDATION_REPORT.json"
    with open(report_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📄 Validation report saved to: {report_path}")
    
    # Exit code based on validation results
    if len(results['failed']) > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()