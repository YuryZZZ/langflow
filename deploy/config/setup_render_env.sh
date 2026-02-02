#!/bin/bash
# Render.com Environment Variables Setup Script
# Generated from generate_render_env_config.py

echo "================================================"
echo "Render.com Environment Variables Setup"
echo "================================================"
echo ""
echo "Copy and paste the following commands into Render.com dashboard:"
echo ""
echo "1. Go to your web service on Render.com"
echo "2. Click on 'Environment'"
echo "3. Add the following environment variables:"
echo ""

# Group variables by category
categories = {
    "Core Langflow Configuration": [],
    "MCP Configuration": [],
    "PostgreSQL TaskBus": [],
    "API Keys (REQUIRED)": [],
    "Deployment Configuration": []
}

# Categorize variables
for key, value in config.items():
    if key.startswith("LANGFLOW_"):
        categories["Core Langflow Configuration"].append((key, value))
    elif key.startswith("OPENCODE_") or key.startswith("MCP_"):
        categories["MCP Configuration"].append((key, value))
    elif key.startswith("POSTGRES_"):
        categories["PostgreSQL TaskBus"].append((key, value))
    elif "API" in key or "KEY" in key or "TOKEN" in key:
        categories["API Keys (REQUIRED)"].append((key, value))
    else:
        categories["Deployment Configuration"].append((key, value))

# Generate the script
for category, variables in categories.items():
    if variables:
        print(f"
# {category}")
        print("#" * 50)
        for key, value_info in variables:
            desc = value_info.get('description', '')
            val = value_info.get('value', '')
            required = value_info.get('required', False)
            
            if required and not val:
                print(f"# [REQUIRED] {desc}")
                print(f"# Key: {key}")
                print(f"# Value: [YOUR_{key}_HERE]")
                print("# ---")
            else:
                print(f"# {desc}")
                print(f"# Key: {key}")
                print(f"# Value: {val}")
                print("# ---")

print("")
print("================================================")
print("Important Notes:")
print("================================================")
print("1. For PostgreSQL variables (POSTGRES_*):")
print("   - Render will automatically set these when you link a PostgreSQL database")
print("   - Create a PostgreSQL database named 'opencode_taskbus'")
print("   - Link it to your web service")
print("")
print("2. For API Keys:")
print("   - Get keys from respective provider dashboards")
print("   - Never commit API keys to git")
print("   - Set sync: false for all API keys")
print("")
print("3. After setting variables:")
print("   - Save changes")
print("   - Redeploy the service")
print("   - Check logs for any configuration errors")
print("================================================")
