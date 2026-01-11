import json
import sys
import requests
import time
from pathlib import Path

# Configuration
# Using raw string for Windows path to avoid escape character issues
MCP_SETTINGS_PATH = Path(r"C:\Users\yuryz\Documents\MCP\mcp_settings.json")
LANGFLOW_HOST = "http://localhost:7860"

def wait_for_langflow():
    """Waits for Langflow to be available."""
    print("Waiting for Langflow to start...")
    for _ in range(30):
        try:
            response = requests.get(f"{LANGFLOW_HOST}/health")
            if response.status_code == 200:
                print("Langflow is running!")
                return True
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(2)
    print("Timeout waiting for Langflow.")
    return False

def register_servers():
    servers = []

    # 1. Add Render Gateway (Remote)
    servers.append({
        "name": "render-gateway",
        "transport": "sse", # Assuming SSE transport for the gateway
        "url": "https://mcp-gateway-github.onrender.com/sse"
    })

    # 2. Load Local Servers
    if MCP_SETTINGS_PATH.exists():
        try:
            with open(MCP_SETTINGS_PATH, 'r') as f:
                settings = json.load(f)
            local_servers = settings.get("servers", [])
            servers.extend(local_servers)
        except Exception as e:
            print(f"Error reading settings file: {e}")
    else:
        print(f"Warning: Local settings file not found at {MCP_SETTINGS_PATH}")

    print(f"Found {len(servers)} servers to register.")

    for server in servers:
        name = server.get("name")
        if not name:
            print("Skipping server without name.")
            continue

        # The API endpoint to add a server is POST /api/v2/mcp/servers/{server_name}
        url = f"{LANGFLOW_HOST}/api/v2/mcp/servers/{name}"
        
        print(f"Registering '{name}'...")
        try:
            response = requests.post(url, json=server)
            if response.status_code in [200, 201]:
                print(f"✅ Successfully registered '{name}'")
            else:
                print(f"❌ Failed to register '{name}': {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ Error registering '{name}': {e}")

if __name__ == "__main__":
    if wait_for_langflow():
        register_servers()
    else:
        print("Please make sure Langflow is running (python -m langflow run)")
        sys.exit(1)
