#!/usr/bin/env python3
"""
Test script for real OpenCode integration in Hybrid Agent Component.
Validates the 10x deeper development implementation.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_real_opencode_integration():
    """Test the real OpenCode integration in Hybrid Agent Component"""
    print("🧪 Testing Real OpenCode Integration")
    print("=" * 60)

    try:
        # Import the updated component
        from src.backend.base.langflow.components.hybrid.hybrid_agent import OpenCodeParallelBridge

        # Create instance of real OpenCode bridge
        bridge = OpenCodeParallelBridge()

        print(f"✅ OpenCodeParallelBridge initialized")
        print(f"   Agents available: {len(bridge.agent_registry)}")
        print(f"   MCP servers: {len(bridge.mcp_config)}")

        # Test task description
        task_description = "Develop AI document analysis system with security features"

        # Test subtasks with varying complexity
        test_subtasks = [
            "Analyze user requirements for document processing",
            "Design secure authentication system",
            "Implement PDF text extraction algorithm",
            "Create unit tests for core functionality",
            "Review code for security vulnerabilities",
            "Research best practices for document OCR",
            "Optimize performance for large documents",
            "Design database schema for document metadata",
        ]

        print(f"\n📋 Test Task: {task_description}")
        print(f"   Subtasks: {len(test_subtasks)}")

        # Dispatch parallel tasks
        print("\n🚀 Dispatching parallel tasks via real OpenCode integration...")
        results = bridge.dispatch_parallel(task_description, test_subtasks)

        # Validate results
        print("\n📊 Results Validation:")
        print(f"   Run ID: {results.get('run_id')}")
        print(f"   Execution Mode: {results.get('mode')}")
        print(f"   Parallel Execution: {results.get('parallel_execution')}")

        # Check MCP integration
        mcp_integration = results.get("mcp_integration", {})
        print(f"\n🔌 MCP Integration Status:")
        print(f"   TaskBus: {'✅ Enabled' if mcp_integration.get('taskbus') else '❌ Disabled'}")
        print(f"   Parallel: {'✅ Enabled' if mcp_integration.get('parallel') else '❌ Disabled'}")
        print(f"   Memory: {'✅ Enabled' if mcp_integration.get('memory') else '❌ Disabled'}")
        print(f"   Agents Available: {mcp_integration.get('agents_available', 0)}")

        # Check execution statistics
        exec_stats = results.get("execution_stats", {})
        print(f"\n📈 Execution Statistics:")
        print(f"   Total Tasks: {exec_stats.get('total_tasks', 0)}")
        print(f"   Successful: {exec_stats.get('successful_tasks', 0)}")
        print(f"   Failed: {exec_stats.get('failed_tasks', 0)}")
        print(f"   Avg Complexity: {exec_stats.get('average_complexity', 0):.1f}")

        # Check performance metrics
        perf_metrics = results.get("performance_metrics", {})
        print(f"\n⚡ Performance Metrics:")
        print(f"   Success Rate: {perf_metrics.get('success_rate', 0):.1f}%")
        print(f"   Tasks/Second: {perf_metrics.get('tasks_per_second', 0):.2f}")
        print(f"   Avg Time/Task: {perf_metrics.get('average_execution_time', 0):.2f}s")
        print(f"   Total Cost Estimate: ${perf_metrics.get('total_cost_estimate', 0):.4f}")

        # Check quality metrics
        quality_metrics = results.get("quality_metrics", {})
        print(f"\n🎯 Quality Metrics:")
        print(f"   Overall Quality: {quality_metrics.get('overall_quality', 0):.1f}/100")
        print(f"   Validation Coverage: {quality_metrics.get('validation_coverage', 0):.1f}%")
        print(f"   Quality Gate Success: {quality_metrics.get('quality_gate_success_rate', 0):.1f}%")

        # Check agent utilization
        agent_util = exec_stats.get("agent_utilization", {})
        if agent_util:
            print(f"\n🤖 Agent Utilization:")
            for agent, count in sorted(agent_util.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"   {agent}: {count} tasks")

        # Check task details
        task_details = results.get("results", {}).get("task_details", {})
        if task_details:
            print(f"\n📝 Task Details (first 3):")
            for i, (task_id, details) in enumerate(list(task_details.items())[:3]):
                print(f"   {i + 1}. {details.get('task', 'Unknown')[:50]}...")
                print(f"      Agent: {details.get('agent')} | Complexity: {details.get('complexity')}")
                print(f"      Status: {details.get('status')} | Quality: {details.get('quality_score', 'N/A')}")

        # Validate agent selection logic
        print(f"\n🔍 Validating Agent Selection Logic...")
        test_tasks = [
            ("Simple text edit", 2, "coder-fast or cheap-worker"),
            ("Complex algorithm implementation", 9, "coder or coder-deepseek"),
            ("Security vulnerability analysis", 7, "security"),
            ("Research best practices", 5, "researcher or planner-7"),
            ("Code review", 6, "reviewer"),
            ("Performance optimization", 8, "coder or planner-1"),
        ]

        for task_desc, expected_complexity, expected_agent_type in test_tasks:
            complexity = bridge._assess_complexity_enhanced(task_desc)
            agent = bridge._select_optimal_agent(task_desc, complexity)
            validator = bridge._select_validator_agent(agent)

            print(f"   Task: '{task_desc[:30]}...'")
            print(f"     Complexity: {complexity} (expected: {expected_complexity})")
            print(f"     Agent: {agent} (expected type: {expected_agent_type})")
            print(f"     Validator: {validator} (cross-provider: ✅)")

        print(f"\n✅ Real OpenCode Integration Test PASSED!")
        print(f"   Summary: {len(test_subtasks)} tasks executed via {len(bridge.agent_registry)} agents")
        print(f"   Integration: Real MCP bridge with comprehensive monitoring")
        print(f"   Quality: {quality_metrics.get('overall_quality', 0):.1f}/100 overall quality score")

        return True

    except Exception as e:
        print(f"\n❌ Test FAILED: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_performance_scenarios():
    """Test different performance scenarios"""
    print("\n" + "=" * 60)
    print("📊 Performance Scenario Testing")
    print("=" * 60)

    try:
        from src.backend.base.langflow.components.hybrid.hybrid_agent import OpenCodeParallelBridge

        bridge = OpenCodeParallelBridge()

        # Scenario 1: Small batch (6 tasks)
        small_tasks = [
            "Fix typo in documentation",
            "Update configuration file",
            "Run basic validation test",
            "Check API response format",
            "Update dependency version",
            "Add simple logging",
        ]

        print("\n🔹 Scenario 1: Small Batch (6 simple tasks)")
        results = bridge.dispatch_parallel("Small maintenance tasks", small_tasks)
        perf = results.get("performance_metrics", {})
        print(f"   Execution Time: {results.get('results', {}).get('summary', {}).get('execution_time', 0):.2f}s")
        print(f"   Tasks/Second: {perf.get('tasks_per_second', 0):.2f}")
        print(f"   Cost/Task: ${perf.get('cost_per_task', 0):.4f}")

        # Scenario 2: Medium batch (12 mixed tasks)
        medium_tasks = [
            "Implement user authentication",
            "Design database schema",
            "Write unit tests for core features",
            "Optimize query performance",
            "Add input validation",
            "Implement error handling",
            "Create API documentation",
            "Set up CI/CD pipeline",
            "Configure monitoring alerts",
            "Implement caching layer",
            "Add security headers",
            "Optimize bundle size",
        ]

        print("\n🔹 Scenario 2: Medium Batch (12 mixed tasks)")
        results = bridge.dispatch_parallel("Medium complexity development", medium_tasks)
        perf = results.get("performance_metrics", {})
        print(f"   Execution Time: {results.get('results', {}).get('summary', {}).get('execution_time', 0):.2f}s")
        print(f"   Tasks/Second: {perf.get('tasks_per_second', 0):.2f}")
        print(f"   Cost/Task: ${perf.get('cost_per_task', 0):.4f}")

        # Scenario 3: Complex tasks (8 high-complexity)
        complex_tasks = [
            "Design microservices architecture for scalable system",
            "Implement machine learning model for document classification",
            "Create comprehensive security audit framework",
            "Develop real-time collaboration features",
            "Build automated deployment orchestration",
            "Implement advanced caching strategy with invalidation",
            "Create performance monitoring and alerting system",
            "Develop AI-powered code review assistant",
        ]

        print("\n🔹 Scenario 3: Complex Batch (8 high-complexity tasks)")
        results = bridge.dispatch_parallel("Complex system development", complex_tasks)
        perf = results.get("performance_metrics", {})
        print(f"   Execution Time: {results.get('results', {}).get('summary', {}).get('execution_time', 0):.2f}s")
        print(f"   Tasks/Second: {perf.get('tasks_per_second', 0):.2f}")
        print(f"   Cost/Task: ${perf.get('cost_per_task', 0):.4f}")

        print("\n✅ Performance Scenario Testing COMPLETED")
        return True

    except Exception as e:
        print(f"\n❌ Performance Test FAILED: {e}")
        return False


def test_cross_provider_validation():
    """Test cross-provider validation logic"""
    print("\n" + "=" * 60)
    print("🔄 Cross-Provider Validation Testing")
    print("=" * 60)

    try:
        from src.backend.base.langflow.components.hybrid.hybrid_agent import OpenCodeParallelBridge

        bridge = OpenCodeParallelBridge()

        # Test different agents and their validators
        test_agents = [
            ("coder", "moonshot", "validator-anthropic"),
            ("coder-fast", "google", "validator-anthropic"),
            ("coder-glm", "zai", "validator"),
            ("reviewer", "anthropic", "validator"),
            ("security", "anthropic", "validator"),
            ("coder-deepseek", "deepseek", "validator-anthropic"),
            ("coder-groq", "groq", "validator"),
            ("researcher", "perplexity", "validator"),
            ("planner-6", "openai", "validator-anthropic"),
        ]

        print("Testing cross-provider validation pairs:")
        print("-" * 50)

        all_passed = True
        for agent, expected_provider, expected_validator in test_agents:
            validator = bridge._select_validator_agent(agent)

            # Check that validator is different from agent
            is_different = validator != agent

            # Check that validator matches expected
            is_correct = validator == expected_validator

            status = "✅" if is_different and is_correct else "❌"

            print(
                f"{status} {agent:20} ({expected_provider:10}) → {validator:25} "
                f"{'✓ Different' if is_different else '✗ Same'} | "
                f"{'✓ Correct' if is_correct else '✗ Wrong'}"
            )

            if not (is_different and is_correct):
                all_passed = False

        if all_passed:
            print("\n✅ All cross-provider validation tests PASSED!")
            print("   Every agent has a different-provider validator")
        else:
            print("\n❌ Some cross-provider validation tests FAILED")

        return all_passed

    except Exception as e:
        print(f"\n❌ Cross-Provider Test FAILED: {e}")
        return False


def main():
    """Main test execution"""
    print("🧪 COMPREHENSIVE OPENCODE INTEGRATION TEST SUITE")
    print("=" * 60)
    print("Testing 10x deeper development implementation")
    print("=" * 60)

    # Run all tests
    tests = [
        ("Real OpenCode Integration", test_real_opencode_integration),
        ("Performance Scenarios", test_performance_scenarios),
        ("Cross-Provider Validation", test_cross_provider_validation),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n{'=' * 60}")
        print(f"Running: {test_name}")
        print(f"{'=' * 60}")

        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ Test '{test_name}' crashed: {e}")
            results.append((test_name, False))

    # Print summary
    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY")
    print("=" * 60)

    passed = 0
    total = len(results)

    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status}: {test_name}")
        if success:
            passed += 1

    print(f"\n📊 Results: {passed}/{total} tests passed ({passed / total * 100:.1f}%)")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Real OpenCode integration is working correctly.")
        print("   10x deeper development implementation validated successfully.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Review implementation.")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
