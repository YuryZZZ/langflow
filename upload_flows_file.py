#!/usr/bin/env python3
"""
Upload flows using the correct /upload/ endpoint with multipart/form-data
"""

import requests
import json
from pathlib import Path
from datetime import datetime

LANGFLOW_URL = "https://langflow-7vd3.onrender.com"
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


def upload_flow(flow_file: Path, session: requests.Session) -> bool:
    """Upload flow using multipart/form-data"""

    try:
        # Read the flow file
        with open(flow_file, "rb") as f:
            flow_content = f.read()

        # Parse to check content
        flow_data = json.loads(flow_content)
        flow_name = flow_data.get("name", flow_file.stem)

        log(f"Uploading: {flow_name}")

        # Prepare multipart form data
        files = {"file": (flow_file.name, flow_content, "application/json")}

        # Upload to the /upload/ endpoint
        response = session.post(f"{LANGFLOW_URL}/api/v1/flows/upload/", files=files, timeout=60)

        if response.status_code in [200, 201]:
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                uploaded_flow = result[0]
                new_id = uploaded_flow.get("id", "unknown")
                nodes = len(uploaded_flow.get("data", {}).get("nodes", []))
                log(f"✅ Uploaded - ID: {new_id}, Nodes: {nodes}")
                return True
            else:
                log(f"✅ Uploaded (response: {type(result).__name__})")
                return True
        else:
            log(f"❌ Upload failed: HTTP {response.status_code}")
            try:
                error = response.json()
                log(f"   Error: {error.get('detail', response.text[:200])}")
            except:
                log(f"   Response: {response.text[:200]}")
            return False

    except Exception as e:
        log(f"❌ Error: {e}")
        return False


def main():
    print("=" * 70)
    print("📤 UPLOAD FLOWS VIA FILE UPLOAD")
    print("=" * 70)
    print(f"Target: {LANGFLOW_URL}")
    print()

    session = requests.Session()

    # Check health
    try:
        r = session.get(f"{LANGFLOW_URL}/health", timeout=10)
        if r.status_code == 200:
            log("✅ Langflow is running")
        else:
            log(f"⚠️ Health check: {r.status_code}")
    except Exception as e:
        log(f"❌ Cannot reach Langflow: {e}", "ERROR")
        return 1

    # Try auto-login by accessing flows
    log("Checking authentication...")
    r = session.get(f"{LANGFLOW_URL}/api/v1/flows", timeout=10)
    if r.status_code == 200:
        log("✅ Auto-login successful")
    elif r.status_code == 401:
        log("❌ Authentication required")
        print("\nPlease login via UI first")
        return 1
    else:
        log(f"⚠️ Auth check: {r.status_code}")

    print()
    print("=" * 70)
    print("📤 UPLOADING FLOWS")
    print("=" * 70)
    print()

    results = {}

    for flow_name in FLOWS:
        flow_path = FLOWS_DIR / flow_name
        if flow_path.exists():
            results[flow_name] = upload_flow(flow_path, session)
        else:
            log(f"⚠️  File not found: {flow_name}")
            results[flow_name] = False

    # Summary
    print()
    print("=" * 70)
    print("📊 RESULTS")
    print("=" * 70)

    success = sum(1 for v in results.values() if v)
    total = len(results)

    print(f"Success: {success}/{total}")
    print()

    for flow_name, ok in results.items():
        status = "✅" if ok else "❌"
        print(f"{status} {flow_name}")

    print()

    if success == total:
        print("🎉 All flows uploaded successfully!")
        print("\nPlease check the Langflow UI - flows should now have")
        print("nodes and edges visible!")
        return 0
    else:
        print(f"⚠️  {total - success} flow(s) failed")
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
