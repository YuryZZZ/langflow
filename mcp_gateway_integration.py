#!/usr/bin/env python3
"""
MCP Gateway Integration for Hybrid Multilayer System.
Connects agents to memory system via MCP server hosted on Render.
"""

import json
import requests
import sqlite3
from datetime import datetime
from typing import Dict, List, Any, Optional
import hashlib

class MCPGatewayClient:
    """Client for communicating with MCP Gateway on Render."""
    
    def __init__(self, base_url: str = "https://langflow-mcp.onrender.com"):
        self.base_url = base_url
        self.session = requests.Session()
        
    def check_connection(self) -> bool:
        """Check if MCP gateway is accessible."""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def send_to_memory(self, layer_id: int, agent_name: str, task_name: str, data: Any) -> Dict:
        """Send data to memory via MCP gateway."""
        payload = {
            "operation": "store_memory",
            "layer_id": layer_id,
            "agent_name": agent_name,
            "task_name": task_name,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/mcp/memory",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"⚠️ MCP Gateway error: {response.status_code}")
                return {"status": "error", "message": response.text}
                
        except Exception as e:
            print(f"❌ MCP Gateway connection failed: {e}")
            return {"status": "error", "message": str(e)}
    
    def get_from_memory(self, layer_id: int = None, agent_name: str = None) -> Dict:
        """Get data from memory via MCP gateway."""
        params = {}
        if layer_id:
            params["layer_id"] = layer_id
        if agent_name:
            params["agent_name"] = agent_name
        
        try:
            response = self.session.get(
                f"{self.base_url}/api/mcp/memory",
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"⚠️ MCP Gateway error: {response.status_code}")
                return {"status": "error", "message": response.text}
                
        except Exception as e:
            print(f"❌ MCP Gateway connection failed: {e}")
            return {"status": "error", "message": str(e)}
    
    def trigger_parallel_execution(self, layer_config: Dict) -> Dict:
        """Trigger parallel execution via MCP gateway."""
        payload = {
            "operation": "parallel_execution",
            "layer_config": layer_config,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/mcp/parallel",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"⚠️ MCP Gateway error: {response.status_code}")
                return {"status": "error", "message": response.text}
                
        except Exception as e:
            print(f"❌ MCP Gateway connection failed: {e}")
            return {"status": "error", "message": str(e)}
    
    def get_execution_status(self, execution_id: str) -> Dict:
        """Get status of parallel execution."""
        try:
            response = self.session.get(
                f"{self.base_url}/api/mcp/status/{execution_id}",
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"⚠️ MCP Gateway error: {response.status_code}")
                return {"status": "error", "message": response.text}
                
        except Exception as e:
            print(f"❌ MCP Gateway connection failed: {e}")
            return {"status": "error", "message": str(e)}


class HybridSystemWithMCP:
    """Hybrid system with MCP gateway integration."""
    
    def __init__(self, mcp_url: str = None, local_db: str = "hybrid_memory.db"):
        self.local_memory = sqlite3.connect(local_db)
        self.init_local_tables()
        
        # Try to connect to MCP gateway
        self.mcp_client = MCPGatewayClient(mcp_url) if mcp_url else None
        self.use_mcp = False
        
        if self.mcp_client:
            self.use_mcp = self.mcp_client.check_connection()
            if self.use_mcp:
                print("✅ Connected to MCP Gateway on Render")
            else:
                print("⚠️ MCP Gateway not available, using local memory")
    
    def init_local_tables(self):
        """Initialize local memory tables."""
        cursor = self.local_memory.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mcp_sync (
                sync_id INTEGER PRIMARY KEY AUTOINCREMENT,
                local_id INTEGER NOT NULL,
                mcp_id TEXT,
                entity_type TEXT NOT NULL,
                synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sync_status TEXT DEFAULT 'pending'
            )
        ''')
        
        self.local_memory.commit()
    
    def store_layer_result(self, layer_id: int, agent_name: str, task_name: str, result: Any) -> str:
        """Store result locally and optionally sync to MCP."""
        result_json = json.dumps(result)
        result_hash = hashlib.sha256(result_json.encode()).hexdigest()
        
        # Store locally
        cursor = self.local_memory.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO results (layer_id, agent_name, task_name, result_content, result_hash)
            VALUES (?, ?, ?, ?, ?)
        ''', (layer_id, agent_name, task_name, result_json, result_hash))
        
        local_id = cursor.lastrowid
        
        # Sync to MCP if available
        if self.use_mcp:
            mcp_response = self.mcp_client.send_to_memory(layer_id, agent_name, task_name, result)
            
            if mcp_response.get("status") == "success":
                mcp_id = mcp_response.get("memory_id")
                cursor.execute('''
                    INSERT INTO mcp_sync (local_id, mcp_id, entity_type, sync_status)
                    VALUES (?, ?, 'result', 'synced')
                ''', (local_id, mcp_id))
                print(f"✅ Result synced to MCP Gateway (ID: {mcp_id})")
            else:
                cursor.execute('''
                    INSERT INTO mcp_sync (local_id, entity_type, sync_status)
                    VALUES (?, 'result', 'failed')
                ''', (local_id,))
                print(f"⚠️ MCP sync failed: {mcp_response.get('message')}")
        
        self.local_memory.commit()
        return result_hash
    
    def get_previous_layer_results(self, current_layer: int, agent_name: str) -> Dict:
        """Get results from previous layers, trying MCP first then local."""
        results = {}
        
        # Try MCP first
        if self.use_mcp:
            mcp_results = self.mcp_client.get_from_memory(agent_name=agent_name)
            
            if mcp_results.get("status") == "success":
                print(f"📡 Retrieved {len(mcp_results.get('data', []))} results from MCP Gateway")
                results["source"] = "mcp"
                results["data"] = mcp_results.get("data", [])
                return results
        
        # Fall back to local
        cursor = self.local_memory.cursor()
        cursor.execute('''
            SELECT l.layer_number, l.layer_name, r.task_name, r.result_content
            FROM layers l
            JOIN results r ON l.layer_id = r.layer_id
            WHERE l.layer_number < ? AND r.agent_name = ?
            ORDER BY l.layer_number
        ''', (current_layer, agent_name))
        
        local_results = []
        for row in cursor.fetchall():
            layer_number, layer_name, task_name, result_content = row
            local_results.append({
                "layer": layer_number,
                "layer_name": layer_name,
                "task": task_name,
                "result": json.loads(result_content)
            })
        
        print(f"💾 Retrieved {len(local_results)} results from local memory")
        results["source"] = "local"
        results["data"] = local_results
        return results
    
    def execute_layer_with_mcp(self, layer_config: Dict) -> Dict:
        """Execute a layer using MCP parallel execution."""
        if not self.use_mcp:
            return {"status": "error", "message": "MCP Gateway not available"}
        
        print(f"🚀 Triggering parallel execution via MCP Gateway...")
        print(f"   Layer: {layer_config.get('name')}")
        print(f"   Agents: {layer_config.get('max_agents')}")
        print(f"   Type: {layer_config.get('type')}")
        
        response = self.mcp_client.trigger_parallel_execution(layer_config)
        
        if response.get("status") == "success":
            execution_id = response.get("execution_id")
            print(f"✅ Parallel execution started (ID: {execution_id})")
            
            # Monitor execution
            return self.monitor_execution(execution_id)
        else:
            print(f"❌ Failed to trigger execution: {response.get('message')}")
            return response
    
    def monitor_execution(self, execution_id: str, max_checks: int = 20) -> Dict:
        """Monitor execution progress via MCP."""
        print(f"📊 Monitoring execution {execution_id}...")
        
        for i in range(max_checks):
            status = self.mcp_client.get_execution_status(execution_id)
            
            if status.get("status") == "completed":
                print(f"✅ Execution completed successfully")
                return status
            elif status.get("status") == "failed":
                print(f"❌ Execution failed: {status.get('message')}")
                return status
            else:
                progress = status.get("progress", 0)
                print(f"   Progress: {progress}% ({i+1}/{max_checks})")
                
                if i < max_checks - 1:
                    import time
                    time.sleep(5)  # Wait 5 seconds between checks
        
        print(f"⚠️ Execution monitoring timeout")
        return {"status": "timeout", "execution_id": execution_id}
    
    def close(self):
        """Close connections."""
        self.local_memory.close()


def test_mcp_integration():
    """Test MCP gateway integration."""
    print("🧪 TESTING MCP GATEWAY INTEGRATION")
    print("="*60)
    
    # Try to connect to Render MCP gateway
    mcp_url = "https://langflow-mcp.onrender.com"
    system = HybridSystemWithMCP(mcp_url)
    
    if system.use_mcp:
        print("✅ Connected to MCP Gateway on Render")
        
        # Test storing data
        print("\n📝 Testing data storage via MCP...")
        result = system.store_layer_result(
            layer_id=1,
            agent_name="Test Agent",
            task_name="Test Analysis",
            result={"test": "data", "timestamp": datetime.now().isoformat()}
        )
        
        print(f"   Result hash: {result}")
        
        # Test retrieving data
        print("\n🔍 Testing data retrieval via MCP...")
        previous_results = system.get_previous_layer_results(
            current_layer=2,
            agent_name="Test Agent"
        )
        
        print(f"   Source: {previous_results.get('source')}")
        print(f"   Results count: {len(previous_results.get('data', []))}")
        
        # Test parallel execution
        print("\n🚀 Testing parallel execution via MCP...")
        layer_config = {
            "name": "Test Parallel Layer",
            "type": "parallel",
            "max_agents": 4,
            "tasks": [
                "Task 1: Analyze requirements",
                "Task 2: Design architecture",
                "Task 3: Implement core",
                "Task 4: Write tests"
            ]
        }
        
        execution_result = system.execute_layer_with_mcp(layer_config)
        print(f"   Execution result: {execution_result.get('status')}")
        
    else:
        print("⚠️ MCP Gateway not available, testing local fallback...")
        
        # Test local storage
        print("\n📝 Testing local data storage...")
        result = system.store_layer_result(
            layer_id=1,
            agent_name="Local Test Agent",
            task_name="Local Analysis",
            result={"local": "test", "timestamp": datetime.now().isoformat()}
        )
        
        print(f"   Result hash: {result}")
        
        # Test local retrieval
        print("\n🔍 Testing local data retrieval...")
        previous_results = system.get_previous_layer_results(
            current_layer=2,
            agent_name="Local Test Agent"
        )
        
        print(f"   Source: {previous_results.get('source')}")
        print(f"   Results count: {len(previous_results.get('data', []))}")
    
    system.close()
    print("\n✅ MCP integration test completed!")


def create_mcp_enhanced_hybrid_flow():
    """Create a hybrid flow with MCP integration."""
    flow = {
        "name": "Hybrid Multilayer with MCP Integration",
        "description": "5-layer hybrid execution with MCP gateway for cross-layer memory",
        "version": "3.0.0",
        "created": datetime.now().strftime("%Y-%m-%d"),
        "mcp_config": {
            "gateway_url": "https://langflow-mcp.onrender.com",
            "memory_endpoint": "/api/mcp/memory",
            "parallel_endpoint": "/api/mcp/parallel",
            "status_endpoint": "/api/mcp/status",
            "fallback_mode": "local_memory"
        },
        "layers": [
            {
                "id": "layer1",
                "name": "Parallel Analysis with MCP",
                "type": "parallel",
                "max_agents": 8,
                "mcp_integration": True,
                "memory_access": "write_only",
                "tasks": [
                    {
                        "name": "Technical Analysis",
                        "agent": "technical_agent",
                        "mcp_store": True
                    },
                    {
                        "name": "UX Analysis",
                        "agent": "ux_agent",
                        "mcp_store": True
                    },
                    {
                        "name": "Business Analysis",
                        "agent": "business_agent",
                        "mcp_store": True
                    },
                    {
                        "name": "Security Analysis",
                        "agent": "security_agent",
                        "mcp_store": True
                    }
                ]
            },
            {
                "id": "layer2",
                "name": "Sequential Design with Memory Read",
                "type": "sequential",
                "max_agents": 4,
                "mcp_integration": True,
                "memory_access": "read_write",
                "dependencies": ["layer1"],
                "tasks": [
                    {
                        "name": "Architecture Design",
                        "agent": "architecture_agent",
                        "read_from": ["layer1"],
                        "mcp_store": True
                    },
                    {
                        "name": "Component Design",
                        "agent": "component_agent",
                        "read_from": ["layer1"],
                        "mcp_store": True
                    }
                ]
            }
        ],
        "components": [
            {
                "id": "mcp_gateway",
                "type": "MCPGateway",
                "config": {
                    "url": "https://langflow-mcp.onrender.com",
                    "auto_reconnect": True,
                    "timeout": 30,
                    "retry_attempts": 3
                }
            },
            {
                "id": "memory_bridge",
                "type": "MemoryBridge",
                "config": {
                    "primary": "mcp_gateway",
                    "fallback": "local_sqlite",
                    "sync_interval": 5,
                    "conflict_resolution": "mcp_priority"
                }
            }
        ]
    }
    
    # Save the flow
    flow_path = "agent/workflows/hybrid_mcp_integrated.json"
    with open(flow_path, 'w') as f:
        json.dump(flow, f, indent=2)
    
    print(f"✅ Created MCP-enhanced hybrid flow: {flow_path}")
    return flow_path


if __name__ == "__main__":
    print("🚀 HYBRID SYSTEM WITH MCP INTEGRATION")
    print("="*60)
    
    # Test MCP integration
    test_mcp_integration()
    
    # Create enhanced flow
    flow_path = create_mcp_enhanced_hybrid_flow()
    
    print("\n🎯 SYSTEM READY WITH:")
    print("1. MCP Gateway integration for cross-layer memory")
    print("2. Automatic fallback to local storage")
    print("3. Parallel execution via MCP")
    print("4. Real-time progress monitoring")
    print(f"5. Enhanced flow file: {flow_path}")
    
    print("\n🔗 AGENTS CAN NOW:")
    print("• Read previous layer results via MCP")
    print("• Store results in shared memory")
    print("• Trigger parallel execution")
    print("• Monitor execution progress in real-time")