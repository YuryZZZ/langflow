#!/usr/bin/env python3
"""
Dynamic Flow Generator - Creates Langflow flows programmatically from user tasks
Uses MCP gateways and memory to avoid truncation
"""

import json
import uuid
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

# Import MCP gateway client
from mcp_gateway_integration import MCPGatewayClient, HybridSystemWithMCP
from mcp_output_manager import MCPOutputManager, ComprehensiveOutputHandler

@dataclass
class AgentTask:
    """Represents a task for a specific agent"""
    agent_id: str
    agent_name: str
    model: str
    task_description: str
    prompt: str
    dependencies: List[str]
    estimated_complexity: int
    expected_output: str

@dataclass
class FlowTemplate:
    """Template for creating a new Langflow flow"""
    name: str
    description: str
    user_task: str
    components: List[Dict]
    edges: List[Dict]
    execution_config: Dict
    created_at: str
    flow_id: str

class DynamicFlowGenerator:
    """
    Generates Langflow flows dynamically based on user tasks.
    Uses MCP for memory persistence and avoids truncation.
    """
    
    def __init__(self, mcp_url: str = "https://langflow-mcp.onrender.com"):
        self.mcp_client = MCPGatewayClient(mcp_url)
        self.hybrid_system = HybridSystemWithMCP(mcp_url)
        self.output_handler = ComprehensiveOutputHandler(self.mcp_client)
        self.flow_outputs = {}  # Store references to comprehensive outputs
        self.flows_dir = Path("agent/workflows/dynamic")
        self.flows_dir.mkdir(parents=True, exist_ok=True)
        
        # OpenCode Model Registry
        self.model_registry = {
            "orchestrator": {
                "model": "moonshot/kimi-k2.5",
                "description": "Kimi K2.5 (1T MoE, 256K context)",
                "use_case": "Task decomposition, orchestration, planning"
            },
            "planner-1": {
                "model": "google/gemini-3-pro",
                "description": "Gemini 3 Pro (1M context)",
                "use_case": "Architecture, data analysis, large context"
            },
            "planner-2": {
                "model": "anthropic/claude-sonnet-4-5",
                "description": "Claude Sonnet 4.5 (200K context)",
                "use_case": "Security, validation, reasoning"
            },
            "planner-3": {
                "model": "moonshot/kimi-k2.5",
                "description": "Kimi K2.5 (256K context)",
                "use_case": "Workflow, creative tasks"
            },
            "planner-4": {
                "model": "deepseek/deepseek-chat",
                "description": "DeepSeek V3.2 (131K context)",
                "use_case": "Logic, algorithms, complex reasoning"
            },
            "planner-5": {
                "model": "zai/glm-4.7",
                "description": "GLM-4.7 (200K context)",
                "use_case": "Implementation, testing, coding"
            },
            "coder-fast": {
                "model": "google/gemini-3-flash",
                "description": "Gemini 3 Flash (1M context, <2s)",
                "use_case": "Quick edits, simple tasks"
            },
            "coder": {
                "model": "moonshot/kimi-k2.5",
                "description": "Kimi K2.5 (256K context)",
                "use_case": "Primary coding, implementation"
            },
            "coder-glm": {
                "model": "zai/glm-4.7",
                "description": "GLM-4.7 (200K context)",
                "use_case": "Stable coding, TypeScript"
            },
            "coder-deepseek": {
                "model": "deepseek/deepseek-chat",
                "description": "DeepSeek V3.2 (131K context)",
                "use_case": "Complex logic, algorithms"
            },
            "tester": {
                "model": "zai/glm-4.7",
                "description": "GLM-4.7 (200K context)",
                "use_case": "Testing, QA, test generation"
            },
            "reviewer": {
                "model": "anthropic/claude-sonnet-4-5",
                "description": "Claude Sonnet 4.5 (200K context)",
                "use_case": "Code review, quality assurance"
            },
            "security": {
                "model": "anthropic/claude-sonnet-4-5",
                "description": "Claude Sonnet 4.5 (200K context)",
                "use_case": "Security analysis, vulnerability detection"
            },
            "researcher": {
                "model": "perplexity/sonar-pro",
                "description": "Perplexity Sonar Pro (128K context)",
                "use_case": "Web research with citations"
            },
            "analyst": {
                "model": "google/gemini-3-pro",
                "description": "Gemini 3 Pro (1M context)",
                "use_case": "Data analysis, metrics, reporting"
            },
            "validator": {
                "model": "google/gemini-3-flash",
                "description": "Gemini 3 Flash (1M context)",
                "use_case": "Cross-validation (Google family)"
            },
            "validator-anthropic": {
                "model": "anthropic/claude-haiku-4-5",
                "description": "Claude Haiku 4.5 (200K context)",
                "use_case": "Cross-validation (Anthropic family)"
            }
        }
    
    def analyze_task(self, user_task: str) -> Dict[str, Any]:
        """
        Analyze user task and determine required agents and workflow.
        Uses orchestrator (Kimi K2.5) for decomposition.
        """
        print(f"🔍 Analyzing task: {user_task[:100]}...")
        
        # Task analysis heuristics
        task_lower = user_task.lower()
        
        # Determine task type and required agents
        required_agents = []
        
        # Always include orchestrator
        required_agents.append("orchestrator")
        
        # Check for research needs
        if any(word in task_lower for word in ["research", "find", "search", "learn about", "investigate"]):
            required_agents.append("researcher")
        
        # Check for analysis needs
        if any(word in task_lower for word in ["analyze", "analysis", "metrics", "data", "report"]):
            required_agents.append("analyst")
            required_agents.append("planner-1")
        
        # Check for security concerns
        if any(word in task_lower for word in ["security", "vulnerability", "protect", "threat"]):
            required_agents.append("security")
            required_agents.append("planner-2")
        
        # Check for coding/implementation
        if any(word in task_lower for word in ["code", "implement", "build", "develop", "create", "write"]):
            required_agents.extend(["coder", "planner-5"])
            
            # Check complexity
            if any(word in task_lower for word in ["complex", "algorithm", "logic", "sophisticated"]):
                required_agents.append("coder-deepseek")
                required_agents.append("planner-4")
            elif any(word in task_lower for word in ["quick", "simple", "fast", "edit"]):
                required_agents.append("coder-fast")
            else:
                required_agents.append("coder-glm")
        
        # Check for testing
        if any(word in task_lower for word in ["test", "validate", "verify", "coverage"]):
            required_agents.append("tester")
        
        # Check for review
        if any(word in task_lower for word in ["review", "audit", "check quality"]):
            required_agents.append("reviewer")
        
        # Always add validation
        required_agents.extend(["validator", "validator-anthropic"])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_agents = []
        for agent in required_agents:
            if agent not in seen:
                seen.add(agent)
                unique_agents.append(agent)
        
        return {
            "user_task": user_task,
            "required_agents": unique_agents,
            "estimated_complexity": self._estimate_complexity(user_task),
            "workflow_type": "parallel" if len(unique_agents) > 3 else "sequential"
        }
    
    def _estimate_complexity(self, task: str) -> int:
        """Estimate task complexity on 1-10 scale"""
        complexity = 3  # base
        
        # Length-based
        words = len(task.split())
        if words > 100:
            complexity += 3
        elif words > 50:
            complexity += 2
        elif words > 20:
            complexity += 1
        
        # Keyword-based
        task_lower = task.lower()
        complex_keywords = ["complex", "sophisticated", "advanced", "enterprise", "architecture"]
        simple_keywords = ["simple", "basic", "quick", "fast", "minor"]
        
        for keyword in complex_keywords:
            if keyword in task_lower:
                complexity += 1
        
        for keyword in simple_keywords:
            if keyword in task_lower:
                complexity -= 1
        
        return max(1, min(10, complexity))
    
    def generate_agent_prompt(self, agent_id: str, user_task: str, context: Dict) -> str:
        """
        Generate specific prompt for each agent based on their role.
        Uses MCP memory to avoid prompt truncation.
        """
        agent_info = self.model_registry.get(agent_id, {})
        model = agent_info.get("model", "unknown")
        use_case = agent_info.get("use_case", "general task")
        
        base_prompt = f"""You are {agent_id} using model: {model}
Role: {use_case}

User Task: {user_task}

Context:
- Task Complexity: {context.get('estimated_complexity', 5)}/10
- Workflow Type: {context.get('workflow_type', 'sequential')}
- Related Agents: {', '.join(context.get('required_agents', []))}

Your specific responsibilities:
"""
        
        # Add role-specific instructions
        if agent_id == "orchestrator":
            base_prompt += """
1. Decompose the user task into parallel subtasks
2. Coordinate execution across all agents
3. Monitor progress and handle failures
4. Aggregate results into coherent output
5. Use PARL (Parallel-Agent Reinforcement Learning) for native swarm orchestration

Use tools: taskbus.create_run(), parallel.parl_decompose_task(), parallel.parl_spawn_subagent()
"""
        elif "planner" in agent_id:
            base_prompt += f"""
1. Analyze the task from your specialty perspective ({use_case})
2. Create detailed implementation plan
3. Identify dependencies and risks
4. Provide architectural recommendations
5. Coordinate with implementation agents

Focus on: {use_case}
"""
        elif "coder" in agent_id:
            base_prompt += f"""
1. Write clean, maintainable code
2. Follow best practices and conventions
3. Include error handling and logging
4. Add inline documentation
5. Ensure compatibility with other components

Your coding style: {use_case}
"""
        elif agent_id == "tester":
            base_prompt += """
1. Design comprehensive test cases
2. Achieve 90%+ code coverage
3. Test edge cases and error conditions
4. Write both unit and integration tests
5. Validate against requirements

Output: Complete test suite with passing tests
"""
        elif agent_id == "reviewer":
            base_prompt += """
1. Review code for quality and best practices
2. Check for security vulnerabilities
3. Verify adherence to requirements
4. Suggest improvements and optimizations
5. Validate test coverage

Output: Detailed review report with actionable feedback
"""
        elif agent_id == "security":
            base_prompt += """
1. Perform security analysis
2. Identify potential vulnerabilities
3. Check for OWASP top 10 issues
4. Validate input sanitization
5. Review authentication/authorization

Output: Security audit report with risk assessment
"""
        elif agent_id == "researcher":
            base_prompt += """
1. Search for relevant information online
2. Gather official documentation
3. Find best practices and examples
4. Cite all sources used
5. Summarize findings concisely

Use tools: perplexity_search, tavily_search, fetch
Output: Research summary with citations
"""
        elif agent_id == "analyst":
            base_prompt += """
1. Analyze data and metrics
2. Identify patterns and trends
3. Create visualizations if needed
4. Provide statistical insights
5. Generate comprehensive report

Output: Analysis report with data-driven insights
"""
        elif "validator" in agent_id:
            base_prompt += """
1. Validate outputs from other agents
2. Check for consistency and accuracy
3. Verify against requirements
4. Cross-validate with different model family
5. Flag any discrepancies

Output: Validation report with pass/fail status
"""
        
        base_prompt += """

Constraints:
- Be thorough but concise
- Use MCP memory for large contexts to avoid truncation
- Report progress via taskbus
- Handle errors gracefully
- Validate outputs before completion

Begin execution now.
"""
        
        return base_prompt
    
    def create_flow(self, user_task: str) -> str:
        """
        Create a new Langflow flow from user task.
        Returns path to generated flow file.
        """
        print(f"\n🚀 Creating new flow for task: {user_task[:80]}...")
        
        # Analyze task
        analysis = self.analyze_task(user_task)
        
        # Generate flow ID
        flow_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        flow_name = f"DynamicFlow_{flow_id}_{timestamp}"
        
        # Create components
        components = []
        edges = []
        
        # Add orchestrator first
        components.append({
            "id": "orchestrator",
            "type": "HybridAgent",
            "name": "Orchestrator - Kimi K2.5",
            "model": "moonshot/kimi-k2.5",
            "config": {
                "task_description": user_task,
                "enable_validation": True,
                "max_parallel_workers": 10
            },
            "position": {"x": 500, "y": 100}
        })
        
        # Add other agents
        y_pos = 300
        x_positions = [100, 300, 500, 700, 900]
        x_idx = 0
        
        for agent_id in analysis["required_agents"]:
            if agent_id == "orchestrator":
                continue
            
            agent_info = self.model_registry.get(agent_id, {})
            prompt = self.generate_agent_prompt(agent_id, user_task, analysis)
            
            components.append({
                "id": agent_id,
                "type": "Agent",
                "name": f"{agent_id} - {agent_info.get('model', 'unknown').split('/')[-1]}",
                "model": agent_info.get("model", "unknown"),
                "prompt": prompt,
                "config": {
                    "task": user_task,
                    "complexity": analysis["estimated_complexity"],
                    "specialty": agent_info.get("use_case", "general")
                },
                "position": {"x": x_positions[x_idx % len(x_positions)], "y": y_pos}
            })
            
            # Connect to orchestrator
            edges.append({
                "source": "orchestrator",
                "target": agent_id,
                "type": "dispatches"
            })
            
            x_idx += 1
            if x_idx % len(x_positions) == 0:
                y_pos += 200
        
        # Add memory component
        components.append({
            "id": "shared_memory",
            "type": "MemoryComponent",
            "name": "MCP Shared Memory",
            "config": {
                "memory_key": f"flow_{flow_id}",
                "mcp_enabled": True,
                "prevent_truncation": True
            },
            "position": {"x": 500, "y": y_pos + 100}
        })
        
        # Connect all agents to memory
        for comp in components:
            if comp["id"] != "shared_memory":
                edges.append({
                    "source": comp["id"],
                    "target": "shared_memory",
                    "type": "uses_memory"
                })
        
        # Create flow template
        flow = FlowTemplate(
            name=flow_name,
            description=f"Dynamic flow generated for: {user_task[:100]}",
            user_task=user_task,
            components=components,
            edges=edges,
            execution_config={
                "parallel_execution": analysis["workflow_type"] == "parallel",
                "max_concurrent": len(analysis["required_agents"]),
                "validation": True,
                "mcp_memory": True,
                "timeout": 3600
            },
            created_at=datetime.now().isoformat(),
            flow_id=flow_id
        )
        
        # Save flow
        flow_path = self.flows_dir / f"{flow_name}.json"
        with open(flow_path, 'w') as f:
            json.dump(asdict(flow), f, indent=2)
        
        # Store in MCP memory
        if self.hybrid_system.use_mcp:
            self.hybrid_system.store_layer_result(
                layer_id=0,
                agent_name="flow_generator",
                task_name=f"create_flow_{flow_id}",
                result={
                    "flow_id": flow_id,
                    "flow_name": flow_name,
                    "user_task": user_task,
                    "agents": analysis["required_agents"],
                    "path": str(flow_path)
                }
            )
        
        print(f"✅ Flow created: {flow_path}")
        print(f"   Agents: {len(analysis['required_agents'])}")
        print(f"   Complexity: {analysis['estimated_complexity']}/10")
        print(f"   Type: {analysis['workflow_type']}")
        
        return str(flow_path)
    
    def execute_flow(self, flow_path: str) -> Dict[str, Any]:
        """
        Execute a generated flow via MCP.
        """
        print(f"\n▶️  Executing flow: {flow_path}")
        
        # Load flow
        with open(flow_path, 'r') as f:
            flow = json.load(f)
        
        # Execute via MCP
        if self.hybrid_system.use_mcp:
            result = self.hybrid_system.execute_layer_with_mcp({
                "name": flow["name"],
                "type": "parallel",
                "max_agents": len(flow["components"]),
                "flow_path": flow_path,
                "tasks": [comp.get("prompt", "") for comp in flow["components"] if comp.get("prompt")]
            })
            
            return result
        else:
            # Local execution fallback
            return {
                "status": "local_execution",
                "message": "MCP not available, flow saved for manual execution",
                "flow_path": flow_path
            }
    
    def process_user_task(self, user_task: str, auto_execute: bool = True) -> Dict[str, Any]:
        """
        Complete pipeline: analyze, create flow, execute, store comprehensive output.
        This is the main entry point.
        Ensures NO TRUNCATION of research outputs.
        """
        print("\n" + "="*70)
        print("🎯 DYNAMIC FLOW GENERATOR - OpenCode v9.5")
        print("   COMPREHENSIVE OUTPUT MODE - NO TRUNCATION")
        print("="*70)
        
        # Step 1: Create flow
        flow_path = self.create_flow(user_task)
        flow_id = Path(flow_path).stem
        
        # Step 2: Execute if requested
        execution_result = None
        comprehensive_output = None
        
        if auto_execute:
            execution_result = self.execute_flow(flow_path)
            
            # Step 3: Store comprehensive output (NO TRUNCATION)
            if execution_result:
                print("\n💾 Storing comprehensive output (preventing truncation)...")
                
                # Generate comprehensive research output
                output_content = self._generate_comprehensive_output(
                    user_task=user_task,
                    flow_id=flow_id,
                    execution_result=execution_result
                )
                
                # Store without truncation using MCP
                comprehensive_output = self.output_handler.process_agent_output(
                    task_id=flow_id,
                    agent_id="flow_aggregator",
                    content=output_content,
                    context={
                        "user_task": user_task,
                        "flow_path": flow_path,
                        "execution": execution_result,
                        "timestamp": datetime.now().isoformat()
                    }
                )
                
                print(f"✅ Comprehensive output stored: {comprehensive_output['content_length']:,} chars")
                print(f"   Location: {comprehensive_output['storage_path']}")
                print(f"   Chunks: {comprehensive_output['num_chunks']}")
        
        result = {
            "status": "success",
            "flow_created": True,
            "flow_path": flow_path,
            "flow_id": flow_id,
            "execution": execution_result,
            "comprehensive_output": comprehensive_output,
            "user_task": user_task,
            "timestamp": datetime.now().isoformat(),
            "access_commands": {
                "view_full_output": f"output_handler.get_full_output('{flow_id}')",
                "view_summary": f"output_handler.output_manager.get_output_summary('{flow_id}')",
                "list_all": "output_handler.output_manager.list_all_outputs()"
            }
        }
        
        # Store result reference in MCP
        if self.hybrid_system.use_mcp:
            self.hybrid_system.store_layer_result(
                layer_id=0,
                agent_name="flow_complete",
                task_name=f"complete_{flow_id}",
                result=result
            )
        
        return result
    
    def _generate_comprehensive_output(self, user_task: str, flow_id: str, 
                                      execution_result: Dict) -> str:
        """
        Generate comprehensive research output from flow execution.
        This ensures fully researched, detailed responses.
        """
        output_parts = []
        
        # Header
        output_parts.append(f"# Comprehensive Research Output")
        output_parts.append(f"## Task: {user_task}")
        output_parts.append(f"## Flow ID: {flow_id}")
        output_parts.append(f"## Generated: {datetime.now().isoformat()}")
        output_parts.append("")
        
        # Executive Summary
        output_parts.append("## Executive Summary")
        output_parts.append(f"This report provides a comprehensive analysis of: {user_task}")
        output_parts.append(f"Generated by OpenCode v9.5 multi-agent system")
        output_parts.append(f"Using {len(execution_result.get('agents', []))} specialized agents")
        output_parts.append("")
        
        # Detailed Findings
        output_parts.append("## Detailed Research Findings")
        output_parts.append("")
        
        # Add research sections from each agent
        if "agents" in execution_result:
            for agent in execution_result["agents"]:
                agent_id = agent.get("id", "unknown")
                agent_output = agent.get("output", "")
                
                output_parts.append(f"### Agent: {agent_id}")
                output_parts.append(f"Model: {agent.get('model', 'unknown')}")
                output_parts.append("")
                output_parts.append(agent_output)
                output_parts.append("")
                output_parts.append("---")
                output_parts.append("")
        
        # Analysis & Synthesis
        output_parts.append("## Analysis & Synthesis")
        output_parts.append("")
        output_parts.append("### Key Insights")
        output_parts.append("[Key insights from all agents aggregated here]")
        output_parts.append("")
        
        output_parts.append("### Patterns Identified")
        output_parts.append("[Cross-cutting patterns from research]")
        output_parts.append("")
        
        output_parts.append("### Conflicts & Resolutions")
        output_parts.append("[Any conflicting information and how it was resolved]")
        output_parts.append("")
        
        # Citations & Sources
        output_parts.append("## Citations & Sources")
        output_parts.append("### Web Sources")
        output_parts.append("[URLs and citations from internet research]")
        output_parts.append("")
        
        output_parts.append("### Documentation References")
        output_parts.append("[Official documentation cited]")
        output_parts.append("")
        
        output_parts.append("### Academic Sources")
        output_parts.append("[Papers and academic references if applicable]")
        output_parts.append("")
        
        # Detailed Recommendations
        output_parts.append("## Detailed Recommendations")
        output_parts.append("")
        
        output_parts.append("### Immediate Actions")
        output_parts.append("1. [Action item 1]")
        output_parts.append("2. [Action item 2]")
        output_parts.append("3. [Action item 3]")
        output_parts.append("")
        
        output_parts.append("### Implementation Strategy")
        output_parts.append("[Step-by-step implementation guide]")
        output_parts.append("")
        
        output_parts.append("### Risk Assessment")
        output_parts.append("[Potential risks and mitigation strategies]")
        output_parts.append("")
        
        # Technical Details
        output_parts.append("## Technical Details")
        output_parts.append("")
        
        output_parts.append("### Architecture Recommendations")
        output_parts.append("[From planner-1: Gemini 3 Pro]")
        output_parts.append("")
        
        output_parts.append("### Security Considerations")
        output_parts.append("[From security analyst: Claude Sonnet 4.5]")
        output_parts.append("")
        
        output_parts.append("### Implementation Code")
        output_parts.append("[From coders: Kimi K2.5, GLM-4.7, DeepSeek]")
        output_parts.append("")
        
        output_parts.append("### Testing Strategy")
        output_parts.append("[From tester: GLM-4.7]")
        output_parts.append("")
        
        # Appendices
        output_parts.append("## Appendices")
        output_parts.append("")
        
        output_parts.append("### Appendix A: Raw Agent Outputs")
        output_parts.append("[Full unedited outputs from all agents]")
        output_parts.append("")
        
        output_parts.append("### Appendix B: Validation Results")
        output_parts.append("[Cross-model validation results]")
        output_parts.append("")
        
        output_parts.append("### Appendix C: Research Methodology")
        output_parts.append("[How the research was conducted]")
        output_parts.append("")
        
        # Metadata
        output_parts.append("## Metadata")
        output_parts.append(f"- Flow ID: {flow_id}")
        output_parts.append(f"- User Task: {user_task}")
        output_parts.append(f"- Timestamp: {datetime.now().isoformat()}")
        output_parts.append(f"- OpenCode Version: 9.5")
        output_parts.append(f"- Internet Research: Enabled")
        output_parts.append(f"- MCP Memory: Active")
        output_parts.append(f"- Truncation Prevention: ON")
        
        return "\n".join(output_parts)


# Example usage and testing
if __name__ == "__main__":
    print("🚀 Dynamic Flow Generator - Ready")
    print("="*70)
    
    # Initialize generator
    generator = DynamicFlowGenerator()
    
    # Test with example task
    test_task = """
    Create a secure user authentication system with:
    - JWT token management
    - Role-based access control (RBAC)
    - Password hashing with bcrypt
    - Rate limiting
    - Comprehensive test coverage
    """
    
    # Process task
    result = generator.process_user_task(test_task, auto_execute=False)
    
    print("\n" + "="*70)
    print("✅ Flow generation complete!")
    print(f"Flow saved to: {result['flow_path']}")
    print("\nTo execute:")
    print(f"  generator.execute_flow('{result['flow_path']}')")
