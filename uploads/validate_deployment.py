#!/usr/bin/env python3
"""Quick validation script for uploads system"""

import os
import json

print("=" * 60)
print("🧪 UPLOADS SYSTEM - VALIDATION REPORT")
print("=" * 60)
print()

# 1. Directory Structure
print("1. Directory Structure:")
dirs = ["documents", "processed", "failed", "vector_store"]
for dir_name in dirs:
    path = f"uploads/{dir_name}"
    exists = os.path.exists(path)
    status = "✅" if exists else "❌"
    print(f"   {path}: {status}")

print()

# 2. Flow Files
print("2. Langflow Flow Files:")
flow_files = [
    "uploads/FOLDER_UPLOAD_WITH_RAG.json",
    "uploads/FOLDER_UPLOAD_MCP_GATEWAY.json",
    "uploads/FOLDER_UPLOAD_UI_FILE_INPUT.json",
]
for flow_file in flow_files:
    exists = os.path.exists(flow_file)
    if exists:
        try:
            with open(flow_file, "r") as f:
                data = json.load(f)
                name = data.get("name", "Unknown")
                print(f"   {name}: ✅")
        except:
            print(f"   {flow_file}: ⚠️ Invalid JSON")
    else:
        print(f"   {flow_file}: ❌ Missing")

print()

# 3. Core Files
print("3. Core System Files:")
core_files = [
    "uploads/auto_processor.py",
    "uploads/auto_processor_mcp.py",
    "uploads/config.json",
    "uploads/requirements.txt",
    "uploads/start_render_watcher.py",
]
for file in core_files:
    exists = os.path.exists(file)
    if exists:
        size = os.path.getsize(file)
        print(f"   {os.path.basename(file)}: ✅ ({size} bytes)")
    else:
        print(f"   {os.path.basename(file)}: ❌ Missing")

print()

# 4. Documentation
print("4. Documentation:")
docs = [
    "uploads/README.md",
    "uploads/INTEGRATION_GUIDE.md",
    "uploads/RENDER_DEPLOYMENT_GUIDE.md",
    "uploads/UI_FILE_UPLOAD_GUIDE.md",
]
for doc in docs:
    exists = os.path.exists(doc)
    status = "✅" if exists else "❌"
    print(f"   {os.path.basename(doc)}: {status}")

print()

# 5. Config Validation
print("5. Configuration:")
if os.path.exists("uploads/config.json"):
    with open("uploads/config.json", "r") as f:
        config = json.load(f)
    print(f"   Chunk Size: {config.get('chunk_size', 'N/A')}")
    print(f"   Chunk Overlap: {config.get('chunk_overlap', 'N/A')}")
    print(f"   Embedding Model: {config.get('embedding_model', 'N/A')}")
    print(f"   Watch Folder: {config.get('watch_folder', 'N/A')}")
    print("   ✅ Config valid")
else:
    print("   ❌ Config missing")

print()

# Summary
print("=" * 60)
print("📊 VALIDATION SUMMARY")
print("=" * 60)

all_files = dirs + flow_files + core_files + docs
total = len(all_files)
existing = sum(1 for f in all_files if os.path.exists(f))

print(f"Files checked: {total}")
print(f"Files present: {existing}")
print(f"Missing: {total - existing}")
print()

if existing == total:
    print("✅ ALL VALIDATIONS PASSED - READY FOR DEPLOYMENT")
else:
    print(f"⚠️  {total - existing} files missing - check paths")

print("=" * 60)
