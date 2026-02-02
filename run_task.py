#!/usr/bin/env python3
"""
Simple interface to submit tasks to the Dynamic Flow Generator
Usage: python run_task.py "Your task description here"
"""

import sys
import argparse
from dynamic_flow_generator import DynamicFlowGenerator

def main():
    parser = argparse.ArgumentParser(description='Create and execute Langflow flows from tasks')
    parser.add_argument('task', help='The task description')
    parser.add_argument('--no-execute', action='store_true', help='Create flow but do not execute')
    parser.add_argument('--mcp-url', default='https://langflow-mcp.onrender.com', help='MCP gateway URL')
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("🚀 OPENCODE DYNAMIC FLOW GENERATOR")
    print("="*70)
    
    # Initialize generator
    generator = DynamicFlowGenerator(mcp_url=args.mcp_url)
    
    # Process task
    result = generator.process_user_task(
        user_task=args.task,
        auto_execute=not args.no_execute
    )
    
    print("\n" + "="*70)
    print("✅ TASK PROCESSING COMPLETE")
    print("="*70)
    print(f"\nFlow created: {result['flow_path']}")
    
    if result.get('execution'):
        print(f"Execution status: {result['execution'].get('status', 'unknown')}")
    
    print("\n📁 Flow files location: agent/workflows/dynamic/")
    print("🔗 Connect to Langflow at: https://langflow-7vd3.onrender.com")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_task.py 'Your task description'")
        print("\nExample:")
        print('  python run_task.py "Create a REST API with authentication and tests"')
        sys.exit(1)
    
    main()
