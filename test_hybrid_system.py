#!/usr/bin/env python3
"""
Test script for Hybrid Langflow + OpenCode system.
Tests the hybrid agent component and flow integration.
"""

import json
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_hybrid_agent_component():
    """Test the hybrid agent component."""
    print("🔧 Testing Hybrid Agent Component...")
    
    try:
        # Import the component
        from src.backend.base.langflow.components.hybrid.hybrid_agent import HybridAgentComponent
        
        # Create instance
        agent = HybridAgentComponent()
        
        # Test basic execution
        test_tasks = [
            "Analyze user requirements",
            "Design system architecture", 
            "Implement core functionality",
            "Write unit tests",
            "Perform code review"
        ]
        
        # Set component properties
        agent.task_description = "Test hybrid multiflow execution"
        agent.subtasks = json.dumps(test_tasks)
        agent.enable_validation = True
        agent.max_parallel_workers = 4
        
        # Execute
        results = agent.execute_hybrid_flow()
        
        print(f"✅ Hybrid agent component test passed!")
        print(f"   Status: {results.get('status', 'unknown')}")
        print(f"   Tasks dispatched: {results.get('subtasks_count', 0)}")
        print(f"   Execution ID: {results.get('execution_id', 'unknown')}")
        
        # Check execution history
        history = agent.get_execution_history()
        print(f"   Execution history entries: {len(history)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Hybrid agent component test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_hybrid_flow_file():
    """Test the hybrid flow JSON file."""
    print("\n📄 Testing Hybrid Flow File...")
    
    flow_path = "agent/workflows/hybrid_multiflow.json"
    
    try:
        with open(flow_path, 'r') as f:
            flow_data = json.load(f)
        
        # Validate structure
        required_keys = ['name', 'description', 'components', 'edges', 'execution_config']
        for key in required_keys:
            if key not in flow_data:
                print(f"❌ Missing required key: {key}")
                return False
        
        components = flow_data.get('components', [])
        edges = flow_data.get('edges', [])
        
        print(f"✅ Hybrid flow file validated!")
        print(f"   Name: {flow_data.get('name')}")
        print(f"   Components: {len(components)}")
        print(f"   Connections: {len(edges)}")
        print(f"   Parallel execution: {flow_data.get('execution_config', {}).get('parallel_execution', False)}")
        
        # Check for hybrid agent component
        hybrid_components = [c for c in components if c.get('type') == 'HybridAgent']
        if hybrid_components:
            print(f"   Found {len(hybrid_components)} HybridAgent component(s)")
        else:
            print("⚠️  No HybridAgent components found (check component types)")
        
        return True
        
    except Exception as e:
        print(f"❌ Hybrid flow file test failed: {e}")
        return False

def test_system_integration():
    """Test system integration points."""
    print("\n🔗 Testing System Integration...")
    
    integration_points = [
        ("src/backend/base/langflow/components/hybrid/hybrid_agent.py", "Hybrid Agent Component"),
        ("docker/hybrid.Dockerfile", "Hybrid Dockerfile"),
        ("scripts/start-hybrid.sh", "Startup Script"),
        ("render-hybrid.yaml", "Render Deployment Config"),
        ("scripts/validate_hybrid_system.py", "Validation Script"),
    ]
    
    all_valid = True
    for file_path, description in integration_points:
        if os.path.exists(file_path):
            print(f"✅ {description}: Found")
        else:
            print(f"❌ {description}: Missing")
            all_valid = False
    
    return all_valid

def create_test_report():
    """Create comprehensive test report."""
    print("\n" + "="*60)
    print("HYBRID SYSTEM TEST REPORT")
    print("="*60)
    
    tests = [
        ("Hybrid Agent Component", test_hybrid_agent_component()),
        ("Hybrid Flow File", test_hybrid_flow_file()),
        ("System Integration", test_system_integration()),
    ]
    
    print("\n" + "="*60)
    print("TEST RESULTS SUMMARY")
    print("="*60)
    
    passed = 0
    total = len(tests)
    
    for test_name, result in tests:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n📊 Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    # Create report file
    report = {
        "test_summary": {
            "total_tests": total,
            "passed": passed,
            "failed": total - passed,
            "success_rate": passed/total*100 if total > 0 else 0
        },
        "tests": [
            {
                "name": test_name,
                "passed": result,
                "description": "Hybrid system component validation"
            }
            for test_name, result in tests
        ],
        "system_status": "READY" if passed == total else "NEEDS_ATTENTION",
        "recommendations": [
            "Deploy to Render using render-hybrid.yaml",
            "Access Langflow UI and load hybrid_multiflow.json",
            "Test parallel execution with Hybrid Agent component",
            "Monitor execution via TaskBus interface"
        ] if passed == total else [
            "Fix the failing tests above",
            "Ensure all required files are present",
            "Run validation scripts to identify issues"
        ]
    }
    
    with open("HYBRID_SYSTEM_TEST_REPORT.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Full test report saved to: HYBRID_SYSTEM_TEST_REPORT.json")
    
    return passed == total

def main():
    """Main test function."""
    print("🧪 Testing Hybrid Langflow + OpenCode System")
    print("="*60)
    
    success = create_test_report()
    
    if success:
        print("\n🎉 ALL TESTS PASSED! Hybrid system is ready.")
        print("\nNEXT STEPS:")
        print("1. Deploy to Render: render deploy -f render-hybrid.yaml")
        print("2. Or run locally: docker build -f docker/hybrid.Dockerfile -t langflow-hybrid:latest .")
        print("3. Access Langflow UI at http://localhost:10000")
        print("4. Load hybrid_multiflow.json workflow")
        print("5. Test parallel execution with Hybrid Agent component")
        return 0
    else:
        print("\n⚠️  SOME TESTS FAILED. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())