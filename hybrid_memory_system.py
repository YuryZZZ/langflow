#!/usr/bin/env python3
"""
Hybrid Memory System for cross-layer communication.
Enables agents to read previous layer results via MCP server.
"""

import json
import os
import sqlite3
from datetime import datetime
from typing import Dict, List, Any, Optional
import hashlib

class HybridMemorySystem:
    """Memory system for storing and retrieving layer results."""
    
    def __init__(self, db_path: str = "hybrid_memory.db"):
        """Initialize memory system with SQLite database."""
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create layers table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS layers (
                layer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                layer_number INTEGER NOT NULL,
                layer_name TEXT NOT NULL,
                layer_type TEXT NOT NULL,
                start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_time TIMESTAMP,
                status TEXT DEFAULT 'in_progress',
                quality_score REAL,
                metadata TEXT
            )
        ''')
        
        # Create results table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS results (
                result_id INTEGER PRIMARY KEY AUTOINCREMENT,
                layer_id INTEGER NOT NULL,
                agent_name TEXT NOT NULL,
                task_name TEXT NOT NULL,
                result_content TEXT NOT NULL,
                result_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (layer_id) REFERENCES layers (layer_id)
            )
        ''')
        
        # Create dependencies table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dependencies (
                dependency_id INTEGER PRIMARY KEY AUTOINCREMENT,
                layer_id INTEGER NOT NULL,
                depends_on_layer_id INTEGER NOT NULL,
                dependency_type TEXT NOT NULL,
                satisfied BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (layer_id) REFERENCES layers (layer_id),
                FOREIGN KEY (depends_on_layer_id) REFERENCES layers (layer_id)
            )
        ''')
        
        # Create agent_access table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agent_access (
                access_id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT NOT NULL,
                layer_id INTEGER NOT NULL,
                access_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                operation TEXT NOT NULL,
                FOREIGN KEY (layer_id) REFERENCES layers (layer_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def start_layer(self, layer_number: int, layer_name: str, layer_type: str) -> int:
        """Start a new layer execution."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO layers (layer_number, layer_name, layer_type, status)
            VALUES (?, ?, ?, 'in_progress')
        ''', (layer_number, layer_name, layer_type))
        
        layer_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        print(f"📝 Started Layer {layer_number}: {layer_name} (ID: {layer_id})")
        return layer_id
    
    def complete_layer(self, layer_id: int, quality_score: float = None, metadata: Dict = None):
        """Mark a layer as completed."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        metadata_json = json.dumps(metadata) if metadata else None
        
        cursor.execute('''
            UPDATE layers 
            SET end_time = CURRENT_TIMESTAMP, 
                status = 'completed',
                quality_score = ?,
                metadata = ?
            WHERE layer_id = ?
        ''', (quality_score, metadata_json, layer_id))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Completed Layer ID {layer_id}")
    
    def store_result(self, layer_id: int, agent_name: str, task_name: str, result: Any) -> str:
        """Store a result from an agent."""
        result_content = json.dumps(result)
        result_hash = hashlib.sha256(result_content.encode()).hexdigest()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO results (layer_id, agent_name, task_name, result_content, result_hash)
            VALUES (?, ?, ?, ?, ?)
        ''', (layer_id, agent_name, task_name, result_content, result_hash))
        
        result_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        print(f"💾 Stored result from {agent_name}: {task_name} (Hash: {result_hash[:8]}...)")
        return result_hash
    
    def add_dependency(self, layer_id: int, depends_on_layer_id: int, dependency_type: str = "results"):
        """Add a dependency between layers."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO dependencies (layer_id, depends_on_layer_id, dependency_type)
            VALUES (?, ?, ?)
        ''', (layer_id, depends_on_layer_id, dependency_type))
        
        conn.commit()
        conn.close()
        
        print(f"🔗 Added dependency: Layer {layer_id} depends on Layer {depends_on_layer_id}")
    
    def check_dependencies(self, layer_id: int) -> bool:
        """Check if all dependencies for a layer are satisfied."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT d.depends_on_layer_id, l.status
            FROM dependencies d
            JOIN layers l ON d.depends_on_layer_id = l.layer_id
            WHERE d.layer_id = ? AND d.satisfied = FALSE
        ''', (layer_id,))
        
        unsatisfied = cursor.fetchall()
        conn.close()
        
        if not unsatisfied:
            return True
        
        # Check if all dependencies are completed
        for dep_layer_id, status in unsatisfied:
            if status != 'completed':
                print(f"⏳ Layer {layer_id} waiting for Layer {dep_layer_id} (status: {status})")
                return False
        
        # Mark dependencies as satisfied
        self.mark_dependencies_satisfied(layer_id)
        return True
    
    def mark_dependencies_satisfied(self, layer_id: int):
        """Mark all dependencies for a layer as satisfied."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE dependencies 
            SET satisfied = TRUE 
            WHERE layer_id = ?
        ''', (layer_id,))
        
        conn.commit()
        conn.close()
        
        print(f"✅ All dependencies satisfied for Layer {layer_id}")
    
    def get_layer_results(self, layer_id: int) -> List[Dict]:
        """Get all results from a specific layer."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT agent_name, task_name, result_content, result_hash, created_at
            FROM results
            WHERE layer_id = ?
            ORDER BY created_at
        ''', (layer_id,))
        
        results = []
        for row in cursor.fetchall():
            agent_name, task_name, result_content, result_hash, created_at = row
            results.append({
                'agent_name': agent_name,
                'task_name': task_name,
                'result': json.loads(result_content),
                'result_hash': result_hash,
                'created_at': created_at
            })
        
        conn.close()
        return results
    
    def get_previous_layer_results(self, current_layer_number: int) -> Dict[int, List[Dict]]:
        """Get results from all previous layers."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT l.layer_id, l.layer_number, l.layer_name, r.agent_name, r.task_name, r.result_content
            FROM layers l
            JOIN results r ON l.layer_id = r.layer_id
            WHERE l.layer_number < ? AND l.status = 'completed'
            ORDER BY l.layer_number, r.created_at
        ''', (current_layer_number,))
        
        layer_results = {}
        for row in cursor.fetchall():
            layer_id, layer_number, layer_name, agent_name, task_name, result_content = row
            
            if layer_number not in layer_results:
                layer_results[layer_number] = {
                    'layer_id': layer_id,
                    'layer_name': layer_name,
                    'results': []
                }
            
            layer_results[layer_number]['results'].append({
                'agent_name': agent_name,
                'task_name': task_name,
                'result': json.loads(result_content)
            })
        
        conn.close()
        return layer_results
    
    def log_agent_access(self, agent_name: str, layer_id: int, operation: str):
        """Log when an agent accesses layer results."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO agent_access (agent_name, layer_id, operation)
            VALUES (?, ?, ?)
        ''', (agent_name, layer_id, operation))
        
        conn.commit()
        conn.close()
    
    def get_system_status(self) -> Dict:
        """Get overall system status."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get layer status
        cursor.execute('''
            SELECT layer_number, layer_name, layer_type, status, quality_score
            FROM layers
            ORDER BY layer_number
        ''')
        
        layers = []
        for row in cursor.fetchall():
            layer_number, layer_name, layer_type, status, quality_score = row
            layers.append({
                'layer_number': layer_number,
                'layer_name': layer_name,
                'layer_type': layer_type,
                'status': status,
                'quality_score': quality_score
            })
        
        # Get dependency status
        cursor.execute('''
            SELECT l1.layer_number, l2.layer_number, d.dependency_type, d.satisfied
            FROM dependencies d
            JOIN layers l1 ON d.layer_id = l1.layer_id
            JOIN layers l2 ON d.depends_on_layer_id = l2.layer_id
        ''')
        
        dependencies = []
        for row in cursor.fetchall():
            from_layer, to_layer, dep_type, satisfied = row
            dependencies.append({
                'from_layer': from_layer,
                'to_layer': to_layer,
                'type': dep_type,
                'satisfied': bool(satisfied)
            })
        
        # Get statistics
        cursor.execute('SELECT COUNT(*) FROM results')
        total_results = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT agent_name) FROM results')
        unique_agents = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'layers': layers,
            'dependencies': dependencies,
            'statistics': {
                'total_results': total_results,
                'unique_agents': unique_agents,
                'completed_layers': len([l for l in layers if l['status'] == 'completed'])
            },
            'timestamp': datetime.now().isoformat()
        }


class AgentMemoryClient:
    """Client for agents to access memory system."""
    
    def __init__(self, agent_name: str, memory_system: HybridMemorySystem):
        self.agent_name = agent_name
        self.memory = memory_system
    
    def get_previous_results(self, current_layer_number: int) -> Dict:
        """Get results from all previous layers."""
        print(f"🔍 Agent '{self.agent_name}' accessing previous layer results...")
        
        previous_results = self.memory.get_previous_layer_results(current_layer_number)
        
        # Log the access
        for layer_number, layer_data in previous_results.items():
            self.memory.log_agent_access(
                self.agent_name, 
                layer_data['layer_id'], 
                f'read_previous_layer_{layer_number}'
            )
        
        print(f"📚 Agent '{self.agent_name}' retrieved {len(previous_results)} previous layers")
        return previous_results
    
    def get_specific_layer_results(self, layer_number: int) -> List[Dict]:
        """Get results from a specific layer."""
        conn = sqlite3.connect(self.memory.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT l.layer_id, l.layer_name
            FROM layers l
            WHERE l.layer_number = ? AND l.status = 'completed'
        ''', (layer_number,))
        
        layer_row = cursor.fetchone()
        if not layer_row:
            print(f"⚠️ Layer {layer_number} not found or not completed")
            conn.close()
            return []
        
        layer_id, layer_name = layer_row
        
        # Get results
        results = self.memory.get_layer_results(layer_id)
        
        # Log access
        self.memory.log_agent_access(
            self.agent_name,
            layer_id,
            f'read_layer_{layer_number}'
        )
        
        conn.close()
        
        print(f"📄 Agent '{self.agent_name}' retrieved {len(results)} results from Layer {layer_number}")
        return results
    
    def store_result(self, layer_id: int, task_name: str, result: Any) -> str:
        """Store a result from this agent."""
        result_hash = self.memory.store_result(layer_id, self.agent_name, task_name, result)
        
        # Log the storage
        self.memory.log_agent_access(
            self.agent_name,
            layer_id,
            f'store_result_{task_name}'
        )
        
        return result_hash


def test_memory_system():
    """Test the memory system."""
    print("🧪 TESTING HYBRID MEMORY SYSTEM")
    print("="*60)
    
    # Initialize memory system
    memory = HybridMemorySystem("test_memory.db")
    
    # Test Layer 1: Parallel Analysis
    print("\n📝 Starting Layer 1: Parallel Analysis")
    layer1_id = memory.start_layer(1, "Parallel Analysis", "parallel")
    
    # Simulate agents storing results
    agent1 = AgentMemoryClient("Technical Analyst", memory)
    agent2 = AgentMemoryClient("UX Analyst", memory)
    
    agent1.store_result(layer1_id, "Technical Analysis", {
        "requirements": ["PDF processing", "AI extraction", "Scalability"],
        "complexity": "high",
        "estimated_time": "2 weeks"
    })
    
    agent2.store_result(layer1_id, "UX Analysis", {
        "user_interface": "web-based",
        "features": ["drag-drop", "preview", "batch processing"],
        "accessibility": "WCAG 2.1 compliant"
    })
    
    memory.complete_layer(layer1_id, 0.92, {"agents": 8, "tasks": 6})
    
    # Test Layer 2: Sequential Design (depends on Layer 1)
    print("\n📝 Starting Layer 2: Sequential Design")
    layer2_id = memory.start_layer(2, "Sequential Design", "sequential")
    
    # Add dependency
    memory.add_dependency(layer2_id, layer1_id, "analysis_results")
    
    # Check dependencies
    print(f"🔍 Checking dependencies for Layer 2...")
    if memory.check_dependencies(layer2_id):
        print("✅ Dependencies satisfied, proceeding with Layer 2")
        
        # Agent in Layer 2 reads previous results
        design_agent = AgentMemoryClient("Architecture Designer", memory)
        previous_results = design_agent.get_previous_results(2)
        
        print(f"📚 Design agent retrieved {len(previous_results)} previous layers")
        
        # Use previous results to inform design
        design_agent.store_result(layer2_id, "System Architecture", {
            "based_on_analysis": list(previous_results.keys()),
            "architecture": "microservices",
            "components": ["API Gateway", "Document Processor", "AI Engine", "Storage Service"],
            "technology_stack": ["Python", "FastAPI", "PostgreSQL", "Redis"]
        })
        
        memory.complete_layer(layer2_id, 0.95, {"agents": 4, "tasks": 4})
    else:
        print("⏳ Waiting for dependencies...")
    
    # Get system status
    print("\n📊 SYSTEM STATUS:")
    status = memory.get_system_status()
    print(f"Layers: {len(status['layers'])}")
    print(f"Dependencies: {len(status['dependencies'])}")
    print(f"Total Results: {status['statistics']['total_results']}")
    print(f"Unique Agents: {status['statistics']['unique_agents']}")
    
    # Print layer details
    print("\n📋 LAYER DETAILS:")
    for layer in status['layers']:
        print(f"  Layer {layer['layer_number']}: {layer['layer_name']}")
        print(f"    Type: {layer['layer_type']}")
        print(f"    Status: {layer['status']}")
        print(f"    Quality: {layer.get('quality_score', 'N/A')}")
    
    print("\n✅ Memory system test completed successfully!")
    return memory


if __name__ == "__main__":
    test_memory_system()