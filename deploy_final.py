#!/usr/bin/env python3
"""
Langflow Deployment via API with Session Auth
Supports multiple authentication methods
"""

import json
import requests
from pathlib import Path
from datetime import datetime
import sys
import os

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


class LangflowDeployer:
    def __init__(self, base_url: str = LANGFLOW_URL):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json", "Accept": "application/json"})

    def check_health(self) -> bool:
        """Check if Langflow is running"""
        try:
            r = self.session.get(f"{self.base_url}/health", timeout=10)
            return r.status_code == 200
        except Exception as e:
            log(f"Health check failed: {e}", "ERROR")
            return False

    def try_auto_login(self) -> bool:
        """Try auto-login if enabled"""
        try:
            # Try to get flows without auth (auto-login)
            r = self.session.get(f"{self.base_url}/api/v1/flows", timeout=10)
            if r.status_code == 200:
                log("Auto-login successful")
                return True
            elif r.status_code == 401:
                log("Authentication required")
                return False
            else:
                log(f"Unexpected status: {r.status_code}")
                return False
        except Exception as e:
            log(f"Auto-login check failed: {e}", "ERROR")
            return False

    def login_with_credentials(self, username: str, password: str) -> bool:
        """Login with username/password"""
        try:
            r = self.session.post(
                f"{self.base_url}/api/v1/login", json={"username": username, "password": password}, timeout=30
            )
            if r.status_code == 200:
                log("Login successful")
                # Session cookie should be set automatically
                return True
            else:
                log(f"Login failed: HTTP {r.status_code}")
                return False
        except Exception as e:
            log(f"Login error: {e}", "ERROR")
            return False

    def deploy_flow(self, flow_file: Path) -> bool:
        """Deploy a single flow"""
        try:
            with open(flow_file, "r", encoding="utf-8") as f:
                flow_data = json.load(f)

            flow_name = flow_data.get("name", flow_file.stem)
            log(f"Deploying: {flow_name}")

            # Try to create flow
            r = self.session.post(f"{self.base_url}/api/v1/flows/", json=flow_data, timeout=60)

            if r.status_code in [200, 201]:
                result = r.json()
                log(f"✅ Success - ID: {result.get('id', 'unknown')}")
                return True
            elif r.status_code == 401:
                log(f"❌ Authentication required (401)")
                return False
            elif r.status_code == 403:
                log(f"❌ Forbidden (403) - Check permissions")
                return False
            elif r.status_code == 422:
                log(f"❌ Validation error (422)")
                try:
                    error_detail = r.json()
                    log(f"   Details: {error_detail.get('detail', 'Unknown')}")
                except:
                    pass
                return False
            else:
                log(f"❌ HTTP {r.status_code}")
                return False

        except Exception as e:
            log(f"❌ Error: {e}")
            return False

    def deploy_all(self, auth_method: str = "auto") -> dict:
        """Deploy all flows"""
        print("=" * 70)
        print("🚀 LANGFLOW DEPLOYMENT")
        print("=" * 70)
        print(f"Target: {self.base_url}")
        print(f"Auth Method: {auth_method}")
        print("")

        # Check health
        if not self.check_health():
            log("Langflow instance not reachable", "ERROR")
            return {}

        log("✅ Langflow is running")

        # Try authentication
        auth_success = False

        if auth_method == "auto":
            auth_success = self.try_auto_login()
        elif auth_method == "credentials":
            username = os.getenv("LANGFLOW_USERNAME", "admin")
            password = os.getenv("LANGFLOW_PASSWORD", "langflow_admin_2024")
            auth_success = self.login_with_credentials(username, password)
        elif auth_method == "api_key":
            api_key = os.getenv("LANGFLOW_API_KEY", "")
            if api_key:
                self.session.headers.update({"Authorization": f"Bearer {api_key}"})
                auth_success = self.try_auto_login()  # Test the key

        if not auth_success:
            log("Authentication failed or required", "ERROR")
            print("\n" + "=" * 70)
            print("📋 MANUAL DEPLOYMENT REQUIRED")
            print("=" * 70)
            print("\nSince programmatic deployment requires authentication,")
            print("please use one of these methods:\n")
            print("Method 1: Manual Import (Easiest)")
            print("  1. Visit:", self.base_url)
            print("  2. Login with your credentials")
            print("  3. Go to: Flows → Import")
            print("  4. Upload these files:")
            for flow in FLOWS:
                print(f"     • {flow}")
            print("\nMethod 2: API with Credentials")
            print("  Set environment variables:")
            print("    export LANGFLOW_USERNAME='admin'")
            print("    export LANGFLOW_PASSWORD='your-password'")
            print("    python deploy_final.py --auth credentials")
            print("\nMethod 3: API Key")
            print("  Set environment variable:")
            print("    export LANGFLOW_API_KEY='your-api-key'")
            print("    python deploy_final.py --auth api_key")
            print("")
            return {}

        # Deploy flows
        results = {}
        for flow_name in FLOWS:
            flow_path = FLOWS_DIR / flow_name
            if flow_path.exists():
                results[flow_name] = self.deploy_flow(flow_path)
            else:
                log(f"File not found: {flow_name}", "WARN")
                results[flow_name] = False

        # Summary
        print("\n" + "=" * 70)
        print("📊 DEPLOYMENT SUMMARY")
        print("=" * 70)

        success = sum(1 for v in results.values() if v)
        total = len(results)

        print(f"Success: {success}/{total}")
        print("")

        for flow_name, ok in results.items():
            status = "✅" if ok else "❌"
            print(f"{status} {flow_name}")

        print("")

        if success == total:
            print("🎉 All flows deployed successfully!")
        else:
            print(f"⚠️  {total - success} flow(s) failed")

        return results


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Deploy flows to Langflow")
    parser.add_argument("--url", default=LANGFLOW_URL, help="Langflow URL")
    parser.add_argument(
        "--auth", default="auto", choices=["auto", "credentials", "api_key"], help="Authentication method"
    )

    args = parser.parse_args()

    deployer = LangflowDeployer(args.url)
    results = deployer.deploy_all(args.auth)

    if results:
        success = sum(1 for v in results.values() if v)
        total = len(results)
        sys.exit(0 if success == total else 1)
    else:
        # Manual deployment required
        sys.exit(0)


if __name__ == "__main__":
    main()
