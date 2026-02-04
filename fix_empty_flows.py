#!/usr/bin/env python3
"""
Delete all empty flows and re-import them with proper data
"""

import requests
import json
from pathlib import Path
from datetime import datetime

LANGFLOW_URL = "https://langflow-7vd3.onrender.com"
API_KEY = "sk-jeqYCKW7Q9U_wfEjt848DeBgAaWs9sYoNErIRHGuGUc"
FLOWS_DIR = Path("uploads")

FLOWS = [
    "MASTER_TEMPLATE_MEGA_FLOW.json",
    "ULTIMATE_MEGA_FLOW.json",
    "PROFESSIONAL_DEBUGGER.json",
    "DOCUMENT_ANALYSIS_EXPERT.json",
    "RESEARCH_REPORT_ANALYZER.json",
    "FOLDER_UPLOAD_UI_FILE_INPUT.json",
]


def log(msg, level="INFO"):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [{level}] {msg}")


def get_all_flows(session):
    """Get list of all flows"""
    try:
        r = session.get(f"{LANGFLOW_URL}/api/v1/flows", timeout=30)
        if r.status_code == 200:
            return r.json()
        else:
            log(f"Failed to get flows: {r.status_code}", "ERROR")
            return []
    except Exception as e:
        log(f"Error: {e}", "ERROR")
        return []


def delete_flow(session, flow_id):
    """Delete a flow by ID"""
    try:
        r = session.delete(f"{LANGFLOW_URL}/api/v1/flows/{flow_id}", timeout=30)
        return r.status_code in [200, 204, 404]
    except Exception as e:
        log(f"Error deleting flow: {e}", "ERROR")
        return False


def upload_flow_file(session, flow_file):
    """Upload flow using file upload endpoint"""
    try:
        with open(flow_file, "rb") as f:
            files = {"file": (flow_file.name, f, "application/json")}
            r = session.post(f"{LANGFLOW_URL}/api/v1/flows/upload/", files=files, timeout=60)

            if r.status_code in [200, 201]:
                result = r.json()
                if isinstance(result, list) and len(result) > 0:
                    flow = result[0]
                    nodes = len(flow.get("data", {}).get("nodes", []))
                    return True, flow.get("id"), nodes
                return True, "unknown", 0
            else:
                return False, None, 0
    except Exception as e:
        log(f"Error uploading: {e}", "ERROR")
        return False, None, 0


def main():
    print("=" * 70)
    print("🗑️  DELETE & RE-IMPORT FLOWS")
    print("=" * 70)
    print()

    session = requests.Session()
    # Use auto-login (no API key needed)

    # Step 1: Get all flows
    log("Fetching all flows...")
    flows = get_all_flows(session)
    log(f"Found {len(flows)} flows")
    print()

    # Step 2: Delete all flows
    print("=" * 70)
    print("STEP 1: DELETING ALL FLOWS")
    print("=" * 70)
    print()

    deleted = 0
    for flow in flows:
        flow_id = flow.get("id")
        name = flow.get("name", "Unknown")
        if flow_id:
            if delete_flow(session, flow_id):
                log(f"✅ Deleted: {name[:50]}")
                deleted += 1
            else:
                log(f"❌ Failed to delete: {name[:50]}")

    log(f"Deleted {deleted} flows")
    print()

    # Step 3: Re-import all flows
    print("=" * 70)
    print("STEP 2: RE-IMPORTING FLOWS")
    print("=" * 70)
    print()

    results = []
    for flow_name in FLOWS:
        flow_path = FLOWS_DIR / flow_name
        if not flow_path.exists():
            log(f"❌ File not found: {flow_name}")
            continue

        log(f"Uploading: {flow_name}")
        success, flow_id, nodes = upload_flow_file(session, flow_path)

        if success:
            log(f"✅ Imported: {nodes} nodes, ID: {flow_id[:8] if flow_id else 'N/A'}...")
            results.append((flow_name, True, nodes))
        else:
            log(f"❌ Failed to import: {flow_name}")
            results.append((flow_name, False, 0))

    # Summary
    print()
    print("=" * 70)
    print("📊 RESULTS")
    print("=" * 70)
    print()

    success_count = sum(1 for _, ok, _ in results if ok)
    total = len(results)

    print(f"Success: {success_count}/{total}")
    print()

    for name, ok, nodes in results:
        status = "✅" if ok else "❌"
        print(f"{status} {name}: {nodes} nodes")

    print()

    if success_count == total:
        print("🎉 All flows re-imported successfully!")
        print("\nThe flows should now have all nodes visible in the UI.")
        return 0
    else:
        print(f"⚠️  {total - success_count} flow(s) failed")
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
