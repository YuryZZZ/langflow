#!/usr/bin/env python3
"""
MCP Output Manager - Prevents Truncation of Large Research Outputs
Stores comprehensive replies in MCP memory with chunking support
"""

import json
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

class MCPOutputManager:
    """
    Manages large outputs to prevent truncation.
    Stores comprehensive research results in MCP with automatic chunking.
    """
    
    def __init__(self, mcp_client=None):
        self.mcp_client = mcp_client
        self.chunk_size = 8000  # Safe chunk size for most models
        self.storage_dir = Path("outputs")
        self.storage_dir.mkdir(exist_ok=True)
        
    def store_comprehensive_output(self, 
                                   task_id: str, 
                                   agent_id: str, 
                                   content: str,
                                   metadata: Dict = None) -> Dict[str, Any]:
        """
        Store large output without truncation.
        Automatically chunks and stores in MCP + local filesystem.
        
        Args:
            task_id: Unique task identifier
            agent_id: Agent that generated the output
            content: The full comprehensive output
            metadata: Additional context
            
        Returns:
            Storage metadata with access information
        """
        timestamp = datetime.now().isoformat()
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        
        # Calculate chunks needed
        total_length = len(content)
        num_chunks = (total_length + self.chunk_size - 1) // self.chunk_size
        
        print(f"📦 Storing comprehensive output: {total_length:,} chars")
        print(f"   Chunks: {num_chunks} (chunk size: {self.chunk_size:,})")
        
        # Split into chunks
        chunks = []
        for i in range(num_chunks):
            start = i * self.chunk_size
            end = min(start + self.chunk_size, total_length)
            chunk_content = content[start:end]
            
            chunk_data = {
                "chunk_id": i + 1,
                "total_chunks": num_chunks,
                "task_id": task_id,
                "agent_id": agent_id,
                "content": chunk_content,
                "byte_start": start,
                "byte_end": end,
                "timestamp": timestamp,
                "content_hash": content_hash
            }
            chunks.append(chunk_data)
        
        # Store metadata
        storage_meta = {
            "task_id": task_id,
            "agent_id": agent_id,
            "timestamp": timestamp,
            "content_hash": content_hash,
            "total_length": total_length,
            "num_chunks": num_chunks,
            "chunk_size": self.chunk_size,
            "metadata": metadata or {},
            "chunks": [{"chunk_id": c["chunk_id"], 
                       "byte_start": c["byte_start"], 
                       "byte_end": c["byte_end"]} for c in chunks]
        }
        
        # Save to filesystem (primary storage)
        output_file = self.storage_dir / f"{task_id}_{agent_id}_{content_hash}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "metadata": storage_meta,
                "chunks": chunks
            }, f, indent=2)
        
        print(f"   ✓ Saved to: {output_file}")
        
        # Store in MCP (if available)
        if self.mcp_client:
            try:
                # Store metadata in MCP
                self.mcp_client.send_to_memory(
                    layer_id=0,
                    agent_name="output_manager",
                    task_name=f"meta_{task_id}",
                    data={
                        "type": "output_metadata",
                        "task_id": task_id,
                        "agent_id": agent_id,
                        "content_hash": content_hash,
                        "file_path": str(output_file),
                        "total_length": total_length,
                        "num_chunks": num_chunks
                    }
                )
                
                # Store chunk references
                for i, chunk in enumerate(chunks):
                    self.mcp_client.send_to_memory(
                        layer_id=0,
                        agent_name="output_manager",
                        task_name=f"chunk_{task_id}_{i+1}",
                        data=chunk
                    )
                
                print(f"   ✓ Synced to MCP memory")
                storage_meta["mcp_synced"] = True
                
            except Exception as e:
                print(f"   ⚠️  MCP sync failed: {e}")
                storage_meta["mcp_synced"] = False
        
        return storage_meta
    
    def retrieve_comprehensive_output(self, task_id: str, 
                                     agent_id: str = None) -> Optional[str]:
        """
        Retrieve full output without truncation.
        Reconstructs from chunks if needed.
        
        Args:
            task_id: Task identifier
            agent_id: Optional agent filter
            
        Returns:
            Full content or None if not found
        """
        # Find files matching task_id
        pattern = f"{task_id}_*.json"
        files = list(self.storage_dir.glob(pattern))
        
        if not files:
            # Try MCP
            if self.mcp_client:
                try:
                    result = self.mcp_client.get_from_memory(agent_name="output_manager")
                    if result.get("status") == "success":
                        # Find metadata entry
                        for item in result.get("data", []):
                            if item.get("task_id") == task_id:
                                file_path = item.get("file_path")
                                if file_path and Path(file_path).exists():
                                    files = [Path(file_path)]
                                    break
                except:
                    pass
        
        if not files:
            return None
        
        # Load and reconstruct
        output_file = files[0]  # Take first match
        
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            chunks = data.get("chunks", [])
            if not chunks:
                return None
            
            # Sort chunks by ID and reconstruct
            chunks.sort(key=lambda x: x["chunk_id"])
            full_content = "".join(chunk["content"] for chunk in chunks)
            
            print(f"📖 Retrieved: {len(full_content):,} chars from {len(chunks)} chunks")
            return full_content
            
        except Exception as e:
            print(f"❌ Error retrieving output: {e}")
            return None
    
    def get_output_summary(self, task_id: str) -> Optional[Dict]:
        """Get summary of stored output without loading full content"""
        pattern = f"{task_id}_*.json"
        files = list(self.storage_dir.glob(pattern))
        
        if not files:
            return None
        
        try:
            with open(files[0], 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            meta = data.get("metadata", {})
            return {
                "task_id": meta.get("task_id"),
                "agent_id": meta.get("agent_id"),
                "timestamp": meta.get("timestamp"),
                "total_length": meta.get("total_length"),
                "num_chunks": meta.get("num_chunks"),
                "file_path": str(files[0])
            }
        except:
            return None
    
    def list_all_outputs(self) -> List[Dict]:
        """List all stored outputs with summaries"""
        outputs = []
        
        for file in self.storage_dir.glob("*.json"):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                meta = data.get("metadata", {})
                outputs.append({
                    "task_id": meta.get("task_id"),
                    "agent_id": meta.get("agent_id"),
                    "timestamp": meta.get("timestamp"),
                    "total_length": meta.get("total_length"),
                    "file_path": str(file)
                })
            except:
                continue
        
        # Sort by timestamp (newest first)
        outputs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return outputs


# Integration with Dynamic Flow Generator
class ComprehensiveOutputHandler:
    """
    Handles comprehensive outputs in dynamic flows.
    Ensures no truncation regardless of output size.
    """
    
    def __init__(self, mcp_client=None):
        self.output_manager = MCPOutputManager(mcp_client)
    
    def process_agent_output(self, task_id: str, agent_id: str, 
                            content: str, context: Dict = None) -> Dict:
        """
        Process and store agent output comprehensively.
        
        Returns:
            Storage metadata and access info
        """
        # Store comprehensive output
        storage_meta = self.output_manager.store_comprehensive_output(
            task_id=task_id,
            agent_id=agent_id,
            content=content,
            metadata=context
        )
        
        # Return summary for flow (not full content to avoid truncation)
        return {
            "status": "stored",
            "task_id": task_id,
            "agent_id": agent_id,
            "content_length": len(content),
            "num_chunks": storage_meta["num_chunks"],
            "storage_path": storage_meta["chunks"][0].get("file_path", ""),
            "access_method": "retrieve_comprehensive_output",
            "summary": content[:500] + "..." if len(content) > 500 else content
        }
    
    def get_full_output(self, task_id: str) -> str:
        """Retrieve complete output without truncation"""
        return self.output_manager.retrieve_comprehensive_output(task_id) or ""
    
    def generate_output_report(self, flow_id: str) -> Dict:
        """Generate report of all outputs in a flow"""
        all_outputs = self.output_manager.list_all_outputs()
        
        # Filter by flow_id pattern
        flow_outputs = [o for o in all_outputs if flow_id in o.get("task_id", "")]
        
        total_chars = sum(o.get("total_length", 0) for o in flow_outputs)
        
        return {
            "flow_id": flow_id,
            "total_outputs": len(flow_outputs),
            "total_characters": total_chars,
            "outputs": flow_outputs,
            "storage_location": str(self.output_manager.storage_dir)
        }


# Usage example
if __name__ == "__main__":
    print("📦 MCP Output Manager - Prevents Truncation")
    print("=" * 50)
    
    manager = MCPOutputManager()
    
    # Example: Store large research output
    large_content = """
    # Comprehensive Research Report
    
    ## Executive Summary
    [Very long content here...]
    
    ## Detailed Analysis
    [Thousands of words of research...]
    
    ## Conclusions
    [Comprehensive conclusions...]
    """ * 100  # Simulate very large output
    
    # Store
    meta = manager.store_comprehensive_output(
        task_id="research_001",
        agent_id="researcher",
        content=large_content,
        metadata={"topic": "AI Research", "depth": "comprehensive"}
    )
    
    print(f"\n✅ Stored: {meta['total_length']:,} characters")
    print(f"   Chunks: {meta['num_chunks']}")
    
    # Retrieve
    retrieved = manager.retrieve_comprehensive_output("research_001")
    print(f"\n✅ Retrieved: {len(retrieved):,} characters")
    print(f"   Match: {retrieved == large_content}")
