import argparse
import json
import sys
import requests
from pathlib import Path

def upload_new_flow(host, api_key, file_path):
    """Uploads a new flow from a JSON file."""
    url = f"{host}/api/v1/flows/upload/"
    headers = {}
    if api_key:
        headers["x-api-key"] = api_key

    file_path = Path(file_path)
    if not file_path.exists():
        print(f"Error: File '{file_path}' not found.")
        sys.exit(1)

    try:
        with open(file_path, 'rb') as f:
            files = {'file': (file_path.name, f, 'application/json')}
            print(f"Uploading {file_path} to {url}...")
            response = requests.post(url, headers=headers, files=files)
            
            if response.status_code == 201:
                data = response.json()
                # The response is a list of created flows
                if isinstance(data, list) and len(data) > 0:
                    flow_id = data[0].get("id")
                    print(f"✅ Flow uploaded successfully! Flow ID: {flow_id}")
                else:
                    print("✅ Flow uploaded successfully!")
            else:
                print(f"❌ Error {response.status_code}: {response.text}")
                sys.exit(1)
    except Exception as e:
        print(f"❌ An error occurred: {str(e)}")
        sys.exit(1)

def update_existing_flow(host, api_key, flow_id, file_path):
    """Updates an existing flow using data from a JSON file."""
    url = f"{host}/api/v1/flows/{flow_id}"
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["x-api-key"] = api_key

    file_path = Path(file_path)
    if not file_path.exists():
        print(f"Error: File '{file_path}' not found.")
        sys.exit(1)

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            flow_data = json.load(f)
        
        # Extract relevant fields for update
        payload = {
            "name": flow_data.get("name"),
            "description": flow_data.get("description"),
            "data": flow_data.get("data"),
            "endpoint_name": flow_data.get("endpoint_name")
        }
        
        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}

        print(f"Updating flow {flow_id} at {url}...")
        response = requests.patch(url, headers=headers, json=payload)

        if response.status_code == 200:
            print(f"✅ Flow '{flow_id}' updated successfully!")
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            sys.exit(1)

    except Exception as e:
        print(f"❌ An error occurred: {str(e)}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Upload or Update Langflow Flows to Render")
    parser.add_argument("--host", required=True, help="Base URL of your Langflow instance (e.g., https://my-app.onrender.com)")
    parser.add_argument("--file", required=True, help="Path to the local flow JSON file")
    parser.add_argument("--api-key", help="Langflow API Key (if authentication is enabled)")
    parser.add_argument("--flow-id", help="ID of the flow to update. If not provided, a NEW flow will be created.")

    args = parser.parse_args()

    # Ensure host doesn't have trailing slash
    host = args.host.rstrip('/')

    if args.flow_id:
        update_existing_flow(host, args.api_key, args.flow_id, args.file)
    else:
        upload_new_flow(host, args.api_key, args.file)

if __name__ == "__main__":
    main()
