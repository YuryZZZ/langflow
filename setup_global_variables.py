#!/usr/bin/env python3
"""
Create/update Langflow global variables via API
Uses API key for authentication
"""

import requests
import json
import os
from datetime import datetime

LANGFLOW_URL = "https://langflow-7vd3.onrender.com"
API_KEY = os.getenv("LANGFLOW_API_KEY", "")

# Global variables to set (API keys loaded from environment)
# Set these environment variables before running:
# export MOONSHOT_API_KEY="your-key"
# export GOOGLE_API_KEY="your-key"
# etc.
GLOBAL_VARS = {
    "MOONSHOT_API_KEY": os.getenv("MOONSHOT_API_KEY", ""),
    "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY", ""),
    "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY", ""),
    "ZAI_API_KEY": os.getenv("ZAI_API_KEY", ""),
    "DEEPSEEK_API_KEY": os.getenv("DEEPSEEK_API_KEY", ""),
    "PERPLEXITY_API_KEY": os.getenv("PERPLEXITY_API_KEY", ""),
    "GROQ_API_KEY": os.getenv("GROQ_API_KEY", ""),
    "ENABLE_INTERNET_SEARCH": "true",
    "RESEARCH_CITATIONS": "true",
    "REAL_TIME_SEARCH": "true",
}


def log(msg, level="INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [{level}] {msg}")


def get_existing_variables(session):
    """Get list of existing variables"""
    try:
        response = session.get(f"{LANGFLOW_URL}/api/v1/variables/", timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            log(f"Failed to get variables: {response.status_code}", "ERROR")
            return []
    except Exception as e:
        log(f"Error getting variables: {e}", "ERROR")
        return []


def create_variable(session, name, value, var_type="Credential"):
    """Create a new variable"""
    try:
        payload = {"name": name, "value": value, "type": var_type, "default_fields": []}

        response = session.post(f"{LANGFLOW_URL}/api/v1/variables/", json=payload, timeout=30)

        if response.status_code in [200, 201]:
            return True, "Created"
        elif response.status_code == 400:
            error_detail = response.json().get("detail", "")
            if "already exists" in error_detail.lower():
                return False, "Exists"
            else:
                return False, f"Error: {error_detail}"
        else:
            return False, f"HTTP {response.status_code}"
    except Exception as e:
        return False, f"Exception: {e}"


def update_variable(session, variable_id, value):
    """Update existing variable"""
    try:
        payload = {"id": str(variable_id), "value": value}

        response = session.patch(f"{LANGFLOW_URL}/api/v1/variables/{variable_id}", json=payload, timeout=30)

        if response.status_code in [200, 204]:
            return True, "Updated"
        else:
            return False, f"HTTP {response.status_code}"
    except Exception as e:
        return False, f"Exception: {e}"


def delete_variable(session, variable_id):
    """Delete a variable"""
    try:
        response = session.delete(f"{LANGFLOW_URL}/api/v1/variables/{variable_id}", timeout=30)

        if response.status_code in [200, 204]:
            return True
        else:
            return False
    except Exception as e:
        log(f"Error deleting variable: {e}", "ERROR")
        return False


def configure_all_variables():
    """Configure all global variables"""
    print("=" * 70)
    print("🔧 CONFIGURING LANGFLOW GLOBAL VARIABLES")
    print("=" * 70)
    print(f"Target: {LANGFLOW_URL}")
    print(f"Variables to configure: {len(GLOBAL_VARS)}")
    print()

    # Create session with API key
    session = requests.Session()
    session.headers.update(
        {"Content-Type": "application/json", "Accept": "application/json", "Authorization": f"Bearer {API_KEY}"}
    )

    # Check if API key works
    log("Testing API authentication...")
    test_response = session.get(f"{LANGFLOW_URL}/api/v1/variables/", timeout=10)
    if test_response.status_code == 401:
        log("❌ API key authentication failed", "ERROR")
        print("\nThe API key may not have permission to access variables.")
        print("Trying with auto-login session instead...")
        session.headers.pop("Authorization", None)
    elif test_response.status_code == 200:
        log("✅ API key authenticated successfully")
    else:
        log(f"⚠️  Unexpected response: {test_response.status_code}")
        session.headers.pop("Authorization", None)

    # Get existing variables
    log("Fetching existing variables...")
    existing_vars = get_existing_variables(session)
    existing_map = {var.get("name"): var for var in existing_vars}
    log(f"Found {len(existing_vars)} existing variables")
    print()

    # Configure each variable
    results = {}

    print("=" * 70)
    print("SETTING VARIABLES")
    print("=" * 70)
    print()

    for var_name, var_value in GLOBAL_VARS.items():
        # Determine type based on variable name
        if "API_KEY" in var_name or "TOKEN" in var_name:
            var_type = "Credential"
        else:
            var_type = "Generic"

        log(f"Processing: {var_name} (type: {var_type})")

        if var_name in existing_map:
            # Update existing
            var_id = existing_map[var_name].get("id")
            log(f"  Variable exists (ID: {var_id}), updating...")
            success, msg = update_variable(session, var_id, var_value)
            if success:
                log(f"  ✅ Updated successfully")
                results[var_name] = "Updated"
            else:
                log(f"  ❌ Update failed: {msg}")
                results[var_name] = f"Failed: {msg}"
        else:
            # Create new
            log(f"  Creating new variable...")
            success, msg = create_variable(session, var_name, var_value, var_type)
            if success:
                log(f"  ✅ Created successfully")
                results[var_name] = "Created"
            elif msg == "Exists":
                log(f"  ⚠️  Variable already exists (may be permission issue)")
                results[var_name] = "Already exists"
            else:
                log(f"  ❌ Creation failed: {msg}")
                results[var_name] = f"Failed: {msg}"

    # Summary
    print()
    print("=" * 70)
    print("📊 RESULTS SUMMARY")
    print("=" * 70)
    print()

    success_count = sum(1 for v in results.values() if v in ["Created", "Updated"])
    total_count = len(results)

    print(f"Success: {success_count}/{total_count}")
    print()

    for var_name, status in results.items():
        if status in ["Created", "Updated"]:
            icon = "✅"
        elif status == "Already exists":
            icon = "⚠️"
        else:
            icon = "❌"
        print(f"{icon} {var_name}: {status}")

    print()

    if success_count == total_count:
        print("🎉 All global variables configured successfully!")
        print("\nThe flows should now work with all API keys.")
        return 0
    else:
        print(f"⚠️  {total_count - success_count} variable(s) failed")
        print("\nYou may need to manually configure failed variables via UI:")
        print(f"  {LANGFLOW_URL}/settings/global-variables")
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(configure_all_variables())
