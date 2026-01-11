import json
import os

def remove_agent_description_from_flow(flow_data):
    for node in flow_data.get("data", {}).get("nodes", []):
        if "agent_description" in node.get("data", {}).get("node", {}).get("template", {}):
            del node["data"]["node"]["template"]["agent_description"]
    return flow_data

def process_json_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        modified_data = remove_agent_description_from_flow(data)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(modified_data, f, indent=2)
        print(f"Processed {file_path}")
    except Exception as e:
        print(f"Error processing {file_path}: {e}")

def main():
    file_path = os.path.join(os.path.dirname(__file__), "..", "docs", "docs", "Integrations", "Notion", "Conversational_Notion_Agent.json")
    process_json_file(file_path)

if __name__ == "__main__":
    main()