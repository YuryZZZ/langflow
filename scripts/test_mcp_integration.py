#!/usr/bin/env python3
"""Test script for MCP integration with Langflow deployment.
This script tests connectivity to a Langflow instance and verifies MCP server registration.
"""

import time
from typing import Any

import requests


class LangflowMCPTester:
    def __init__(self, base_url: str):
        """Initialize tester with Langflow base URL.

        Args:
            base_url: Base URL of Langflow deployment (e.g., https://langflow-xyz.onrender.com)
        """
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json", "Accept": "application/json"})

    def test_health(self) -> bool:
        """Test health endpoint."""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"Health check failed: {e}")
            return False

    def test_api_version(self) -> str | None:
        """Test API version endpoint."""
        try:
            response = self.session.get(f"{self.base_url}/api/v1/version", timeout=10)
            if response.status_code == 200:
                return response.json().get("version")
        except Exception as e:
            print(f"API version check failed: {e}")
        return None

    def test_mcp_server_registration(self, server_name: str, server_config: dict[str, Any]) -> bool:
        """Test MCP server registration.

        Args:
            server_name: Name of MCP server
            server_config: MCP server configuration

        Returns:
            True if registration successful
        """
        try:
            # Langflow MCP API endpoint
            url = f"{self.base_url}/api/v2/mcp/servers/{server_name}"
            response = self.session.put(url, json=server_config, timeout=30)

            if response.status_code in [200, 201]:
                print(f"✓ MCP server '{server_name}' registered successfully")
                return True
            print(f"✗ MCP server '{server_name}' registration failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
        except Exception as e:
            print(f"✗ MCP server '{server_name}' registration error: {e}")
            return False

    def test_parallel_mcp_registration(self) -> bool:
        """Test parallel MCP server registration."""
        parallel_config = {
            "type": "local",
            "command": ["python", "-u", "/app/.opencode/parallel_mcp.py"],
            "enabled": True,
            "timeout": 60000,
        }
        return self.test_mcp_server_registration("parallel", parallel_config)

    def test_taskbus_mcp_registration(self) -> bool:
        """Test TaskBus MCP server registration."""
        taskbus_config = {
            "type": "local",
            "command": ["python", "-u", "/app/.opencode/postgres_mcp.py"],
            "environment": {
                "POSTGRES_HOST": "localhost",
                "POSTGRES_PORT": "5432",
                "POSTGRES_DB": "opencode_taskbus",
                "POSTGRES_USER": "postgres",
                "POSTGRES_PASSWORD": "postgres",
            },
            "enabled": True,
            "timeout": 60000,
        }
        return self.test_mcp_server_registration("taskbus", taskbus_config)

    def test_all_mcp_servers(self) -> dict[str, bool]:
        """Test registration of all MCP servers."""
        servers = {
            "parallel": {
                "type": "local",
                "command": ["python", "-u", "/app/.opencode/parallel_mcp.py"],
                "enabled": True,
                "timeout": 60000,
            },
            "taskbus": {
                "type": "local",
                "command": ["python", "-u", "/app/.opencode/postgres_mcp.py"],
                "environment": {
                    "POSTGRES_HOST": "localhost",
                    "POSTGRES_PORT": "5432",
                    "POSTGRES_DB": "opencode_taskbus",
                    "POSTGRES_USER": "postgres",
                    "POSTGRES_PASSWORD": "postgres",
                },
                "enabled": True,
                "timeout": 60000,
            },
            "memory": {
                "type": "local",
                "command": ["node", "/app/.opencode/node_modules/@modelcontextprotocol/server-memory/dist/index.js"],
                "args": ["--memory-file-path", "/app/.ai/knowledge-graph.json"],
                "enabled": True,
                "timeout": 30000,
            },
            "sequential-thinking": {
                "type": "local",
                "command": [
                    "node",
                    "/app/.opencode/node_modules/@modelcontextprotocol/server-sequential-thinking/dist/index.js",
                ],
                "enabled": True,
                "timeout": 60000,
            },
            "filesystem": {
                "type": "local",
                "command": [
                    "node",
                    "/app/.opencode/node_modules/@modelcontextprotocol/server-filesystem/dist/index.js",
                ],
                "args": ["/app"],
                "enabled": True,
            },
        }

        results = {}
        for server_name, config in servers.items():
            print(f"\nTesting MCP server: {server_name}")
            results[server_name] = self.test_mcp_server_registration(server_name, config)
            time.sleep(1)  # Rate limiting

        return results

    def run_comprehensive_test(self) -> dict[str, Any]:
        """Run comprehensive test suite."""
        print("=" * 60)
        print("Langflow MCP Integration Test")
        print("=" * 60)

        results = {"health": False, "api_version": None, "mcp_servers": {}}

        # Test health endpoint
        print("\n1. Testing health endpoint...")
        results["health"] = self.test_health()
        print(f"   Health check: {'✓ PASS' if results['health'] else '✗ FAIL'}")

        # Test API version
        print("\n2. Testing API version...")
        version = self.test_api_version()
        results["api_version"] = version
        print(f"   API Version: {version if version else '✗ Not available'}")

        # Test MCP server registration
        print("\n3. Testing MCP server registration...")
        mcp_results = self.test_all_mcp_servers()
        results["mcp_servers"] = mcp_results

        # Summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"Health endpoint: {'✓ PASS' if results['health'] else '✗ FAIL'}")
        print(f"API version: {results['api_version']}")

        mcp_success = sum(1 for success in mcp_results.values() if success)
        mcp_total = len(mcp_results)
        print(f"MCP servers: {mcp_success}/{mcp_total} successful")

        for server, success in mcp_results.items():
            print(f"  {server}: {'✓' if success else '✗'}")

        overall_success = results["health"] and mcp_success >= 2  # At least 2 MCP servers
        print(f"\nOverall: {'✓ PASS' if overall_success else '✗ FAIL'}")

        return results


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description="Test MCP integration with Langflow deployment")
    parser.add_argument(
        "--url", required=True, help="Langflow deployment URL (e.g., https://langflow-xyz.onrender.com)"
    )
    parser.add_argument("--test-all", action="store_true", help="Test all MCP servers")
    parser.add_argument("--test-parallel", action="store_true", help="Test parallel MCP server only")
    parser.add_argument("--test-taskbus", action="store_true", help="Test TaskBus MCP server only")

    args = parser.parse_args()

    tester = LangflowMCPTester(args.url)

    if args.test_parallel:
        print("Testing parallel MCP server...")
        success = tester.test_parallel_mcp_registration()
        print(f"Parallel MCP: {'✓ PASS' if success else '✗ FAIL'}")

    elif args.test_taskbus:
        print("Testing TaskBus MCP server...")
        success = tester.test_taskbus_mcp_registration()
        print(f"TaskBus MCP: {'✓ PASS' if success else '✗ FAIL'}")

    elif args.test_all:
        tester.run_comprehensive_test()

    else:
        # Default: run comprehensive test
        tester.run_comprehensive_test()


if __name__ == "__main__":
    main()
