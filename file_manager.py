#!/usr/bin/env python3
"""
File Manager for Dynamic Flows
Handles file uploads and makes them available to all agents via MCP
"""

import os
import json
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import hashlib

class FlowFileManager:
    """
    Manages file uploads for dynamic flows.
    Makes files available to all agents via shared storage.
    """
    
    def __init__(self, flows_dir: str = "agent/workflows/dynamic"):
        self.flows_dir = Path(flows_dir)
        self.files_dir = Path("uploads")
        self.files_dir.mkdir(exist_ok=True)
        
        # Shared file registry
        self.registry_file = self.files_dir / "file_registry.json"
        self.registry = self._load_registry()
    
    def _load_registry(self) -> Dict:
        """Load file registry"""
        if self.registry_file.exists():
            with open(self.registry_file, 'r') as f:
                return json.load(f)
        return {"files": {}, "flow_files": {}}
    
    def _save_registry(self):
        """Save file registry"""
        with open(self.registry_file, 'w') as f:
            json.dump(self.registry, f, indent=2)
    
    def upload_file(self, file_path: str, flow_id: str = None, 
                   description: str = "") -> Dict[str, Any]:
        """
        Upload a file and make it available to flow agents.
        
        Args:
            file_path: Path to file to upload
            flow_id: Optional flow ID to associate with
            description: File description
        
        Returns:
            File metadata including access URL
        """
        source = Path(file_path)
        if not source.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Generate file ID
        file_id = hashlib.md5(f"{source}{datetime.now()}".encode()).hexdigest()[:12]
        
        # Create file entry
        file_entry = {
            "file_id": file_id,
            "original_name": source.name,
            "size": source.stat().st_size,
            "type": source.suffix.lower(),
            "uploaded_at": datetime.now().isoformat(),
            "description": description,
            "flow_ids": [flow_id] if flow_id else [],
            "access_path": f"uploads/{file_id}_{source.name}"
        }
        
        # Copy file to uploads directory
        dest = self.files_dir / f"{file_id}_{source.name}"
        shutil.copy2(source, dest)
        
        # Update registry
        self.registry["files"][file_id] = file_entry
        
        if flow_id:
            if flow_id not in self.registry["flow_files"]:
                self.registry["flow_files"][flow_id] = []
            self.registry["flow_files"][flow_id].append(file_id)
        
        self._save_registry()
        
        print(f"✅ File uploaded: {source.name}")
        print(f"   File ID: {file_id}")
        print(f"   Size: {file_entry['size']} bytes")
        print(f"   Access: {file_entry['access_path']}")
        
        return file_entry
    
    def get_flow_files(self, flow_id: str) -> List[Dict]:
        """
        Get all files associated with a flow.
        
        Args:
            flow_id: Flow ID
        
        Returns:
            List of file metadata
        """
        file_ids = self.registry["flow_files"].get(flow_id, [])
        return [self.registry["files"][fid] for fid in file_ids if fid in self.registry["files"]]
    
    def share_file_with_flow(self, file_id: str, flow_id: str):
        """
        Share an existing file with a new flow.
        
        Args:
            file_id: File ID to share
            flow_id: Flow ID to share with
        """
        if file_id not in self.registry["files"]:
            raise ValueError(f"File not found: {file_id}")
        
        if flow_id not in self.registry["flow_files"]:
            self.registry["flow_files"][flow_id] = []
        
        if file_id not in self.registry["flow_files"][flow_id]:
            self.registry["flow_files"][flow_id].append(file_id)
            self.registry["files"][file_id]["flow_ids"].append(flow_id)
            self._save_registry()
            print(f"✅ File {file_id} shared with flow {flow_id}")
    
    def get_file_content(self, file_id: str) -> Optional[str]:
        """
        Get file content as string.
        
        Args:
            file_id: File ID
        
        Returns:
            File content or None if not found
        """
        if file_id not in self.registry["files"]:
            return None
        
        file_info = self.registry["files"][file_id]
        file_path = Path(file_info["access_path"])
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Binary file
            return f"[Binary file: {file_info['original_name']}]"
    
    def create_file_for_flow(self, content: str, filename: str, 
                            flow_id: str, description: str = "") -> Dict:
        """
        Create a new file programmatically for a flow.
        
        Args:
            content: File content
            filename: Desired filename
            flow_id: Flow ID
            description: File description
        
        Returns:
            File metadata
        """
        # Generate file ID
        file_id = hashlib.md5(f"{filename}{datetime.now()}".encode()).hexdigest()[:12]
        
        # Save file
        dest = self.files_dir / f"{file_id}_{filename}"
        with open(dest, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Create entry
        file_entry = {
            "file_id": file_id,
            "original_name": filename,
            "size": dest.stat().st_size,
            "type": Path(filename).suffix.lower(),
            "uploaded_at": datetime.now().isoformat(),
            "description": description,
            "flow_ids": [flow_id],
            "access_path": str(dest)
        }
        
        # Update registry
        self.registry["files"][file_id] = file_entry
        
        if flow_id not in self.registry["flow_files"]:
            self.registry["flow_files"][flow_id] = []
        self.registry["flow_files"][flow_id].append(file_id)
        
        self._save_registry()
        
        return file_entry
    
    def list_all_files(self) -> Dict[str, List[Dict]]:
        """List all uploaded files grouped by flow"""
        result = {}
        for flow_id, file_ids in self.registry["flow_files"].items():
            result[flow_id] = [self.registry["files"][fid] for fid in file_ids if fid in self.registry["files"]]
        return result
    
    def delete_file(self, file_id: str):
        """Delete a file and remove from registry"""
        if file_id not in self.registry["files"]:
            return
        
        file_info = self.registry["files"][file_id]
        file_path = Path(file_info["access_path"])
        
        # Remove file
        if file_path.exists():
            file_path.unlink()
        
        # Remove from flow associations
        for flow_id in file_info.get("flow_ids", []):
            if flow_id in self.registry["flow_files"]:
                if file_id in self.registry["flow_files"][flow_id]:
                    self.registry["flow_files"][flow_id].remove(file_id)
        
        # Remove from registry
        del self.registry["files"][file_id]
        self._save_registry()
        
        print(f"✅ File deleted: {file_id}")


# Integration with Dynamic Flow Generator
def add_file_support_to_flow(flow_data: Dict, file_manager: FlowFileManager, 
                             flow_id: str) -> Dict:
    """
    Add file upload/read components to a flow.
    
    Args:
        flow_data: Flow configuration
        file_manager: File manager instance
        flow_id: Flow ID
    
    Returns:
        Updated flow with file components
    """
    # Get files for this flow
    flow_files = file_manager.get_flow_files(flow_id)
    
    if not flow_files:
        return flow_data
    
    # Add file input component
    file_component = {
        "id": "file_input",
        "type": "FileInput",
        "name": "Shared Files",
        "description": "Files available to all agents",
        "config": {
            "files": flow_files,
            "shared_access": True,
            "auto_distribute": True
        },
        "position": {"x": 50, "y": 100}
    }
    
    # Add to components
    flow_data["components"].insert(0, file_component)
    
    # Connect to all agents
    for component in flow_data["components"]:
        if component["id"] != "file_input" and component.get("type") == "Agent":
            flow_data["edges"].append({
                "source": "file_input",
                "target": component["id"],
                "type": "provides_files"
            })
    
    return flow_data


if __name__ == "__main__":
    # Example usage
    manager = FlowFileManager()
    
    print("📁 Flow File Manager")
    print("="*50)
    
    # List all files
    files = manager.list_all_files()
    print(f"\nFiles by flow:")
    for flow_id, flow_files in files.items():
        print(f"\n  Flow {flow_id}:")
        for f in flow_files:
            print(f"    - {f['original_name']} ({f['size']} bytes)")
